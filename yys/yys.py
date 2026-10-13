import sys,os,random,time,traceback
import cv2
from PyQt6.QtCore import QObject,pyqtSignal
import action

#grab() 用来从任务函数的任意深处退出(ADB 断了、长时间认不出界面)，由 run() 接住
class _Stop(Exception):
    pass

class Worker(QObject):
    finished = pyqtSignal(int)
    progress = pyqtSignal(str,int)
    start_task = pyqtSignal(int, float)  # (任务序号, 次数)；次数用 float 才能把 inf 原样传过来，声明成 int 会被截成乱数
    
    def __init__(self,thread_id=None,index=None,cishu_max=None,load_images=True):
        super().__init__()
        self.game_name='yys'
        self.thread_id = thread_id
        # DO NOT connect signal here - will be connected after moveToThread()
        #设置默认功能和次数
        self.func=[{'description':'0 屏幕截图并保存','func_name':0,'count_default':'inf'},\
        {'description':'1 结界突破','func_name':self.tupo,'count_default':'inf'},\
        {'description':'2 御魂(司机)','func_name':self.yuhun,'count_default':200},\
        {'description':'3 御魂(打手)','func_name':self.yuhun2,'count_default':'inf'},\
        {'description':'4 御魂/御灵/契灵探查(单刷)','func_name':self.yuhundanren,'count_default':200},\
        {'description':'5 探索(司机)','func_name':self.gouliang,'count_default':30},\
        {'description':'6 探索(打手)','func_name':self.gouliang2,'count_default':'inf'},\
        {'description':'7 探索(单刷)','func_name':self.gouliang3,'count_default':30},\
        {'description':'8 百鬼夜行','func_name':self.baigui,'count_default':200},\
        {'description':'9 自动斗技','func_name':self.douji,'count_default':30},\
        {'description':'10 当前活动','func_name':self.huodong,'count_default':200},\
        {'description':'11 厕纸抽卡','func_name':self.chouka,'count_default':'inf'},\
        {'description':'12 秘境召唤','func_name':self.mijing,'count_default':'inf'},\
        {'description':'13 妖气封印/秘闻','func_name':self.yaoqi,'count_default':10},\
        {'description':'14 契灵boss（单刷）','func_name':self.qilingdanren,'count_default':200},\
        {'description':'15 个人突破(打8退'+str(action.config_get('tupo','tui','4'))+')','func_name':self.tupo84,'count_default':'inf'},\
        {'description':'16 英杰试炼·鬼兵演武','func_name':self.yingjie_guibing,'count_default':30},\
        {'description':'17 英杰试炼·梦墟秘境','func_name':self.yingjie_mengxu,'count_default':50}]
        #功能序号
        self.index=index
        self.cishu_max=cishu_max
        self.isRunning=False
        self.act_t=time.time(); self.warn_t=0; self.fail_n=0    #grab() 用，run() 开头会重置
        self.idle_warn,self.idle_stop=120,600
        #读取文件
        self.imgs = action.load_imgs(self.game_name)

    def execute_task(self, index, cishu_max):
        """Slot that receives the start signal with parameters"""
        self.run(index, cishu_max)
    
    def run(self,index=None,cishu_max=None):
        #self.progress.emit('Thread is '+str(self.thread_id),self.thread_id)
        #self.progress.emit('Call function index '+str(self.index)+' with max count of '+str(self.cishu_max),self.thread_id)
        self.index=index
        if cishu_max < 0:
            cishu_max = float('inf')
        elif cishu_max != float('inf'):
            cishu_max = int(cishu_max)
        self.cishu_max=cishu_max
        self.isRunning=True
        self.act_t=time.time()      #上次"认出界面"的时间：点击、或有意等待 >=1 秒
        self.warn_t=0
        self.fail_n=0
        try:
            self.idle_warn=float(action.config_get('general','idle_warn','120'))
            self.idle_stop=float(action.config_get('general','idle_stop','600'))
        except ValueError:
            self.idle_warn,self.idle_stop=120,600
        try:
            if self.index in range(len(self.func)):
                command=self.func[self.index]['func_name']
                command()
        except _Stop:
            pass
        except Exception:
            #异常逃出 Qt 槽会让 PyQt6 直接终止整个界面进程，所以在这里接住、写进日志
            self.message_output('任务出错，已停止：\n'+traceback.format_exc(limit=-3))
        finally:
            self.isRunning=False
            self.finished.emit(self.thread_id)
    
    def message_output(self,msg):
        self.progress.emit(msg,self.thread_id)
    
    #暂停并支持提前停止
    def sleep_fast(self,t=0):
        #return value indicates interrupt happens
        for t_count in range(round(t/0.1)):
            if not self.isRunning:
                return True
            time.sleep(0.1)
        if t>=1:
            #有意的长等待(冷却、战斗中、等刷新)说明任务知道自己在哪，不算"认不出界面"
            self.act_t=time.time()
        return False

    #所有任务都用它截图(不要直接调 action.screenshot)。
    #① 截图失败(ADB 断了、模拟器重启)：原地重试，每 5 次 adb connect 一次，连续 30 次失败就停，
    #   不把 -1/None 交给任务 —— 以前 -1 进了 matchTemplate 会让整个界面崩掉，连「断开ADB」都来不及点。
    #② 认不出界面：距上次点击/有意等待超过 idle_warn 秒写一条日志，超过 idle_stop 秒停止(config.ini [general]，0 = 不停)。
    #   整场战斗期间也是"没点击"，所以阈值要比最长的一场战斗长
    def grab(self):
        while True:
            if not self.isRunning: raise _Stop
            s=action.screenshot(self.thread_id)
            if s is not None and not isinstance(s,int): break
            self.fail_n=self.fail_n+1
            if self.fail_n==1:
                self.message_output('截图失败，重试中(模拟器是不是重启了？)')
            if self.fail_n%5==0 and action.adb_enable[self.thread_id]:
                dev=action.devices_tab[self.thread_id] or ''
                if ':' in dev:
                    self.message_output('重连 ADB：'+action.adb_connect(dev))
            if self.fail_n>=30:
                self.message_output('连续 30 次截图失败，停止。确认模拟器正常后点「断开ADB」再「连接ADB」')
                raise _Stop
            if self.sleep_fast(0.5): raise _Stop
        if self.fail_n:
            self.message_output(f'截图恢复(之前失败 {self.fail_n} 次)')
            self.fail_n=0
        idle=time.time()-max(self.act_t,action.last_touch.get(self.thread_id,0))
        if self.idle_stop>0 and idle>=self.idle_stop:
            self.message_output(f'已经 {int(idle)} 秒没认出界面，自动停止(游戏是不是停在了这个任务不认识的页面？)')
            raise _Stop
        if self.idle_warn>0 and idle>=self.idle_warn and time.time()-self.warn_t>=self.idle_warn:
            self.warn_t=time.time()
            self.message_output(f'已经 {int(idle)} 秒没认出界面：请确认游戏停在这个任务的页面上')
        return s

    #点了"点一下就翻页"的按钮(结算、奖励、准备)之后，等画面真的换了再回主循环。
    #换页有淡出：逻辑上已经到了下一页，截图里还是旧画面，主循环会照着旧画面再点一次，
    #而这一下落在下一页同一位置的按钮上(御魂的奖励袋子 (585,498) 正对挑战页的「阴阳术」(610,520))。
    #names 是这几页会出现的模板；出现新模板 / 全都没了 / 点的那个挪了位置 = 换页了；
    #只剩刚点的那些 = 还在淡出，接着等。等满 polls 次还没换(点击被动画吞了)，交回主循环重点
    def wait_change(self,screen,name,pt,names,polls=6):
        def seen(img):
            got={}
            for n in names:
                p=action.locate(img.copy(),self.imgs[n],0)
                if p: got[n]=p[0]
            return got
        before=seen(screen)
        before[name]=pt     #locate 在主循环那张图上画过圈，刚点的那个要按点击前的位置算
        for _ in range(polls):
            if self.sleep_fast(0.3): return True
            s=self.grab()
            if s is None or isinstance(s,int): continue
            now=seen(s)
            if not now or any(n not in before for n in now): return False
            if name in now and abs(now[name][0]-pt[0])+abs(now[name][1]-pt[1])>15: return False
        return False

    #主循环点完一个按钮后调用：是结算/奖励/准备这类"点一下就翻页"的，等换页再回主循环(见 wait_change)
    SETTLE=('ying','jiangli','jiangli2','jixu','zhunbei','zhunbei2','shibai','hdjiangli','hdjixu','hdshengli')
    def settle(self,screen,name,pt):
        if name not in self.SETTLE: return False
        return self.wait_change(screen,name,pt,[n for n in self.SETTLE if n in self.imgs])

    ####################################################
    #以下是脚本功能代码
    ####################################################
    #结节突破
    def tupo(self):
        last_click=''
        cishu = 0
        refresh=0
        liaotu=None
        while self.isRunning:   #直到取消，或者出错
            #if not isRunning:
            #    break
            #截屏
            #im = np.array(mss.mss().grab(monitor))
            #screen = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR)
            screen=self.grab()
            #cv2.imshow("Image", screen)
            #cv2.waitKey(0)

            #寮突破判断
            if liaotu==None:
                want = self.imgs['liaotupo']
                size = want[0].shape
                h, w , ___ = size
                pts = action.locate(screen,want,0)
                if not len(pts) == 0:
                    liaotu=True
                    self.message_output('寮突破')

                want = self.imgs['gerentupo']
                size = want[0].shape
                h, w , ___ = size
                pts = action.locate(screen,want,0)
                if not len(pts) == 0:
                    liaotu=False
                    self.message_output('个人突破')

            #避免寮突失败次数太多
            if liaotu:
                want = self.imgs['tuposhibai']
                size = want[0].shape
                h, w , ___ = size
                pts = action.locate(screen,want,0)
                if len(pts) >= 4:
                    self.message_output('寮突破失败次数：'+str(len(pts)))
                    self.message_output('向上滑')
                    action.swipe(pts[len(pts)-1],self.thread_id,400)
                    self.sleep_fast(2)
                    continue
            
            #奖励
            for i in ['jujue','queding',\
                      'tuposhangxian','shibai','ying','jiangli','jixu',\
                      'jingong','jingong2','jingong3',\
                      'lingxunzhang','lingxunzhang2','lingxunzhang4',\
                      'shuaxin','zhunbei']:
                want=self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target=screen
                pts=action.locate(target,want,0)
                if not len(pts)==0:
                    #无次数，等待5分钟
                    if i == 'tuposhangxian':
                            self.message_output('进攻CD，暂停5分钟')
                            t=60*5
                            if self.sleep_fast(t): return
                            break
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    if refresh>6:
                        self.message_output('重复次数上限')
                        return
                    
                    t = random.randint(50,100) / 100
                    if i == 'shibai' and refresh==0:
                        if cishu>0:
                            cishu = cishu - 1
                        self.message_output('进攻总次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(50,100) / 100
                    elif 'jingong' in i:
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('进攻总次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(500,800) / 100
                    elif 'lingxunzhang' in i:
                        t = random.randint(100,200) / 100
                    self.message_output(i)
                    if cishu > self.cishu_max:
                        self.message_output('进攻次数上限: '+str(cishu)+'/'+str(self.cishu_max))
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    break

    ########################################################
    #个人突破(打8退N)：板上只剩最后一个结界时，先进攻并退出 N 次(退出算失败，用来压结界等级)，再正常打掉
    #N 在 config.ini 的 [tupo] tui= 里改，默认 4。「次数」按进攻次数算，退出的那几场也算
    #
    #这一版结界板(2026-09 实测)：3x3 张卡片，卡片上没有进攻按钮，点卡片弹出面板才有「进攻」；
    #打赢的卡片整体变灰并盖「破」印；退出/失败的卡片只在右上角多个角标，仍可再打。
    #所以：已攻破 = 卡片变灰(勋章那一行的亮度)，剩余 = 9 - 已攻破；进攻 = 点卡片 → 面板里点「进攻」→「准备」
    #
    #选卡按勋章数(勋章越多对手越强)：还没输过时从多到少打，第一张就是探路 —— 打赢了多半能打满，照常冲 9 胜，
    #勋章最少的留到最后退 N 次。中途真输一场(不是主动退出)就放弃这一板的 9 胜，只保 3/6 胜的里程碑(奖励自动发放)：
    #第一次输时已赢 0~3 张 → 打到 3 胜刷新；4~6 张 → 打到 6 胜刷新；7 张以上 → 立即刷新；之后改成从勋章少的打。
    #第二张也输了 = 剩下的更打不过，立即刷新。真输扣突破券，所以连续两板 0 胜就停(最多亏 4 张券)。
    #没打满时刷新会弹确认框「刷新后攻破记录进度将重置，确定吗？」：右边「确定」就是 A 里现成的 queding(2026-09-26 实测 1.00)；
    #认不出来就存一帧 screenshot.png 停下
    TUPO_CARDS=[(272,183),(566,183),(861,183),(272,303),(566,303),(861,303),(272,423),(566,423),(861,423)]

    #数第 k 张卡片有几个勋章：名字下面一排 5 个槽位，有勋章的是银色星章(纹理多，亮度标准差 24~26)，
    #空槽是平的米色圆(标准差 1)。2026-09-26 在本机结界板上实测校准；上游的 xunzhang 模板在这版界面上只有 0.43
    def tupo_medals(self,screen,k):
        cx,cy=self.TUPO_CARDS[k]
        n=0
        for i in range(5):
            x,y=cx-42+34*i,cy+25
            if float(screen[y-6:y+6,x-6:x+6].mean(axis=2).std())>10:
                n=n+1
        return n

    def tupo84(self):
        try:
            n_tui=int(action.config_get('tupo','tui','4'))
        except ValueError:
            n_tui=4
        last_click=''
        cishu=0
        refresh=0
        tui_done=0          #这一板已经退出的次数
        in_tui=False        #当前这场进攻是要退出的
        tui_taps=0          #连续点退出按钮的次数(确认弹窗没认出来时不至于死循环)
        attacks_pending=0   #点了进攻但还没进战斗的次数(突破券不足时弹窗会被关掉又重来)
        won=False           #这场看到过「赢」
        remain=None
        last_read=None      #上一帧数出来的剩余数
        idle=0
        picked=None         #最近点开的是第几张卡片
        fighting=None       #这场打的是第几张卡片(点「进攻」时记下)
        pending_loss=None   #看到失败页的那张卡片：回到板上确认它没变灰，才算真输
        lost=set()          #这一板真输过的卡片，不再打
        target=None         #放弃 9 胜后的目标胜场，到了就刷新；None = 还在冲 9 胜
        refreshing=0        #点了几次「刷新」还没确认(>0 = 正在刷新)
        refresh_wait=0      #刷新中什么都没点成的帧数
        cd_wait=0           #等刷新冷却的轮数(每轮 5 秒)
        zero_boards=0       #连续 0 胜就刷新掉的板数
        last_medals=None    #上次打到日志里的各卡勋章数

        def new_board(msg):
            #换了一板结界：清掉这一板的记录
            nonlocal tui_done,in_tui,remain,last_read,picked,fighting,pending_loss,target,refreshing,refresh_wait,cd_wait,zero_boards
            if remain is not None:
                zero_boards = zero_boards+1 if remain==9 else 0
            tui_done=0
            in_tui=False
            remain=None
            last_read=None
            picked=None
            fighting=None
            pending_loss=None
            lost.clear()
            target=None
            refreshing=0
            refresh_wait=0
            cd_wait=0
            self.message_output(msg)

        self.message_output(f'个人突破 打8退{n_tui}；勋章多的先打探路，输了只保 3/6 胜，输两张就刷新')
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            if screen is None or isinstance(screen,int):
                self.message_output('截图失败，2秒后重试')
                if self.sleep_fast(2): return
                continue

            #A. 弹窗、结算、准备：看到就点（tuichuqueren = 「确认退出战斗吗？」的确认键，要排在准备前面）
            clicked=False
            for i in ['jujue','tuichuqueren','queding','queren','queren2',\
                      'tuposhangxian','shibai','ying','jiangli','jixu','zhunbei']:
                want=self.imgs[i]
                h, w , ___ = want[0].shape
                pts=action.locate(screen.copy(),want,0)
                if len(pts)==0:
                    continue
                if i == 'tuposhangxian':
                    self.message_output('进攻CD，暂停5分钟')
                    if self.sleep_fast(60*5): return
                    clicked=True
                    break
                if last_click==i:
                    refresh=refresh+1
                else:
                    refresh=0
                last_click=i
                if refresh>6:
                    self.message_output('重复次数上限：'+i)
                    return
                t = random.randint(50,100) / 100
                refresh_confirm=False
                if i in ('ying','jiangli'):
                    #「赢」/奖励 = 这场打赢了。退出模式下还打赢，说明自动战斗比退出快(实测 8 秒就能打完)，不算退出
                    if in_tui:
                        self.message_output('退出前就打赢了，这场不算退出')
                    in_tui=False
                    won=True
                    fighting=None
                elif i in ('shibai','jixu'):
                    #失败页：顶部失败印记，或底部"点击屏幕继续"(jixu)先被认出来；点过退出箭头且没看到赢才计数
                    if in_tui and tui_taps>0 and not won:
                        tui_done=tui_done+1
                        self.message_output(f'已退出 {tui_done}/{n_tui}')
                    elif fighting is not None and not won:
                        #没退出却失败 = 真输。jixu 在赢的结算页上也可能被认出来，所以先记下，回到板上看卡片没变灰才算
                        pending_loss=fighting
                    in_tui=False
                    fighting=None
                elif refreshing and i in ('tuichuqueren','queding','queren','queren2'):
                    #没打满时刷新弹出的确认框
                    refresh_confirm=True
                    t = 2
                elif i=='zhunbei':
                    #点完准备立刻去盯战斗界面：退出模式下要赶在自动战斗打完之前把退出确认掉
                    t = 1.0
                self.message_output(i)
                xy = action.cheat(pts[0], w, h-10)
                action.touch(xy,self.thread_id)
                if self.sleep_fast(t): return
                #结算/奖励页等换页再截图(淡出时补点会点到结界板的卡片上)；准备页不等，退出模式要赶在自动战斗打完前退掉
                if i!='zhunbei' and self.settle(screen,i,pts[0]): return
                if refresh_confirm:
                    new_board('已确认刷新，新的一板结界')
                clicked=True
                break
            if clicked:
                idle=0
                continue

            #点了刷新，确认框却一直没点成(多半是确认键模板和这版界面对不上)：存一帧好补模板
            if refreshing:
                refresh_wait=refresh_wait+1
                if refresh_wait>8:
                    cv2.imwrite('screenshot.png',cv2.cvtColor(screen,cv2.COLOR_RGB2BGR))
                    self.message_output('点了刷新但没认出确认框，已存当前画面到 screenshot.png(用来裁确认键模板)，停止')
                    return

            #B. 卡片弹出的面板：点「进攻」
            want=self.imgs['jingong']
            h, w , ___ = want[0].shape
            pts=action.locate(screen.copy(),want,0)
            if not len(pts)==0:
                attacks_pending=attacks_pending+1
                if attacks_pending>4:
                    self.message_output('连续点进攻都没进入战斗，可能突破券不足，停止')
                    return
                cishu=cishu+1
                if cishu > self.cishu_max:
                    self.message_output('进攻次数上限: '+str(cishu)+'/'+str(self.cishu_max))
                    return
                won=False
                fighting=picked
                if remain==1 and tui_done<n_tui and target is None:
                    in_tui=True
                    tui_taps=0
                    self.message_output(f'最后一个结界，这场退出（{tui_done+1}/{n_tui}）')
                else:
                    in_tui=False
                self.message_output('进攻总次数：'+str(cishu)+'/'+str(self.cishu_max))
                xy = action.cheat(pts[0], w, h-10)
                action.touch(xy,self.thread_id)
                last_click='jingong'
                idle=0
                if self.sleep_fast(random.randint(150,250)/100): return
                continue

            #C. 战斗中(左上角有退出箭头；放技能的过场会把它藏起来，等它回来)
            want=self.imgs['tui']
            h, w , ___ = want[0].shape
            pts=action.locate(screen.copy(),want,0)
            if not len(pts)==0:
                attacks_pending=0
                idle=0
                if in_tui:
                    tui_taps=tui_taps+1
                    if tui_taps>6:
                        self.message_output('点了退出但没看到确认弹窗，停止')
                        return
                    self.message_output(f'退出战斗（第{tui_done+1}/{n_tui}次）')
                    xy = action.cheat(pts[0], w, h)
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(0.3): return
                else:
                    if self.sleep_fast(1): return
                continue

            #D. 结界板(右侧「个人」页签可见)：数已攻破的卡片，点下一张没攻破的
            if not len(action.locate(screen.copy(),self.imgs['gerentupo'],0))==0:
                #面板弹出/过场时整块板被压暗(攻破记录进度条那块正常 170、压暗 66)，这一帧不能拿来判卡片
                if float(screen[515:545, 240:330].mean())<120:
                    idle=idle+1
                    if self.sleep_fast(0.5): return
                    continue
                want=self.imgs['shuaxin']
                h, w , ___ = want[0].shape
                pts_sx=action.locate(screen.copy(),want,0)
                if refreshing and len(pts_sx)==0:
                    #点了刷新，没弹确认框、板子已经回来且按钮进了冷却 = 刷新完成
                    new_board('刷新完成，新的一板结界')
                defeated=[]
                for k,(cx,cy) in enumerate(self.TUPO_CARDS):
                    patch=screen[cy+22:cy+42, cx-30:cx+90]
                    #变灰的卡片这一行亮度 88 上下，正常 163~177
                    if patch.size>0 and float(patch.mean())<125:
                        defeated.append(k)
                now_remain=9-len(defeated)
                #连续两帧数得一样才算数：过场淡入淡出时整板亮度在变，单帧可能把正常卡片数成灰的
                if now_remain!=last_read:
                    last_read=now_remain
                    if self.sleep_fast(0.3): return
                    continue
                if remain is not None and now_remain>remain:
                    new_board('新的一板结界')
                if remain!=now_remain:
                    self.message_output(f'剩余结界：{now_remain}/9')
                remain=now_remain
                idle=0
                wins=9-now_remain
                if pending_loss is not None:
                    if pending_loss in defeated:
                        #结算页是赢的，只是先认出了 jixu
                        pass
                    else:
                        lost.add(pending_loss)
                        if target is None:
                            #第一次输：已赢 0~3 → 保 3 胜；4~6 → 保 6 胜；7 以上 → 立即刷新
                            target = 3 if wins<=3 else (6 if wins<=6 else wins)
                            self.message_output(f'第{pending_loss+1}张打输了(已赢{wins}张)，这一板放弃 9 胜，打到 {target} 胜就刷新')
                        else:
                            #第二次输：已经在从勋章最少的打了还输，剩下的只会更难。目标 = 现有胜场 → 下面立即刷新
                            target=wins
                            self.message_output(f'第{pending_loss+1}张也打输了(已赢{wins}张)，剩下的更难，立即刷新')
                    pending_loss=None
                todo=[k for k in range(9) if k not in defeated and k not in lost]
                if now_remain==0 or (target is not None and (wins>=target or len(todo)==0)):
                    #全部攻破 / 到了目标胜场 / 能打的都打过了：刷新(冷却中时按钮带倒计时认不出来，就等)
                    if now_remain==9 and zero_boards>=1:
                        self.message_output('连续两板 0 胜，可能阵容打不过，停止')
                        return
                    if len(pts_sx)==0:
                        if cd_wait%12==0:
                            self.message_output('等刷新冷却' if now_remain>0 else '等结界板刷新')
                        cd_wait=cd_wait+1
                        if self.sleep_fast(5): return
                        continue
                    if refreshing>=3:
                        self.message_output('点了 3 次刷新都没反应，停止')
                        return
                    refreshing=refreshing+1
                    refresh_wait=0
                    self.message_output(f'刷新结界(这一板赢了 {wins} 张)')
                    xy = action.cheat(pts_sx[0], w, h-10)
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(1.5): return
                    continue
                #没输过：勋章多的先打(探路)；输过：勋章少的先打。勋章一样时按板上顺序
                medals={k:self.tupo_medals(screen,k) for k in todo}
                if medals!=last_medals:
                    last_medals=medals
                    self.message_output('勋章：'+' '.join(f'{k+1}号{m}' for k,m in medals.items()))
                k=min(todo,key=lambda k: medals[k] if lost else -medals[k])
                picked=k
                cx,cy=self.TUPO_CARDS[k]
                self.message_output(f'点第{k+1}张结界')
                xy = action.cheat((cx,cy), 60, 30)
                action.touch(xy,self.thread_id)
                if self.sleep_fast(random.randint(100,150)/100): return
                continue

            #E. 什么都没认出来：等一下，别空转
            idle=idle+1
            if idle%40==0:
                self.message_output('未识别的界面，等待中（请确认游戏停在个人突破的结界板）')
            if self.sleep_fast(0.5): return

    ########################################################
    #御魂司机
    def yuhun(self):
        last_click=''
        cishu=0
        refresh=0
        
        while self.isRunning:
            #截屏
            screen=self.grab()
            
            #self.message_output('screen shot ok',time.ctime())
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            #自动点击通关结束后的页面
            for i in ['jujue','tiaozhan','tiaozhan2',\
                      'moren','queding','zhidao','querenyuhun','ying',\
                      'jiangli','jiangli2',\
                      'jixu','shibai']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    elif i=='querenyuhun':
                        refresh=refresh+2
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if i == 'tiaozhan' or i=='tiaozhan2':
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t=random.randint(500,750)/100
                    else:
                        self.message_output(i)
                        t = random.randint(50,100) / 100
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break
        
    ########################################################
    #御魂打手
    def yuhun2(self):
        last_click=''
        cishu=0
        refresh=0
        while self.isRunning:
            #截屏
            screen=self.grab()
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            #如果队友推出则自己也退出
            want = self.imgs['tiaozhanhuise']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('队友已退出')
                want = self.imgs['likaiduiwu']
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    
            
            #自动点击通关结束后的页面
            for i in ['jujue','moren','queding','querenyuhun','zhidao',\
                      'ying','jiangli','jiangli2','jixu',\
                      'jieshou2','jieshou','shibai']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    elif i=='querenyuhun':
                        refresh=refresh+2
                    else:
                        refresh=0
                    
                    #self.message_output('重复次数：',refresh)
                    if refresh>6:
                        self.message_output('进攻次数上限')
                        return
                    elif refresh==0 and 'jiangli' in i and not last_click=='querenyuhun':
                        #self.message_output('last',last_click)
                        cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                    if 'jieshou' in i:
                        a,b=pts[0]
                        if a<100:
                            break
                        t = random.randint(150,300) / 100
                    else:
                        t = random.randint(15,30) / 100
                    self.message_output(i)
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    last_click=i
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break
                

    ########################################################
    #御魂单人
    #英杰试炼·鬼兵演武：流程和单人御魂一样(挑战 → 准备 → 战斗 → 结算)，只是「挑战」按钮长得不同。
    #tiaozhan6 从本机鬼兵演武页裁(1.00)；不放 tancha，它在这页的体力图标旁有 0.94，离阈值太近
    GUIBING=['jujue','querenyuhun','zhidao','ying','jiangli','jiangli2','jixu','zhunbei','guanbi',
             'tiaozhan6','queding','shibai']
    def yingjie_guibing(self):
        self.yuhundanren(self.GUIBING)

    #英杰试炼·梦墟秘境：挑战 → 准备 → 战斗 → 结算；打完带「祝」的关卡会出「请选择奖励」(4 张祝福卡)。
    #阶段一：按 MX_TARGET 升 涤尘 4 / 同调 3 / 遏云 2(优先级同顺序)，卡上没有要的就选第一张；
    #都到了 → 阶段二：战斗里点右下角阴阳师头像 → 「智能」(之后的战斗会保持，只点一次)，祝福一律选第一张。
    #卡上的 Lv.N 是选了之后的等级，有 Lv.2~4 的模板(mx_lv2~4)，读不出来(Lv.5)就按记录 +1 推算。
    #选卡：点卡片(选中 + 弹详情) → 点标题空白处关掉详情 → 点「确定」。名字模板取「·」后两个字(mx_dichen/mx_tongtiao/mx_eyun)
    MENGXU=['jujue','querenyuhun','zhidao','ying','jiangli','jiangli2','jixu','zhunbei','guanbi',
            'tiaozhan7','queding','shibai']
    MX_TARGET=[('mx_dichen','涤尘',4),('mx_tongtiao','同调',3),('mx_eyun','遏云',2)]
    MX_CARDS=[162,431,700,969]      #4 张卡的中心 x
    def yingjie_mengxu(self):
        #mx_lv：这一局各祝福当前等级(读到或推算)；mx_auto：阴阳师技能已改成「智能」。
        #停了再点开始不清空(同一个界面进程里 Worker 不重建)；新的一局靠"卡上等级比记录的低"自动清空
        if not hasattr(self,'mx_lv'):
            self.mx_lv={}
            self.mx_auto=False
        self.mx_try=0
        self.yuhundanren(self.MENGXU,hook=self.mengxu_hook)

    def mx_phase2(self):
        return all(self.mx_lv.get(n,1)>=lv for n,_,lv in self.MX_TARGET)

    #读 4 张卡：[(名字模板 或 None, 卡上显示的等级 或 None), ...]
    def mx_read(self,screen):
        cards=[]
        for cx in self.MX_CARDS:
            name=next((n for n,_,_ in self.MX_TARGET if n in self.imgs and
                       action.locate(screen[300:365,cx-125:cx+125].copy(),self.imgs[n],0)),None)
            lv=next((d for d in (2,3,4,5) if f'mx_lv{d}' in self.imgs and
                     action.locate(screen[375:412,cx-125:cx-20].copy(),self.imgs[f'mx_lv{d}'],0)),None)
            cards.append((name,lv))
        return cards

    def mengxu_pick(self,screen):
        cards=self.mx_read(screen)
        #目标技能的模板缺失、或目标卡上的等级读不出来(Lv.5 等)：把选择页存进 ./mengxu/ 好补裁，最多 20 张
        if any(n not in self.imgs for n,_,_ in self.MX_TARGET) or any(n and l is None for n,l in cards):
            os.makedirs('mengxu',exist_ok=True)
            k_=len(os.listdir('mengxu'))
            if k_<20:
                cv2.imwrite(f'mengxu/select_{k_+1:02d}.png',cv2.cvtColor(screen,cv2.COLOR_RGB2BGR))
        #卡上显示的等级不比记录的高 = 已经是新的一局，记录作废
        if any(n and lv and self.mx_lv.get(n,0)>=lv for n,lv in cards):
            self.message_output('祝福等级比记录的低，当作新的一局，重新计数')
            self.mx_lv={}
        #没选的卡也能说明当前等级：卡上 Lv.N = 选了之后的等级，所以现在是 N-1
        for n,lv in cards:
            if n and lv: self.mx_lv[n]=max(self.mx_lv.get(n,1),lv-1)
        k=0
        if not self.mx_phase2():
            for n,_,top in self.MX_TARGET:
                hit=[i for i,(m,_) in enumerate(cards) if m==n]
                if hit and (cards[hit[0]][1] or self.mx_lv.get(n,1)+1)<=top:
                    k=hit[0]; break
        n,shown=cards[k]
        zh={a:b for a,b,_ in self.MX_TARGET}
        self.message_output('祝福：'+' '.join(f'{i+1}号'+(zh[m] if m else '?')+(f'Lv{l}' if l else '')
                            for i,(m,l) in enumerate(cards))+f' → 选{k+1}号')
        action.touch(action.cheat((self.MX_CARDS[k],225),40,30),self.thread_id)   #点卡片：选中并弹出详情
        if self.sleep_fast(0.8): return True
        action.touch(action.cheat((568,62),30,10),self.thread_id)              #点标题空白处关掉详情，选择不变
        if self.sleep_fast(0.8): return True
        pts=action.locate(self.grab(),self.imgs['mx_queding'],0)
        action.touch(action.cheat(pts[0] if pts else (568,578),40,20),self.thread_id)
        if self.sleep_fast(1.0): return True
        for _ in range(5):
            if not action.locate(self.grab(),self.imgs['mx_xuanze'],0):
                if n: self.mx_lv[n]=shown or self.mx_lv.get(n,1)+1
                if self.mx_phase2() and not self.mx_auto:
                    self.message_output('涤尘4 / 同调3 / 遏云2 已到：阴阳师技能改「智能」，之后祝福选第一张')
                return True
            if self.sleep_fast(0.5): return True
        self.message_output('点了确定但选择页还在，重试')
        return True

    #阴阳师技能改「智能」：点右下角阴阳师头像弹出技能栏，再点「智能」。改过之后的战斗会保持，只做一次
    def mengxu_set_auto(self,screen):
        self.mx_try=self.mx_try+1
        pts=action.locate(screen.copy(),self.imgs['zhineng'],0)
        if not pts:
            action.touch(action.cheat((1086,585),20,20),self.thread_id)
            if self.sleep_fast(0.8): return True
            pts=action.locate(self.grab(),self.imgs['zhineng'],0)
        if pts:
            action.touch(action.cheat(pts[0],20,20),self.thread_id)
            self.mx_auto=True
            self.message_output('阴阳师技能已改为「智能」')
        elif self.mx_try>=3:
            self.message_output('没找到「智能」按钮，跳过，请手动改一次')
        self.sleep_fast(0.5)
        return True

    #返回 True = 这一帧处理过了，主循环重新截图
    def mengxu_hook(self,screen):
        if action.locate(screen.copy(),self.imgs['mx_xuanze'],0):
            return self.mengxu_pick(screen)
        if self.mx_phase2() and not self.mx_auto and self.mx_try<3:
            #战斗中：左上退出箭头在，且不是准备页(准备页也有退出箭头)
            if action.locate(screen.copy(),self.imgs['tui'],0) and not action.locate(screen.copy(),self.imgs['zhunbei'],0):
                return self.mengxu_set_auto(screen)
        return False

    #hook(screen)：每帧先调，返回 True 表示这一帧它处理了(梦墟秘境的选祝福、改智能)
    def yuhundanren(self,names=None,hook=None):
        last_click=''
        cishu=0
        refresh=0
        
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            if hook and hook(screen):
                continue

            for i in names or ['jujue','querenyuhun','zhidao','ying','jiangli','jiangli2','jixu','zhunbei','guanbi',\
                      'tiaozhan','tiaozhan2','tiaozhan4','queding','tancha','shibai']:
                want=self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target=screen
                pts=action.locate(target,want,0)
                if not len(pts)==0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    self.message_output(i)
                    if 'tiaozhan' in i:
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(300,500) / 100
                    else:
                        t = random.randint(15,30) / 100
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    #结算/奖励/准备：等换页再截图，否则淡出时会照旧画面再点一下，点到挑战页的「阴阳术」
                    if self.settle(screen,i,pts[0]): return
                    break

    ########################################################
    #探索司机
    def gouliang(self):
        last_click=''
        cishu=0
        refresh=0
        right = (654, 420)
        left = (454, 420)
        
        boss_done=False
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()

            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足 ')
                return

            want = self.imgs['queren']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('确认退出')
                try:
                    queding = pts[1]
                except:
                    queding = pts[0]
                xy = action.cheat(queding, w, h)
                action.touch(xy,self.thread_id)
                t = random.randint(15,30) / 100
                if self.sleep_fast(t): return

            #设定目标，开始查找
            #进入后
            want=self.imgs['guding']

            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                #self.message_output('正在地图中')
                want = self.imgs['xiao']
                pts = action.locate(screen,want,0)
                
                if not len(pts) == 0:
                    pass
                    #self.message_output('组队状态中')
                else:
                    self.message_output('退出重新组队')
                    boss_done=True
                    for i in ['queren', 'queren2','tuichu','tuichu2']:
                        want = self.imgs[i]
                        size = want[0].shape
                        h, w , ___ = size
                        pts = action.locate(screen,want,0)
                        
                        if not len(pts) == 0:
                            if last_click==i:
                                refresh=refresh+1
                            else:
                                refresh=0
                            last_click=i
                            #self.message_output('重复次数：',refresh)
                            if refresh>6:
                                self.message_output('进攻次数上限')
                                return
                            
                            self.message_output('退出中'+i)
                            try:
                                queding = pts[1]
                            except:
                                queding = pts[0]
                            xy = action.cheat(queding, w, h)
                            action.touch(xy,self.thread_id)
                            t = random.randint(50,80) / 100
                            if self.sleep_fast(t): return
                            break

                for i in ['weishi','boss', 'jian','jian2','boss2']:
                    want = self.imgs[i]
                    size = want[0].shape
                    h, w , ___ = size
                    target = screen
                    pts = action.locate(target,want,0)
                    if not len(pts) == 0:
                        if 'boss' in i:
                            boss_done=True
                            i='jian'
                        if last_click==i:
                            refresh=refresh+1
                        else:
                            refresh=0
                        last_click=i
                        #self.message_output('重复次数：',refresh)
                        if refresh>6:
                            self.message_output('重复次数上限：'+i)
                            return
                        if i=='weishi':
                            left = (100, 420)
                            pts[0]=left
                            self.message_output('关闭喂食')
                        xy = action.cheat(pts[0], w, h)
                        action.touch(xy,self.thread_id)
                        time.sleep(0.5)
                        break

                if len(pts)==0:
                    if not boss_done:
                        self.message_output('向右走')
                        xy = action.cheat(right, 10, 10)
                        action.touch(xy,self.thread_id)
                        t = random.randint(100,300) / 100
                        if self.sleep_fast(t): return

            for i in ['jujue','queding','ying','querenyuhun',\
                      'jiangli','jixu',\
                      'tiaozhan','ditu','weishi']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    if i=='tiaozhan' and refresh==0:
                        boss_done=False
                        cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                    #self.message_output('重复次数：',refresh)
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    self.message_output(i)
                    xy = action.cheat(pts[0], w, h )
                    action.touch(xy,self.thread_id)
                    if i=='queding':
                        t = random.randint(150,200) / 100
                    elif 'tiaozhan' in i:
                        t = random.randint(150,300) / 100
                    else:
                        t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break

    ########################################################
    #探索打手
    def gouliang2(self):
        last_click=''
        refresh=0
        cishu=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足 ')
                return
            
            #进入后
            want = self.imgs['guding']
            pts = action.locate(screen,want,0)
            if not len(pts) == 0:
                #self.message_output('正在地图中')
                want = self.imgs['xiao']
                pts = action.locate(screen,want,0)
                
                if not len(pts) == 0:
                    pass
                    #self.message_output('组队状态中')
                else:
                    self.message_output('退出重新组队')
                    
                    for i in ['queren', 'queren2','tuichu','tuichu2']:
                        want = self.imgs[i]
                        size = want[0].shape
                        h, w , ___ = size
                        pts = action.locate(screen,want,0)
                        
                        if not len(pts) == 0:
                            if last_click==i:
                                refresh=refresh+1
                            else:
                                refresh=0
                            last_click=i
                            #self.message_output('重复次数：',refresh)
                            if refresh>6:
                                self.message_output('进攻次数上限')
                                return
                            
                            self.message_output('退出中'+i)
                            try:
                                queding = pts[1]
                            except:
                                queding = pts[0]
                            xy = action.cheat(queding, w, h)
                            action.touch(xy,self.thread_id)
                            t = random.randint(50,80) / 100
                            if self.sleep_fast(t): return
                            break
                    continue

            for i in ['jujue','jieshou','querenyuhun','ying',\
                      'jiangli','jixu']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    if i=='jieshou':
                        a,b=pts[0]
                        if a<100:
                            break
                        if refresh==0:
                            cishu=cishu+1
                            self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                    #self.message_output('重复次数：',refresh)
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    self.message_output(i)
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if i=='jieshou' or i=='jieshou1':
                        t = random.randint(150,300) / 100
                    else:
                        t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break
                
    ########################################################
    #探索单人
    def gouliang3(self):
        last_click=''
        cishu=0
        refresh=0
        right = (654, 420)
        left = (454, 420)
        
        boss_done=False
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            want = self.imgs['queren']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            #x1,x2 = upleft, (965, 522)
            #target = action.cut(screen, x1, x2)
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('确认退出')
                try:
                    queding = pts[1]
                except:
                    queding = pts[0]
                xy = action.cheat(queding, w, h)
                action.touch(xy,self.thread_id)
                t = random.randint(15,30) / 100
                if self.sleep_fast(t): return

            
            #设定目标，开始查找
            #进入后
            want=self.imgs['guding']

            pts = action.locate(screen,want,0)
            if not len(pts) == 0:
                self.message_output('正在地图中')
                for i in ['boss','boss2','jian','jian2']:
                    want = self.imgs[i]
                    size = want[0].shape
                    h, w , ___ = size
                    target = screen
                    pts = action.locate(target,want,0)
                    if not len(pts) == 0:
                        if 'boss' in i:
                            boss_done=True
                        if last_click==i:
                            refresh=refresh+1
                        else:
                            refresh=0
                        last_click=i
                        #self.message_output('重复次数：',refresh)
                        if refresh>6:
                            self.message_output('进攻次数上限')
                            return
                        
                        self.message_output('点击小怪'+i)
                        xy = action.cheat(pts[0], w, h)
                        action.touch(xy,self.thread_id)
                        time.sleep(0.5)
                        break

                if len(pts)==0:
                    if not boss_done:
                        self.message_output('向右走')
                        xy = action.cheat(right, 10, 10)
                        action.touch(xy,self.thread_id)
                        t = random.randint(100,300) / 100
                        if self.sleep_fast(t): return
                        continue
                    else:
                        self.message_output('准备退出')
                        for i in ['tuichu','tuichu2']:
                            want = self.imgs[i]
                            size = want[0].shape
                            h, w , ___ = size
                            pts = action.locate(screen,want,0)
                            if not len(pts) == 0:
                                self.message_output('退出中'+i)
                                try:
                                    queding = pts[1]
                                except:
                                    queding = pts[0]
                                xy = action.cheat(queding, w, h)
                                action.touch(xy,self.thread_id)
                                t = random.randint(50,80) / 100
                                if self.sleep_fast(t): return
                    continue

            #zhunbei：点小怪后这版客户端会停在战斗准备页，没有它就卡住(2026-09-26 实测)
            for i in ['jujue','querenyuhun',\
                      'tansuo','ying','jiangli','jixu','zhunbei','c28','ditu']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if refresh==0 and i=='tansuo':
                        cishu=cishu+1
                        self.message_output('探索次数：'+str(cishu)+'/'+str(self.cishu_max))
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    self.message_output(i)
                    xy = action.cheat(pts[0], w, h )
                    action.touch(xy,self.thread_id)
                    t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break

    ########################################################
    #百鬼
    def baigui(self):
        last_click=''
        refresh=0
        cishu=0
        
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()

            #设定目标，开始查找
            #进入后
            for i in ['baigui','gailv','douzihuoqu','miaozhun','baiguijieshu',\
                    'jinru']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                        last_click=i
                    if i=='jinru':
                        if refresh==0:
                            cishu=cishu+1
                            self.message_output('进入百鬼:'+str(cishu)+'/'+str(self.cishu_max))
                        if cishu>self.cishu_max:
                            self.message_output('进攻次数上限')
                            return
                    self.message_output('点击'+i)
                    xy = action.cheat(pts[0], w, h )
                    action.touch(xy,self.thread_id)
                    t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    continue

            i='inbaigui'
            want=self.imgs[i]
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                #self.message_output('正在百鬼中')
                i='blank'
                want = self.imgs[i]
                target = screen
                pts = action.locate(target,want,0)
                if len(pts) == 0:
                    refresh=0
                    #小怪出现！
                    self.message_output('点击小怪')
                    pts2 = (640, 450)
                    xy = action.cheat(pts2, 100, 80)
                    action.touch(xy,self.thread_id)
                    t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                    continue

            i='kaishi'
            want = self.imgs[i]
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                refresh=0
                last_click=i
                self.message_output('选择押注界面')
                i='ya'
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts2 = action.locate(target,want,0)
                if not len(pts2) == 0:
                    self.message_output('点击开始')
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    t = random.randint(15,30) / 100
                    if self.sleep_fast(t): return
                else:
                    #选择押注
                    index=random.randint(0,2)
                    pts2 = (300+index*340, 500)
                    self.message_output('选择押注: '+str(index))
                    xy = action.cheat(pts2, w, h-10 )
                    action.touch(xy,self.thread_id)
                    t = random.randint(100,300) / 100
                    if self.sleep_fast(t): return

                    self.message_output('点击开始')
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    t = random.randint(100,200) / 100
                    if self.sleep_fast(t): return


    ########################################################
    #斗技
    def douji(self):
        last_click=''
        doujipaidui=0
        refresh=0
        cishu=0
        
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()

            for i in ['jujue','shoudong','zidong','queren',\
                      'douji','douji2','douji3','douji4','douji5',\
                      'doujilianxi',\
                      'doujiqueren','doujiend','ying','jixu',\
                      'zhunbei','zhunbei2',\
                      'doujiquxiao','guanbi']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    #self.message_output(i)
                    if i in ['douji','douji2','douji3','douji4']:
                        i='douji'
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if refresh==0 and i=='douji':
                        cishu=cishu+1
                        self.message_output('斗技次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(150,300) / 100
                    elif i=='doujiquxiao':
                        refresh=0
                        doujipaidui=doujipaidui+1
                        self.message_output('斗技搜索:'+str(doujipaidui))
                        if doujipaidui>5:
                            doujipaidui=0
                            self.message_output('取消搜索')
                            cishu=cishu-1
                            t = random.randint(15,30) / 100
                        else:
                            break
                    else:
                        self.message_output(i)
                        t = random.randint(50,100) / 100
                    if refresh>60 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break

    ########################################################
    #当前活动
    def huodong(self):
        last_click=''
        cishu=0
        
        refresh=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()

            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足 ')
                return
            
            for i in ['jujue','querenyuhun','queding','hddianji','hdend',\
                      'hdtiaozhan','hdtiaozhan2','hdfaxian','hdsousuo','hdsousuo2','zhunbei',\
                      'shibai','jixu','liaotianguanbi','hdshengli']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if 'hdtiaozhan' in i:
                        i='hdtiaozhan'
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    self.message_output(i)

                    t = 1
                    if 'hdtiaozhan' in i:
                        if refresh==0:
                            cishu=cishu+1
                            self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t=5
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    if i=='hdsousuo':
                        t=5
                    if i=='hdend':
                        if refresh==0:
                            self.message_output('疲劳度满，休息10分钟')
                            t = 10*60
                            if self.sleep_fast(t): return
                            break
                    elif i=='hddianji':
                        t=0
                        refresh=0
                    xy = action.cheat(pts[0], w, h)
                    action.touch(xy,self.thread_id)
                    #self.message_output('等待时间：',t)
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return

    ##########################################################
    #合成结界卡
    def card(self):
        last_click=''
        refresh=0
        while self.isRunning:
            #截屏
            screen=self.grab()
            
            for i in ['taiyin2','sanshinei','taiyin3']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if refresh>6:
                        self.message_output('进攻次数上限')
                        return
                    
                    self.message_output('结界卡*'+i)
                    xy = action.cheat(pts[0], w/2, h-10)
                    action.touch(xy,self.thread_id)
                    break
            if len(pts) == 0:
                    self.message_output('结界卡不足')
                    return
            

            for i in range(2):
                #截屏
                im = np.array(mss.mss().grab(monitor))
                screen = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR)

                want = self.imgs['taiyin']
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if len(pts) == 0:
                    self.message_output('结界卡不足')
                    return
                else:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click='taiyin'
                    #self.message_output('重复次数：',refresh)
                    if refresh>6:
                        self.message_output('进攻次数上限')
                        return
                    
                    self.message_output('结界卡'+i)
                    xy = action.cheat(pts[0], w/2, h-10 )
                    action.touch(xy,self.thread_id)

            #截屏
            screen=self.grab()

            want = self.imgs['hecheng']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                if last_click==i:
                    refresh=refresh+1
                else:
                    refresh=0
                last_click='hecheng'
                #self.message_output('重复次数：',refresh)
                if refresh>6:
                    self.message_output('进攻次数上限')
                    return
                
                self.message_output('合成中。。。')
                xy = action.cheat(pts[0], w, h-10 )
                action.touch(xy,self.thread_id)

            time.sleep(1)

    ##########################################################
    #抽卡
    def chouka(self):
        last_click=None
        cishu=0
        
        while self.isRunning:
            #截屏
            screen=self.grab()
            
            want = self.imgs['zaicizhaohuan']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                if cishu>self.cishu_max:
                    self.message_output('次数上限')
                    return
                cishu=cishu+1
                self.message_output('抽卡中：'+str(cishu)+'/'+str(self.cishu_max))
                xy = action.cheat(pts[0], w, h-10 )
                action.touch(xy,self.thread_id)
                t = random.randint(10,30) / 100
                if self.sleep_fast(t): return

    ##########################################################
    #蓝蛋升级
    def shengxing(self):
        last_click=''
        cishu=0
        refresh=0
        while self.isRunning:
            #截屏
            screen=self.grab()
                
            for i in ['jineng','jixushengxing',\
                      'jixuyucheng','querenshengxing']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if refresh>6:
                        self.message_output('进攻次数上限')
                        return
                    
                    self.message_output('升级中。。。'+i)
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if i=='querenshengxing':
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('升级个数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(250,350) / 100
                    else:
                        t = random.randint(20,100) / 100
                        
                    if self.sleep_fast(t): return
                    
    ##########################################################
    #秘境召唤
    def mijing(self):
        last_click=''
        refresh=0
        while self.isRunning:
            #截屏
            screen=self.grab()
            
            #检测聊天界面
            want = self.imgs['liaotianguanbi']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                #self.message_output('搜索秘境车中。。。')

                for i in ['jujue','mijingzhaohuan','mijingzhaohuan2']:
                    want = self.imgs[i]
                    size = want[0].shape
                    h, w , ___ = size
                    target = screen
                    pts = action.locate(target,want,0)
                    if not len(pts) == 0:
                        if last_click==i:
                            refresh=refresh+1
                        else:
                            refresh=0
                        last_click=i
                        #self.message_output('重复次数：',refresh)
                        if refresh>6:
                            self.message_output('进攻次数上限')
                            return
                        
                        self.message_output(i)
                        xy = action.cheat(pts[0], w, h-10 )
                        action.touch(xy,self.thread_id)
                        #t = random.randint(10,100) / 100
                        #if self.sleep_fast(t): return
                        break
            else:
                for i in ['jujue','canjia','liaotian']:
                    want = self.imgs[i]
                    size = want[0].shape
                    h, w , ___ = size
                    target = screen
                    pts = action.locate(target,want,0)
                    if not len(pts) == 0:
                        if last_click==i:
                            refresh=refresh+1
                        else:
                            refresh=0
                        last_click=i
                        #self.message_output('重复次数：',refresh)
                        if refresh>6:
                            self.message_output('进攻次数上限')
                            return
                        
                        if i=='canjia':
                            self.message_output('加入秘境召唤！'+i)
                        xy = action.cheat(pts[0], w, h-10 )
                        action.touch(xy,self.thread_id)
                        t = random.randint(10,30) / 100
                        if self.sleep_fast(t): return
                        break

    ########################################################
    #妖气封印和秘闻
    def yaoqi(self):
        global isRunning,cishu_max
        last_click=''
        cishu=0
        refresh=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            
            #委派任务
            for i in ['jujue','jiangli','jixu','zhunbei',\
                      'shibai','zidongpipei','zudui2',\
                      'ying','tiaozhan3','tiaozhan4']:
                want = self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target = screen
                pts = action.locate(target,want,0)
                if not len(pts) == 0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    #self.message_output('重复次数：',refresh)
                    if i=='zidongpipei' or i=='tiaozhan3' or i=='tiaozhan4':
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t=100/100
                    elif i=='shibai':
                        self.message_output('自动结束')
                        return
                    else:
                        self.message_output(i)
                        t = random.randint(30,80) / 100
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    if self.settle(screen,i,pts[0]): return
                    break
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

    ########################################################
    #契灵单人：刷材料，结契失败放弃，不点「再次结契」。
    #成功页按「继续 / 确认」正常领取，保留契灵；不操作「释放 / 弃置 / 召唤」。
    QILING_CONTINUE=('ying','jiangli','jixu','queding','queren','queren2','queren3','zhunbei','shibai')
    QILING_WAIT=('ql_failed','ql_abandon','tiaozhan5')+QILING_CONTINUE

    def qiling_challenge_disabled(self,screen):
        #归一化模板匹配对变灰不敏感。挑战页标题 + 灰度文字位置 + 颜色一起判断。
        if not action.locate(screen.copy(),self.imgs['ql_board'],0):
            return False
        tpl=self.imgs['tiaozhan5'][0]
        h,w=tpl.shape[:2]
        result=cv2.matchTemplate(cv2.cvtColor(screen,cv2.COLOR_RGB2GRAY),
                                 cv2.cvtColor(tpl,cv2.COLOR_RGB2GRAY),cv2.TM_CCOEFF_NORMED)
        _,score,_,(x,y)=cv2.minMaxLoc(result)
        if score<self.imgs['tiaozhan5'][1]:
            return False
        normal=cv2.cvtColor(tpl,cv2.COLOR_RGB2HSV)[:,:,1].mean()
        current=cv2.cvtColor(screen[y:y+h,x:x+w],cv2.COLOR_RGB2HSV)[:,:,1].mean()
        return current<normal*0.4

    def qilingdanren(self):
        last_click=''
        cishu=0
        refresh=0
        disabled_frames=0
        pending_attacks=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=self.grab()
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen.copy()
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            #结契失败是独立页面，和普通战败 shibai 不同。
            #标题 + 放弃按钮同时出现才操作；按钮位置来自模板，不盲点固定坐标。
            if (action.locate(screen.copy(),self.imgs['ql_failed'],0) and
                    (pts:=action.locate(screen.copy(),self.imgs['ql_abandon'],0))):
                refresh=refresh+1 if last_click=='ql_abandon' else 0
                last_click='ql_abandon'
                if refresh>=3:
                    self.message_output('放弃结契后页面未变化，停止，请检查游戏弹窗')
                    return
                self.message_output('结契失败，放弃结契，继续刷材料')
                action.touch(pts[0],self.thread_id)
                if self.wait_change(screen,'ql_abandon',pts[0],self.QILING_WAIT): return
                continue

            if self.qiling_challenge_disabled(screen):
                disabled_frames+=1
                if disabled_frames>=2:
                    self.message_output('挑战按钮不可用，可能已无挑战次数，停止')
                    return
                if self.sleep_fast(0.3): return
                continue
            disabled_frames=0

            for i in ('jujue',)+self.QILING_CONTINUE+('tiaozhan5','xiaozhiren'):
                want=self.imgs[i]
                size = want[0].shape
                h, w , ___ = size
                target=screen.copy()
                pts=action.locate(target,want,0)
                if not len(pts)==0:
                    if last_click==i:
                        refresh=refresh+1
                    else:
                        refresh=0
                    last_click=i
                    if i=='tiaozhan5':
                        #次数按实际发起挑战计算，最后一场的结契与领奖仍要收尾。
                        if refresh==0 and cishu>=self.cishu_max:
                            self.message_output('挑战次数已达上限，停止：'+str(cishu)+'/'+str(self.cishu_max))
                            return
                        if pending_attacks>=3:
                            self.message_output('连续点挑战未能进入战斗，可能次数或资源不足，停止')
                            return
                        pending_attacks+=1
                        if refresh==0: cishu+=1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(50,150) / 100
                    else:
                        t = random.randint(15,30) / 100
                    if i in ('zhunbei','ying','jiangli','jixu','shibai'):
                        pending_attacks=0
                    if refresh>6:
                        self.message_output('重复点击后页面未变化，停止：'+i)
                        return
                    self.message_output(i)
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    if i in self.QILING_CONTINUE or i=='tiaozhan5':
                        if self.wait_change(screen,i,pts[0],self.QILING_WAIT): return
                    break
            else:
                #战斗和结契动画阶段无按钮可点；由 grab() 的空闲超时兜底。
                if self.sleep_fast(0.2): return
