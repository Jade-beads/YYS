#百鬼棋局(自走棋)。阵容由游戏自己的「阵容预设」决定：每局开头点「阵容」应用第一套预设，商店里属于这套阵容的卡右上角带「荐」，
#只买带荐的；钱够就买经验升到 [qiju] level 阶(默认 5)，之后刷新，花到只剩 [qiju] reserve 币(默认 10)为止。
#场上满了(拖上去的卡弹回手里)而手里还有式神时，不管几阶都优先买经验升阶(2026-11-06 用户定：定级赛第 1 局卡在六阶 6/6，
#手里堆了 9 张荐卡上不了场)。
#手牌不会自动上阵(2026-11 教学局实测)，所以备战阶段把手里的式神(带荐的先)拖到空位、把纹章和御魂拖到上过阵的式神身上。
#手牌上限 10 张，定级赛第 1 局堆到 12/10，荐卡买不进来、钱也花不出去，所以场上满了或者买卡失败时要卖卡(拖到左下「购买经验」处，
#照 assttyys)：先卖不带荐的式神，再卖装不上去的御魂/纹章(第 3 局后期弹「式神装备数量已达上限」)。
#符咒三选一、开局的六道投票都点第一项(不点的话符咒要等超时，整个备战阶段就没了)；百鬼夜行投掷不点，系统按血量顺序自动分配。
#坐标和 qj_*.png 模板来自 1136x640 的教学局和定级赛截图。
import os,time,random
import cv2
import numpy
import action

PH={'bei':'qj_ph_bei','zhan':'qj_ph_zhan','dai':'qj_ph_dai','gui':'qj_ph_gui'}    #顶栏阶段字：备战/战斗/等待/百鬼夜行
TOP_BOX=(380,0,820,36)
SHOP_X=(383,550,716,883,1049)   #商店 5 张卡的中心 x，点卡面 (x,150) 就是买
JIAN_BOX=(300,45,1136,100)      #「荐」在卡面右上角，比卡中心靠右约 56
SHOP_BOX=(300,45,1136,265)
HAND_BOX=(150,470,1000,630)     #手牌：式神卡左上角是带月牙的小方块，御魂卡底部是浅色名牌
BOARD_BOX=(250,310,880,490)     #棋盘 12 个空位各站一个小纸人；升阶后整块棋盘会缩放，所以每次现找
FRONT_Y=405                     #纸人 y 小于它的一排是前排(靠近对手)
LV_BOX=(105,595,170,635)
GOLD_BOX=(1060,566,1100,598)    #右下角钱袋上的金币数(不含金币图标)
COIN_BOX=(300,580,450,610)      #大厅「本周鼬乐币 x/600」
EXP_XY=(88,575); REFRESH_XY=(1068,400); BAG_XY=(1075,580); PANEL_BACK=(35,33)
LEAVE_CANCEL=(464,388)          #局内左上箭头会弹「是否确定离开游戏?」，只点取消
FUZHOU_BOX=(400,50,740,115)     #「选择一个符咒」标题；三张卡里第一张的卡面中间是 (322,300)，卡下面的「⟳2」是花钱刷新，别点。
FUZHOU_PICK=(322,300)           #y 取在商店卡片(y<265)下面：弹窗淡出时补点一下也不会买到第一张卡
LIUDAO_BOX=(250,60,900,125)     #开局「本局即将前往的幻境，由八位大人共同决定」；第一个圆(冥界)中心 (293,258)
LIUDAO_PICK=(293,258)
SELL_XY=(50,572)                #卖卡：把手牌拖到这里(assttyys「关闭商店状态」的拖动终点，1280x720 的 (39~71,626~657) 换算过来)
EXP_COST,REFRESH_COST=4,2

def _gray(img):
    return img if img.ndim==2 else cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)

