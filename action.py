import cv2,time,os,random,sys,mss,copy,subprocess,shutil,pyautogui
import numpy
from PyQt6.QtWidgets import QMessageBox,QPushButton,QInputDialog,QFileDialog

#global variables
devices_tab=[None]
adb_enable=[False]
adb_path=None
config=None     #main.py 读完 config.ini 后赋值(configparser.ConfigParser)，给可选配置项用
scalar=False
scaling_factor=1
monitor=None
#截屏，并裁剪以加速
upleft = (0, 0)
downright = (1136, 700)
#默认桌面版
if sys.platform=='darwin':
    scalar=True
    scaling_factor=1/2
else:
    scalar=False
    scaling_factor=1
a,b = upleft
c,d = downright
monitor = {"top": b, "left": a, "width": c, "height": d}

#读 config.ini 里的可选项；没写、留空、没有这一节都返回 fallback
def config_get(section,key,fallback=None):
    try:
        value=config.get(section,key,fallback=fallback) if config is not None else fallback
    except Exception:
        return fallback
    if isinstance(value,str):
        value=value.strip()
        if value=='':
            return fallback
    return value

#跑 adb 这类命令行工具。打包成窗口程序后，win32 上每个子进程都会弹一下黑色控制台，这里统一隐藏
def _run(comm,**kwargs):
    if sys.platform=='win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault('startupinfo',startupinfo)
        kwargs.setdefault('creationflags',subprocess.CREATE_NO_WINDOW)
    return subprocess.run(comm,shell=False,**kwargs)

def adb_connect(addr):
    try:
        out=_run([adb_path,'connect',addr],capture_output=True,check=False)
        return out.stdout.decode('utf-8',errors='replace').strip()
    except Exception as e:
        return 'ADB error: '+str(e)

def adb_devices():
    try:
        out=_run([adb_path,'devices'],capture_output=True,check=False)
        return out.stdout.decode('utf-8',errors='replace')
    except Exception as e:
        return 'ADB error: '+str(e)

#从 adb devices 的输出里挑出在线的设备
def parse_devices(out):
    devices=[]
    for line in out.splitlines()[1:]:
        device=line.split()
        if len(device)==2 and device[1]=='device':
            devices.append(device[0])
    return devices

#initialization thread
def init_thread_variable(nthread):
    global devices_tab,adb_enable
    devices_tab=[None]*nthread
    adb_enable=[False]*nthread

