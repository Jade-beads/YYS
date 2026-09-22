import sys,random,time
from PyQt6.QtCore import QObject,pyqtSignal
import action

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
        {'description':'15 个人突破(打8退'+str(action.config_get('tupo','tui','4'))+')','func_name':self.tupo84,'count_default':'inf'}]
        #功能序号
        self.index=index
        self.cishu_max=cishu_max
        self.isRunning=False
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
        if self.index in range(len(self.func)):
            command=self.func[self.index]['func_name']
            command()
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
        return False
    
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
            screen=action.screenshot(self.thread_id)
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
    TUPO_CARDS=[(272,183),(566,183),(861,183),(272,303),(566,303),(861,303),(272,423),(566,423),(861,423)]
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
        idle=0
        self.message_output(f'个人突破 打8退{n_tui}')
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)
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
                if i in ('ying','jiangli'):
                    #「赢」/奖励 = 这场打赢了。退出模式下还打赢，说明自动战斗比退出快(实测 8 秒就能打完)，不算退出
                    if in_tui:
                        self.message_output('退出前就打赢了，这场不算退出')
                    in_tui=False
                    won=True
                elif i in ('shibai','jixu'):
                    #失败页：顶部失败印记，或底部"点击屏幕继续"(jixu)先被认出来；点过退出箭头且没看到赢才计数
                    if in_tui and tui_taps>0 and not won:
                        tui_done=tui_done+1
                        self.message_output(f'已退出 {tui_done}/{n_tui}')
                    in_tui=False
                elif i=='zhunbei':
                    #点完准备立刻去盯战斗界面：退出模式下要赶在自动战斗打完之前把退出确认掉
                    t = 1.0
                self.message_output(i)
                xy = action.cheat(pts[0], w, h-10)
                action.touch(xy,self.thread_id)
                if self.sleep_fast(t): return
                clicked=True
                break
            if clicked:
                idle=0
                continue

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
                if remain==1 and tui_done<n_tui:
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
                defeated=[]
                for k,(cx,cy) in enumerate(self.TUPO_CARDS):
                    patch=screen[cy+22:cy+42, cx-30:cx+90]
                    #变灰的卡片这一行亮度 88 上下，正常 163~177
                    if patch.size>0 and float(patch.mean())<125:
                        defeated.append(k)
                now_remain=9-len(defeated)
                if remain is not None and now_remain>remain:
                    tui_done=0
                    in_tui=False
                    self.message_output(f'新的一板结界')
                if remain!=now_remain:
                    self.message_output(f'剩余结界：{now_remain}/9')
                remain=now_remain
                idle=0
                if now_remain==0:
                    #全部攻破：刷新(冷却中时按钮认不出来，就等)
                    want=self.imgs['shuaxin']
                    h, w , ___ = want[0].shape
                    pts=action.locate(screen.copy(),want,0)
                    if not len(pts)==0:
                        self.message_output('刷新结界')
                        xy = action.cheat(pts[0], w, h-10)
                        action.touch(xy,self.thread_id)
                        if self.sleep_fast(2): return
                    else:
                        if self.sleep_fast(5): return
                    continue
                k=[k for k in range(9) if k not in defeated][0]
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
            screen=action.screenshot(self.thread_id)
            
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
                    break
        
    ########################################################
    #御魂打手
    def yuhun2(self):
        last_click=''
        cishu=0
        refresh=0
        while self.isRunning:
            #截屏
            screen=action.screenshot(self.thread_id)
            
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
                    break
                

    ########################################################
    #御魂单人
    def yuhundanren(self):
        last_click=''
        cishu=0
        refresh=0
        
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            for i in ['jujue','querenyuhun','zhidao','ying','jiangli','jiangli2','jixu','zhunbei','guanbi',\
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
            screen=action.screenshot(self.thread_id)

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
                    break

    ########################################################
    #探索打手
    def gouliang2(self):
        last_click=''
        refresh=0
        cishu=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)
            
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
            screen=action.screenshot(self.thread_id)
            
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

            for i in ['jujue','querenyuhun',\
                      'tansuo','ying','jiangli','jixu','c28','ditu']:
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
                    break

    ########################################################
    #百鬼
    def baigui(self):
        last_click=''
        refresh=0
        cishu=0
        
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)

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
            screen=action.screenshot(self.thread_id)

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
                    break

    ########################################################
    #当前活动
    def huodong(self):
        last_click=''
        cishu=0
        
        refresh=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)

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

    ##########################################################
    #合成结界卡
    def card(self):
        last_click=''
        refresh=0
        while self.isRunning:
            #截屏
            screen=action.screenshot(self.thread_id)
            
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
            screen=action.screenshot(self.thread_id)

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
            screen=action.screenshot(self.thread_id)
            
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
            screen=action.screenshot(self.thread_id)
                
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
            screen=action.screenshot(self.thread_id)
            
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
            screen=action.screenshot(self.thread_id)
            
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
    #契灵单人
    def qilingdanren(self):
        last_click=''
        cishu=0
        
        refresh=0
        while self.isRunning:   #直到取消，或者出错
            #截屏
            screen=action.screenshot(self.thread_id)
            
            #体力不足
            want = self.imgs['notili']
            size = want[0].shape
            h, w , ___ = size
            target = screen
            pts = action.locate(target,want,0)
            if not len(pts) == 0:
                self.message_output('体力不足')
                return

            for i in ['jujue','ying','jiangli','jixu','queding',\
                      'qiling1','mingqi','queren3',\
                      'tiaozhan5','shibai','xiaozhiren']:
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
                    if i=='tancha' or i=='tiaozhan5':
                        if refresh==0:
                            cishu=cishu+1
                        self.message_output('挑战次数：'+str(cishu)+'/'+str(self.cishu_max))
                        t = random.randint(50,150) / 100
                    elif i=='queren3':
                        t = random.randint(350,450) / 100
                    else:
                        t = random.randint(15,30) / 100
                    if refresh>6 or cishu>self.cishu_max:
                        self.message_output('进攻次数上限')
                        return
                    xy = action.cheat(pts[0], w, h-10 )
                    action.touch(xy,self.thread_id)
                    if self.sleep_fast(t): return
                    break