#灰度归一化匹配，返回(分数,中心点)。不在图上画圈(action.locate 会)
def best(img,tpl,box=None):
    x0,y0=0,0
    if box:
        x0,y0,x1,y1=box; img=img[y0:y1,x0:x1]
    _,s,_,(x,y)=cv2.minMaxLoc(cv2.matchTemplate(_gray(img),_gray(tpl),cv2.TM_CCOEFF_NORMED))
    h,w=tpl.shape[:2]
    return float(s),(x0+x+w//2,y0+y+h//2)

#同一模板在画面上出现的每一处(分数从高到低)，相距 gap 以内的算同一处
def peaks(img,tpl,thr,box=None,gap=None):
    x0,y0=0,0
    if box:
        x0,y0,x1,y1=box; img=img[y0:y1,x0:x1]
    r=cv2.matchTemplate(_gray(img),_gray(tpl),cv2.TM_CCOEFF_NORMED)
    h,w=tpl.shape[:2]
    gx,gy=gap or (w,h)
    out=[]
    while len(out)<20:
        _,s,_,(x,y)=cv2.minMaxLoc(r)
        if s<thr: break
        out.append((x0+x+w//2,y0+y+h//2))
        r[max(0,y-gy):y+gy+1,max(0,x-gx):x+gx+1]=-1
    return out

#金币数字：浅色底上的深色笔画，按连通块从左到右切开，每块缩放到 12x20 再和 qj_d0..qj_d9 比
def gold_glyphs(img):
    x0,y0,x1,y1=GOLD_BOX
    g=_gray(img)[y0:y1,x0:x1]
    n,_,st,_=cv2.connectedComponentsWithStats((g<90).astype(numpy.uint8))
    out=[]
    for k in sorted(range(1,n),key=lambda k:st[k][0]):
        x,y,w,h,_=st[k]
        if 12<=h<=22 and w<=14:
            out.append(cv2.resize(g[y:y+h,x:x+w],(12,20),interpolation=cv2.INTER_AREA))
    return out

class QijuMixin:
    QJ_THR={'qj_lobby':0.85,'qj_zhan':0.85,'qj_zhenrong':0.85,'qj_yushe':0.85,'qj_yingyong':0.85,'qj_quxiao':0.85,
            'qj_likai':0.85,'qj_shuaxin':0.8,'qj_back1':0.85,'qj_back2':0.85,'qj_cont':0.85,'qj_xs_jujue':0.9,'qj_exp':0.85,
            'qj_fuzhou':0.8,'qj_liudao':0.8}

    def qj_tpl(self,name):
        if not hasattr(self,'_qj_gray'): self._qj_gray={}
        if name not in self._qj_gray: self._qj_gray[name]=_gray(self.imgs[name][0])
        return self._qj_gray[name]

    #看到了就返回中心点，否则 None
    def qj_seen(self,screen,name,box=None,thr=None):
        s,p=best(screen,self.qj_tpl(name),box)
        return p if s>=(thr or self.QJ_THR.get(name,0.85)) else None

    def qj_tap(self,xy,jitter=4):
        k=action.scaling_factor if action.scalar else 1
        x,y=xy[0]+random.randint(-jitter,jitter),xy[1]+random.randint(-jitter,jitter)
        action.touch([int(x*k),int(y*k)],self.thread_id)

    def qj_drag(self,a,b):
        k=action.scaling_factor if action.scalar else 1
        action.drag((a[0]*k,a[1]*k),(b[0]*k,b[1]*k),self.thread_id)

    def qj_phase(self,screen):
        scores={k:best(screen,self.qj_tpl(v),TOP_BOX)[0] for k,v in PH.items()}
        k=max(scores,key=scores.get)
        return k if scores[k]>=0.8 else None

    def qj_gold(self,screen):
        digits=''
        for g in gold_glyphs(screen):
            s={d:float(cv2.matchTemplate(g,self.qj_tpl('qj_d'+d),cv2.TM_CCOEFF_NORMED)[0][0]) for d in '0123456789'}
            d=max(s,key=s.get)
            if s[d]<0.6: return None
            digits+=d
        return int(digits) if 0<len(digits)<=3 else None

    #二~五阶认得出；一阶和六阶以上没有模板，返回 None
    def qj_level(self,screen):
        s=sorted(((best(screen,self.qj_tpl('qj_lv%d'%n),LV_BOX)[0],n) for n in (2,3,4,5)),reverse=True)
        return s[0][1] if s[0][0]>=0.85 and s[0][0]-s[1][0]>=0.08 else None

    #左下「购买经验」亮着 = 没有弹窗压暗画面(归一化匹配对整体变暗不敏感，所以再看亮度)
    def qj_clear(self,screen):
        p=self.qj_seen(screen,'qj_exp',(0,540,180,620))
        if not p: return False
        return _gray(screen)[p[1]-10:p[1]+10,p[0]-48:p[0]+48].mean()>=120

    def qj_shop_open(self,screen):
        return self.qj_seen(screen,'qj_shuaxin',(1000,380,1136,470)) is not None

    #带「荐」的商店格(0~4)
    def qj_jian(self,screen):
        out=set()
        for x,y in peaks(screen,self.qj_tpl('qj_jian'),0.85,JIAN_BOX,(40,20)):
            k=min(range(5),key=lambda i:abs(SHOP_X[i]+56-x))
            if abs(SHOP_X[k]+56-x)<40: out.add(k)
        return sorted(out)

    #手牌里式神卡、御魂卡的拖动起点(卡面中心)，从左到右。式神卡左上角的月牙徽章有橙色(qj_badge)和青白色(qj_badge2)两种，
    #只认橙色的话定级赛后期 10 张式神只数出 7 张
    def qj_hand(self,screen):
        raw=[p for t in ('qj_badge','qj_badge2') for p in peaks(screen,self.qj_tpl(t),0.75,HAND_BOX,(30,30)) if 485<=p[1]<=512]
        xs=[]
        for x,y in sorted(raw):
            if not xs or x-xs[-1]>20: xs.append(x)
        shiki=[(x+26,540) for x in xs]
        souls=[(x+31,540) for x,y in peaks(screen,self.qj_tpl('qj_soulname'),0.85,HAND_BOX,(40,20)) if 590<=y<=610]
        return shiki,sorted(souls)

    #每张手牌式神的「荐」分数(荐字在月牙徽章正下方，徽章 x 和荐字 x 差 0~2)。三场录像里带荐的 0.8~1.0、不带的 0.2~0.5
    def qj_tag_scores(self,screen,shiki):
        x0,y0,x1,y1=HAND_BOX
        tpl=self.qj_tpl('qj_jian2'); h,w=tpl.shape
        r=cv2.matchTemplate(_gray(screen)[y0:y1,x0:x1],tpl,cv2.TM_CCOEFF_NORMED)
        out=[]
        for sx,_ in shiki:
            bx=sx-26
            sub=r[max(0,515-h//2-y0):540-h//2-y0+1,max(0,bx-12-w//2-x0):bx+12-w//2-x0+1]
            out.append(float(sub.max()) if sub.size else 0.0)
        return out

    def qj_hand_jian(self,screen,shiki):
        return [s for s,v in zip(shiki,self.qj_tag_scores(screen,shiki)) if v>=0.8]

    #手里的纹章卡(符咒给的「冥府纹章」「锻刀纹章」之类)：名牌上「纹章」两个字 0.97~1.00，别的牌 ≤0.67
    def qj_emblems(self,screen):
        return sorted((x-22,540) for x,y in peaks(screen,self.qj_tpl('qj_wenzhang'),0.85,HAND_BOX,(30,15)) if 590<=y<=610)

    #空位：前排在先，各排从左到右
    def qj_slots(self,screen):
        pts=peaks(screen,self.qj_tpl('qj_slot'),0.7,BOARD_BOX,(30,25))
        return sorted(pts,key=lambda p:(p[1]>=FRONT_Y,p[0]))

    #「本周鼬乐币 600/600」：x/600 里出现两个 600 才算满
    def qj_coin_full(self,screen):
        return len(peaks(screen,self.qj_tpl('qj_600'),0.8,COIN_BOX,(20,8)))>=2

    def qj_new_game(self):
        self.qj_applied=False; self.qj_preset=False; self.qj_panel_n=0; self.qj_units=[]; self.qj_soul_i=0; self.qj_emb_i=0
        self.qj_sell_ok=True; self.qj_sell_fail=0; self.qj_new_round()

    def qj_new_round(self):
        self.qj_failed=set(); self.qj_full=False; self.qj_bag_n=0; self.qj_econ=0; self.qj_buyfail=0
        self.qj_soul_miss=0; self.qj_emb_miss=0; self.qj_sell_n=0; self.qj_noslot=0; self.qj_pending=None
        self.qj_stat={'买卡':0,'上阵':0,'御魂':0,'纹章':0,'卖卡':0,'经验':0,'刷新':0}

    #备战阶段：每帧只做一件事，下一帧先核对上一件做成没有
    def qj_prepare(self,screen):
        if not self.qj_clear(screen):
            return self.sleep_fast(0.5)     #符咒/提示之类的弹窗盖着，不点
        shiki,souls=self.qj_hand(screen)
        emblems=self.qj_emblems(screen)
        slots=self.qj_slots(screen)
        #手里有式神、却一个空位都认不出(首领回合的紫色棋盘上纸人认不出)：连着 3 帧就当场上满了
        self.qj_noslot=self.qj_noslot+1 if shiki and not slots else 0
        if self.qj_pending:
            kind,a,b,t=self.qj_pending
            self.qj_pending=None
            if kind=='buy':
                if a in self.qj_jian(screen):
                    self.qj_failed.add(a); self.qj_buyfail+=1     #钱不够或手牌满
                else:
                    self.qj_buyfail=0; self.qj_stat['买卡']+=1
            elif kind=='deploy':
                if len(shiki)>=a: self.qj_full=True                #上限到了，这回合不再拖
                else: self.qj_units.append(b); self.qj_stat['上阵']+=1
            elif kind=='soul':
                if len(souls)>=a: self.qj_soul_miss+=1; self.qj_soul_i+=1     #这个式神御魂满了或站位变了
                else: self.qj_stat['御魂']+=1
            elif kind=='emblem':
                if len(emblems)>=a: self.qj_emb_miss+=1; self.qj_emb_i+=1
                else: self.qj_stat['纹章']+=1
            elif kind=='sell':
                cat,n_before=a
                n_now={'shiki':len(shiki),'soul':len(souls),'emblem':len(emblems)}[cat]
                gold=self.qj_gold(screen)
                if gold is not None and b is not None and gold<b:
                    self.qj_sell_ok=False       #拖到左下角变成了买经验
                    self.message_output('卖卡时金币变少了(%d → %d)，这局不再卖卡'%(b,gold))
                elif n_now<n_before:
                    self.qj_sell_fail=0; self.qj_stat['卖卡']+=1
                    self.qj_failed=set(); self.qj_buyfail=0       #腾出位置了，买不进来的荐卡再试一次
                else:
                    self.qj_sell_fail+=1
                    if self.qj_sell_fail>=2:
                        self.qj_sell_ok=False
                        self.message_output('拖到左下角卖不掉卡，这局不再卖卡')
            elif kind=='refresh':
                x0,y0,x1,y1=SHOP_BOX
                if numpy.abs(screen[y0:y1,x0:x1].astype(numpy.int16)-a).mean()<6 and time.time()-t<2.5:
                    self.qj_pending=(kind,a,b,t)     #商店还没换完，别照旧画面买
                    return self.sleep_fast(0.3)
                self.qj_failed=set()
        if not self.qj_applied:
            if self.qj_panel_n>=3:
                self.message_output('打不开阵容预设，这局不按「荐」买卡'); self.qj_applied=True
            elif (p:=self.qj_seen(screen,'qj_zhenrong',(200,0,320,70))):
                self.qj_panel_n+=1; self.qj_tap(p,2)
                return self.sleep_fast(1.2)
        #先上阵(腾出手牌位置，带荐的先上)，再买荐卡，再装纹章、御魂，手牌塞满了就卖卡，最后升级/刷新
        if shiki and slots and not self.qj_full:
            pick=(self.qj_hand_jian(screen,shiki) or shiki)[0]
            self.qj_pending=('deploy',len(shiki),slots[0],0)
            self.qj_drag(pick,slots[0])
            return self.sleep_fast(0.6)
        shop=self.qj_shop_open(screen)
        if shop:
            todo=[k for k in self.qj_jian(screen) if k not in self.qj_failed]
            if todo:
                self.qj_pending=('buy',todo[0],0,0)
                self.qj_tap((SHOP_X[todo[0]],150))
                return self.sleep_fast(0.6)
        if emblems and self.qj_units and self.qj_emb_miss<2:
            target=self.qj_units[self.qj_emb_i%len(self.qj_units)]
            self.qj_pending=('emblem',len(emblems),0,0)
            self.qj_drag(emblems[0],target)
            return self.sleep_fast(0.6)
        if souls and self.qj_units and self.qj_soul_miss<2:
            target=self.qj_units[self.qj_soul_i%len(self.qj_units)]
            self.qj_pending=('soul',len(souls),0,0)
            self.qj_drag(souls[0],target)
            return self.sleep_fast(0.6)
        gold=self.qj_gold(screen)
        if gold is None:
            return self.sleep_fast(0.3)
        #场上满了、手里还有式神：不管几阶都买经验(六阶起 qj_level 认不出，也走这里)。买完清掉 qj_full，
        #下一帧再拖一次试试升阶了没有；弹回来就又是满的，接着买
        stuck=bool(shiki) and (self.qj_full or self.qj_noslot>=3)
        can_exp=gold-EXP_COST>=self.qj_reserve
        #卖卡：手牌快满(≥9 张，满 10 张就买不进荐卡)或者买卡失败了，或者场上满了又没钱买经验。
        #先卖不带荐的式神(只在场上满了时卖，没满的话上一步就拖上去了)，再卖装了两次都装不上的御魂、纹章
        clogged=len(shiki)+len(souls)+len(emblems)>=9 or self.qj_buyfail>=1
        if self.qj_sell_ok and self.qj_sell_n<6 and (clogged or (stuck and not can_exp)):
            card=None
            if stuck and self.qj_preset:        #没应用上阵容预设时谁都没有荐，别把手里的全卖了
                junk=[s for s,v in zip(shiki,self.qj_tag_scores(screen,shiki)) if v<0.6]
                if junk: card=('shiki',len(shiki),junk[0])
            if card is None and souls and self.qj_soul_miss>=2: card=('soul',len(souls),souls[0])
            if card is None and emblems and self.qj_emb_miss>=2: card=('emblem',len(emblems),emblems[0])
            if card:
                self.qj_sell_n+=1
                self.qj_pending=('sell',(card[0],card[1]),gold,0)
                self.qj_drag(card[2],SELL_XY)
                return self.sleep_fast(0.8)
        if self.qj_econ>=25:
            return self.sleep_fast(0.3)
        level=self.qj_level(screen)
        want_exp=stuck or (level is not None and level<self.qj_level_to)
        if want_exp and can_exp:
            self.qj_econ+=1; self.qj_stat['经验']+=1
            if stuck: self.qj_full=False
            self.qj_tap(EXP_XY)
            return self.sleep_fast(0.8)
        if gold-REFRESH_COST>=self.qj_reserve and self.qj_buyfail<2 and (level is None or level>=self.qj_level_to):
            if not shop:
                if self.qj_bag_n>=3: return self.sleep_fast(0.3)
                self.qj_bag_n+=1; self.qj_tap(BAG_XY)
                return self.sleep_fast(1.0)
            x0,y0,x1,y1=SHOP_BOX
            self.qj_pending=('refresh',screen[y0:y1,x0:x1].astype(numpy.int16),0,time.time())
            self.qj_econ+=1; self.qj_stat['刷新']+=1
            self.qj_tap(REFRESH_XY)
            return self.sleep_fast(0.5)
        return self.sleep_fast(0.3)

    def qj_round_log(self):
        s=self.qj_stat
        if any(s.values()):
            self.message_output('备战：'+'，'.join('%s %d'%(k,v) for k,v in s.items() if v))
        for k in s: s[k]=0

    #认不出的画面存下来补模板：./qiju/NN.png，接着目录里已有的编号往下存(每局是新进程，从 0 开始会覆盖上一局的)，最多 100 张
    def qj_save_unknown(self,screen,n):
        os.makedirs('qiju',exist_ok=True)
        used=[int(f[:-4]) for f in os.listdir('qiju') if f.endswith('.png') and f[:-4].isdigit()]
        k=max(used)+1 if used else 0
        if k>=100: return None
        path=os.path.join('qiju','%02d.png'%k)
        cv2.imwrite(path,cv2.cvtColor(screen,cv2.COLOR_RGB2BGR))
        return path

    ########################################################
    #主循环：大厅点「战」→ 局内按顶栏阶段处理 → 结算页一路点回大厅；打满次数或本周鼬乐币 600/600 就停
    def baiguiqiju(self):
        try:
            self.qj_level_to=int(action.config_get('qiju','level','5'))
            self.qj_reserve=int(action.config_get('qiju','reserve','10'))
        except ValueError:
            self.qj_level_to,self.qj_reserve=5,10
        self.qj_games=0; self.qj_new_game()
        ingame=False; phase=None; zhan_t=0; end_t=0; blank_n=0; shots=0; shot_t=0; known_t=time.time()
        fz_n=0; ld_done=False
        while self.isRunning:
            screen=self.grab()
            now=time.time()
            #弹窗：组队邀请、好友「协助悬赏封印」、误触的「离开游戏?」
            if (pts:=action.locate(screen.copy(),self.imgs['jujue'],0)):
                h,w=self.imgs['jujue'][0].shape[:2]
                action.touch(action.cheat(pts[0],w,h-10),self.thread_id)
                if self.sleep_fast(1): return
                continue
            if (p:=self.qj_seen(screen,'qj_xs_jujue')):
                self.qj_tap(p)
                if self.sleep_fast(1.5): return
                continue
            if self.qj_seen(screen,'qj_likai'):
                self.message_output('「离开游戏?」→ 取消')
                self.qj_tap(LEAVE_CANCEL,2)
                if self.sleep_fast(1): return
                continue
            #符咒三选一(第 5/11/17 回合的备战阶段弹出，盖住顶栏，qj_phase 认不出)：点第一张。
            #点三次还在就不点了，存图等它超时
            if self.qj_seen(screen,'qj_fuzhou',FUZHOU_BOX):
                known_t=now
                if fz_n<3:
                    fz_n+=1
                    if fz_n==1: self.message_output('符咒三选一 → 选第一张')
                    self.qj_tap(FUZHOU_PICK,6)
                    if self.sleep_fast(1.5): return
                    continue
                if fz_n==3:
                    fz_n+=1
                    if shots<30:
                        path=self.qj_save_unknown(screen,shots); shots+=1
                        self.message_output('点了三次符咒还在，等它超时，已存 %s'%path)
                if self.sleep_fast(1): return
                continue
            fz_n=0
            #六道投票(匹配成功后、进对局前)：点第一个圆，每局只点一次(再点可能就取消了)
            if self.qj_seen(screen,'qj_liudao',LIUDAO_BOX):
                known_t=now
                if not ld_done:
                    ld_done=True
                    self.message_output('六道投票 → 选第一个')
                    self.qj_tap(LIUDAO_PICK,6)
                if self.sleep_fast(1): return
                continue
            #阵容预设面板：第一套是「应用」就点，变成「取消」= 已应用，点左上箭头关掉
            if self.qj_seen(screen,'qj_yushe',(0,0,300,70)):
                known_t=now
                if self.qj_seen(screen,'qj_quxiao',(940,80,1040,120)):
                    if not self.qj_applied: self.message_output('已应用第一套阵容预设')
                    self.qj_applied=True; self.qj_preset=True; self.qj_tap(PANEL_BACK,2)
                elif self.qj_seen(screen,'qj_yingyong',(940,80,1040,120)) and not self.qj_applied:
                    self.qj_tap((990,100),2)
                else:
                    self.qj_tap(PANEL_BACK,2)
                if self.sleep_fast(1.2): return
                continue
            #结算：「第N名」下的返回大厅 → 点击空白处继续 → 排名页的返回大厅
            hit=None
            for name in ('qj_back1','qj_back2','qj_cont'):
                if (p:=self.qj_seen(screen,name)):
                    hit=p; break
            if hit:
                known_t=now; end_t=now
                if ingame:
                    ingame=False; phase=None; self.qj_round_log()
                    self.message_output('第 %d 局结束'%self.qj_games)
                self.qj_tap(hit)
                if self.sleep_fast(2): return
                continue
            #大厅
            if self.qj_seen(screen,'qj_lobby',(80,0,300,70)):
                known_t=now; end_t=0; blank_n=0; ld_done=False
                if ingame:
                    ingame=False; phase=None; self.message_output('回到大厅')
                if self.qj_games>=self.cishu_max and not zhan_t:
                    self.message_output('已打 %d 局，达到次数上限，停止'%self.qj_games)
                    return
                if self.qj_coin_full(screen):
                    self.message_output('本周鼬乐币已满 600/600，停止')
                    return
                if zhan_t and now-zhan_t>240:
                    self.message_output('点「战」后 4 分钟没进对局，停止(匹配卡住了？)')
                    return
                if not zhan_t and (p:=self.qj_seen(screen,'qj_zhan',(980,480,1136,640))):
                    self.message_output('开始匹配：第 %d/%s 局'%(self.qj_games+1,self.cishu_max))
                    self.qj_tap(p,6); zhan_t=now
                if self.sleep_fast(1): return
                continue
            #局内
            p=self.qj_phase(screen)
            if p:
                known_t=now
                if not ingame:
                    ingame=True; zhan_t=0; self.qj_games+=1; self.qj_new_game()
                    self.message_output('第 %d 局：进入对局'%self.qj_games)
                if p=='bei':
                    if phase!='bei': self.qj_new_round()
                    phase=p
                    if self.qj_prepare(screen): return
                else:
                    if phase=='bei': self.qj_round_log()
                    phase=p
                    if self.sleep_fast(1): return
                continue
            #都不认识：加载、匹配成功、符咒/六道这类还没有模板的页面。结算后的奖励页点空白继续
            if end_t and now-end_t<90 and now-known_t>8 and blank_n<5:
                blank_n+=1; self.qj_tap((568,600),10)
                if self.sleep_fast(2): return
                continue
            if now-known_t>20 and shots<30 and now-shot_t>30:
                path=self.qj_save_unknown(screen,shots); shots+=1; shot_t=now
                self.message_output('%d 秒没认出画面，已存 %s'%(int(now-known_t),path))
            if self.sleep_fast(0.5): return