def startup(window):
    global scalar,scaling_factor,monitor,adb_enable,adb_path,devices_tab
    thread_id=window.tabWidget.currentIndex()
    textBrowser=window.tab[thread_id].textBrowser
    pushButton_restart=window.tab[thread_id].pushButton_restart
    #config.ini 可手动指定 adb_path(adb 可执行文件)和 adb_address(模拟器 ip:端口)，自动检测失败时用
    cfg_adb=config_get('general','adb_path')
    addr=config_get('general','adb_address')
    mumu=False
    #检测ADB
    if cfg_adb:
        adb_path=cfg_adb
        textBrowser.append('使用config.ini指定的adb：'+adb_path)
    elif sys.platform=='win32':
        adb_path=None
        textBrowser.append('检测模拟器')
        path_list = ["C:\\Program Files\\Netease\\MuMuPlayer-12.0\\shell\\adb.exe", "C:\\Program Files\\Netease\\MuMu\\nx_main\\adb.exe", "C:\\leidian\\LDPlayer9\\adb.exe"]
        for id_path in path_list:
            if os.path.isfile(id_path):
                adb_path=id_path
                if 'MuMu' in id_path:
                    textBrowser.append('检测到MuMu模拟器')
                    mumu=True
                elif 'LD' in id_path:
                    textBrowser.append('检测到雷电模拟器')
                break
        if adb_path==None:
            #模拟器装在别的路径：先找 PATH 里的 adb，再让用户自己选
            adb_path=shutil.which('adb')
            if adb_path:
                textBrowser.append('未找到模拟器安装路径，使用PATH里的adb：'+adb_path)
            else:
                textBrowser.append('未找到adb.exe，请在弹窗里选择模拟器目录下的adb.exe（MuMu在安装目录的shell文件夹里）')
                path,_=QFileDialog.getOpenFileName(window,'选择模拟器目录里的adb.exe','C:\\','adb.exe (adb.exe);;所有文件 (*)')
                adb_path=path if path else 'adb'
    else:
        adb_path='adb'

    #连接模拟器：config.ini 的 adb_address > MuMu 端口弹窗 > 检测不到设备时弹窗问地址
    #（雷电/真机会被 adb 自动发现，不需要 connect）
    if not addr and mumu:
        port, ok = QInputDialog.getInt(window, '模拟器端口', '输入MuMu模拟器端口（默认16384，多开每个+32）：',16384,0,65535,1)
        if ok:
            addr='127.0.0.1:'+str(port)
    if addr:
        textBrowser.append(f'连接 {addr}：'+adb_connect(addr))
    out=adb_devices()
    textBrowser.append(out)
    devices=parse_devices(out)
    if len(devices)==0 and not addr:
        addr, ok = QInputDialog.getText(window, '模拟器ADB地址',
            '未检测到ADB设备。输入模拟器的ADB地址后重试\n（MuMu默认 127.0.0.1:16384，多开每个+32，可在MuMu的「问题诊断」里查看）。\n取消则使用桌面版：', text='127.0.0.1:16384')
        addr=addr.strip() if ok else ''
        if addr:
            textBrowser.append(f'连接 {addr}：'+adb_connect(addr))
            out=adb_devices()
            textBrowser.append(out)
            devices=parse_devices(out)
    #存在ADB设备
    if len(devices)>0:
        #如果存在多个ADB设备，选择其中一个
        if len(devices)==1:
            device=devices[0]
        else:
            #popup window
            msg_box = QMessageBox()
            msg_box.setText("选择安卓设备")
            # Change the button texts
            for device in devices:
                button = QPushButton(device)
                msg_box.addButton(button, QMessageBox.ButtonRole.ActionRole)
            msg_box.exec()
            clicked = msg_box.clickedButton()
            device = clicked.text() if clicked is not None else devices[0]
        textBrowser.append('监测到ADB设备，默认使用安卓截图')
        devices_tab[thread_id]=device
        adb_enable[thread_id]=True
        #change resolution
        screen=screenshot(thread_id)
        if not (isinstance(screen, int) and screen == -1):
            w=screen.shape[0]
            h=screen.shape[1]
            textBrowser.append(f'使用设备：{device}')
            window.tabWidget.setTabText(thread_id, f'设备{thread_id+1}：{device}')
            pushButton_restart.setText('断开ADB')
        else:
            #截屏失败
            textBrowser.append('截屏失败，断开ADB')
            devices_tab[thread_id]=None
            adb_enable[thread_id]=False
            return
        textBrowser.append(f'原始分辨率：{w}x{h}')
        if (w==640 and h==1136) or (h==640 and w==1136):
            textBrowser.append('无需修改分辨率')
        else:
            if w>h:
                comm=[adb_path,"-s",device,"shell","wm","size","1136x640"]
                _run(comm)
                textBrowser.append('修改成桌面版分辨率: 1136x640')
            elif w<=h:
                comm=[adb_path,"-s",device,"shell","wm","size","640x1136"]
                _run(comm)
                textBrowser.append('修改成桌面版分辨率: 640x1136')
    else:
        textBrowser.append('未监测到ADB设备，默认使用桌面版')
        textBrowser.append('请把桌面版窗口移动到第一个屏幕的左上角')
        adb_enable[thread_id]=False
        pyautogui.FAILSAFE=False

    #检测系统
    if sys.platform=='darwin' and not adb_enable[thread_id]:
        scalar=True
        scaling_factor=1/2
    else:
        scalar=False
        scaling_factor=1

    #截屏，并裁剪以加速
    upleft = (0, 0)
    if scalar==True:
        downright = (1136,750)
    else:
        downright = (1136, 700)
    a,b = upleft
    c,d = downright
    monitor = {"top": b, "left": a, "width": c, "height": d}

