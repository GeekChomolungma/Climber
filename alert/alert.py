import win32gui
import win32api
import win32con
import time
import win32clipboard as w

def FindWindow(chatroom):
    win = win32gui.FindWindow(None, chatroom)
    if win != 0:
        win32gui.ShowWindow(win, win32con.SW_SHOWMINIMIZED)
        win32gui.ShowWindow(win, win32con.SW_SHOWNORMAL)
        win32gui.ShowWindow(win, win32con.SW_SHOW)
        win32gui.SetWindowPos(win, win32con.HWND_TOPMOST, 100, 100, 500, 500, win32con.SWP_SHOWWINDOW)#第二个参数是置顶，前两个数字是位置，后两个数字是大小，最后一个是显示
        win32gui.SetForegroundWindow(win)  # 获取控制
        time.sleep(0.5)
    else:
        print('找不到该窗口，请双击联系人，保证其是一个单独的窗口' % chatroom)
        # exit()
# def CloseWindow(chatroom):
#     win = win32gui.FindWindow(None, chatroom)
#     #print("找到关闭窗口：%x" % win)
#     time.sleep(3)
#     win32gui.ShowWindow(win, win32con.SW_SHOWMINIMIZED)
def setText(aString):
    w.OpenClipboard()
    w.EmptyClipboard()
    w.SetClipboardData(win32con.CF_UNICODETEXT, aString)
    w.CloseClipboard()
def zhanTie():
    win32api.keybd_event(17, 0, 0, 0)  # ctrl键位码是17
    win32api.keybd_event(86, 0, 0, 0)  # v键位码是86
    win32api.keybd_event(86, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放按键
    win32api.keybd_event(17, 0, win32con.KEYEVENTF_KEYUP, 0)
def huiche():
    win32api.keybd_event(18, 0, 0, 0)  # Alt键位码
    win32api.keybd_event(83, 0, 0, 0)  # s键位码
    win32api.keybd_event(18, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放按键
    win32api.keybd_event(83, 0, win32con.KEYEVENTF_KEYUP, 0)
def sendText(chatrooms,text):
    for chatroom in chatrooms:
        FindWindow(chatroom)
        setText(" "+text)
        zhanTie()
        huiche()

def Alert(text):
    sendText(['险峰创世'],text)

#方法2，直接发消息，不需要复制粘贴
#handle = win32gui.FindWindow(None, '劳模')
#win32gui.SetForegroundWindow(handle)
#st=[ord(s) for s in '中国']
#for x in st:
#    win32gui.PostMessage(handle,win32con.WM_CHAR,x,0)
#    huiche()