def reset_resolution(window):
    global adb_enable, devices_tab, adb_path
    thread_id = window.tabWidget.currentIndex()
    textBrowser=window.tab[thread_id].textBrowser
    pushButton_restart=window.tab[thread_id].pushButton_restart
    if adb_enable[thread_id]:
        textBrowser.append('重置安卓分辨率')
        comm=[adb_path,"-s",devices_tab[thread_id],"shell","wm","size","reset"]
        _run(comm)
        #remove device info
        devices_tab[thread_id]=None
        adb_enable[thread_id]=False
        #日志更新
        textBrowser.append('已断开连接')
        window.tabWidget.setTabText(thread_id, f'设备{thread_id+1}：桌面版')
        pushButton_restart.setText('连接ADB')

def screenshot(thread_id):
    #ADB截屏
    if adb_enable[thread_id]:
        if not devices_tab[thread_id]:
            return -1
        comm=[adb_path,"-s",devices_tab[thread_id],"shell","screencap","-p"]
        try:
            image_bytes = _run(comm,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
        except Exception:
            #adb 本身跑不起来(模拟器重启、adb 被卸载等)
            return -1
        image_array=numpy.frombuffer(image_bytes, numpy.uint8)
        #sometime numpy returns empty
        if image_array.size != 0:
            screen=cv2.imdecode(image_array,cv2.IMREAD_COLOR)
        else:
            screen=None
        if screen is None:
            image_bytes = image_bytes.replace(b'\r\n', b'\n')
            image_array=numpy.frombuffer(image_bytes, numpy.uint8)
            if image_array.size == 0:
                #截图失败
                return -1
            else:
                screen = cv2.imdecode(image_array,cv2.IMREAD_COLOR)
    else:
        #桌面版截屏
        with mss.mss() as sct:
            if scalar:
                #{"top": b, "left": a, "width": c, "height": d}
                #shrink monitor to half due to macOS default DPI scaling
                monitor2=copy.deepcopy(monitor)
                monitor2["width"]=int(monitor2["width"]*scaling_factor)
                monitor2["height"]=int(monitor2["height"]*scaling_factor)
                screen=sct.grab(monitor2)
                #mss.tools.to_png(screen.rgb, screen.size, output="screenshot.png")
                screen = numpy.array(screen)
                #textBrowser.append('Screen size: ',screen.shape)
                #MuMu助手默认拉伸4/3倍
                screen = cv2.resize(screen, (int(screen.shape[1]*0.75), int(screen.shape[0]*0.75)),
                                    interpolation = cv2.INTER_LINEAR)
            else:
                screen = numpy.array(sct.grab(monitor))

    #all else failed
    if screen is None:
        return screen
    screen = cv2.cvtColor(screen, cv2.COLOR_BGR2RGB)
    return screen

#在背景查找目标图片，并返回查找到的结果坐标列表，target是背景，want是要找目标
def locate(target,want, show=bool(0), msg=bool(0)):
    loc_pos=[]
    want,treshold,c_name=want[0],want[1],want[2]
    #screenshot() 失败时返回的是 -1 而不是图片；直接送进 matchTemplate 会抛异常，整个界面进程跟着崩
    if target is None or not isinstance(target,numpy.ndarray):
        return loc_pos
    result=cv2.matchTemplate(target,want,cv2.TM_CCOEFF_NORMED)
    location=numpy.where(result>=treshold)
    #textBrowser.append(location)

    if msg:  #显示正式寻找目标名称，调试时开启
        textBrowser.append(c_name,'searching... ')

    h,w=want.shape[:-1] #want.shape[:-1]

    n,ex,ey=1,0,0
    for pt in zip(*location[::-1]):    #其实这里经常是空的
        x,y=pt[0]+int(w/2),pt[1]+int(h/2)
        if (x-ex)+(y-ey)<15:  #去掉邻近重复的点
            continue
        ex,ey=x,y

        cv2.circle(target,(x,y),10,(0,0,255),3)

        if msg:
            textBrowser.append(c_name,'we find it !!! ,at',x,y)

        if scalar:
            x,y=int(x*scaling_factor),int(y*scaling_factor)
        else:
            x,y=int(x),int(y)

        loc_pos.append([x,y])

    if show:  #在图上显示寻找的结果，调试时开启
        textBrowser.append('Debug: show action.locate')
        cv2.imshow('we get',target)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    if len(loc_pos)==0:
        #textBrowser.append(c_name,'not find')
        pass

    return loc_pos

#数目标在画面上出现了几处(阈值以上区域的连通块数)。locate 的去重只对扫描顺序相邻的点有效，
#换行后左边的目标会被误当成重复点，数 3x3 结界板上的进攻按钮会漏，所以另写一个。不在图上画圈
#TM_CCOEFF_NORMED 对颜色不敏感(橙色进攻按钮对灰色的也能到 0.93)，所以每处再比一下平均颜色，要和模板相近
def count(target,want,color_tol=50):
    if target is None or not isinstance(target,numpy.ndarray):
        return 0
    tpl=want[0]
    h,w=tpl.shape[:2]
    result=cv2.matchTemplate(target,tpl,cv2.TM_CCOEFF_NORMED)
    mask=(result>=want[1]).astype(numpy.uint8)
    n,labels=cv2.connectedComponents(mask)
    tpl_mean=tpl.reshape(-1,3).mean(axis=0)
    found=0
    for k in range(1,n):
        ys,xs=numpy.where(labels==k)
        #这一块里分数最高的点
        i=numpy.argmax(result[ys,xs])
        y,x=int(ys[i]),int(xs[i])
        patch=target[y:y+h,x:x+w].reshape(-1,3).mean(axis=0)
        if numpy.abs(patch-tpl_mean).max()<=color_tol:
            found=found+1
    return found

#按【文件内容，匹配精度，名称】格式批量聚聚要查找的目标图片，精度统一为0.95，名称为文件名
def load_imgs(game_name):
    mubiao = {}
    acc=0.95
    # Determine base path: when frozen by PyInstaller, resources are unpacked to _MEIPASS
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(base, game_name, 'png')
    if not os.path.isdir(path):
        # Fall back to cwd-based path for compatibility
        path = os.path.join(os.getcwd(), game_name, 'png')
    try:
        file_list = os.listdir(path)
    except Exception:
        return mubiao
    for file in file_list:
        if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        name = file.split('.')[0]
        file_path = path + '/' + file
        a = [cv2.cvtColor(cv2.imread(file_path),cv2.COLOR_BGR2RGB),acc,name]
        mubiao[name] = a
    return mubiao

#蜂鸣报警器，参数n为鸣叫次数
def alarm(n):
    frequency = 1500
    duration = 500

    if os.name=='nt':
        import winsound
        winsound.Beep(frequency, duration)
    else:
        #os.system('afplay /System/Library/Sounds/Sosumi.aiff')
        sys.stdout.write('\a')
        sys.stdout.flush()

#裁剪图片以缩小匹配范围，screen为原图内容，upleft、downright是目标区域的左上角、右下角坐标
def cut(screen,upleft,downright):

    a,b=upleft
    c,d=downright
    screen=screen[b:d,a:c]

    return screen

#随机偏移坐标，防止游戏的外挂检测。p是原坐标，w、n是目标图像宽高，返回目标范围内的一个随机坐标
def cheat(p, w, h):
    a,b = p
    if scalar:
        w, h = int(w/3/2), int(h/3/2)
    else:
        w, h = int(w/3), int(h/3)
    if h<0:
        h=1
    c,d = random.randint(-w, w),random.randint(-h, h)
    e,f = a + c, b + d
    y = [e, f]
    return(y)

# 点击屏幕，参数pos为目标坐标
def touch(pos,thread_id):
    x, y = pos
    if adb_enable[thread_id]:
        comm=[adb_path,"-s",devices_tab[thread_id],"shell","input","tap",str(x),str(y)]
        #textBrowser.append('Command: ',comm)
        _run(comm)
    else:
        pyautogui.click(pos)




def swipe(pos,thread_id,dy):
    x, y = pos
    x1=x
    if y>dy:
        y1=y-dy
    else:
        y1=1

    if adb_enable[thread_id]:
        comm=[adb_path,"-s",devices_tab[thread_id],"shell","input","touchscreen","swipe",str(x),str(y),str(x1),str(y1)]
        #print(comm)
        #textBrowser.append('Command: ',comm)
        _run(comm)
    else:
        # Move to the starting point and press the left mouse button
        pyautogui.moveTo(pos)
        pyautogui.mouseDown(button='left')

        # Drag the mouse to the ending point over 1 second
        pyautogui.dragTo(x, y1, duration=1)

        # Release the left mouse button
        pyautogui.mouseUp(button='left')
