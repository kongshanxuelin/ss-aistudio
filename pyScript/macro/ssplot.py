import os, sys, json, datetime
from copy import deepcopy
from sslog import sslogger, close_log_queue
try:
    import matplotlib.pyplot as plt
    import matplotlib
    from matplotlib import font_manager
    from matplotlib.widgets import Button, CheckButtons, Cursor
    import matplotlib.patches as mptch
    #import matplotlib.dates as mdates
    from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MONDAY,YEARLY
    import numpy as np
    import AnnotatedCursor
except Exception as e:
    sslogger.error(str(e))

#E:\> cd sdmp3-client?master?\Build\Debug\pyScript
class SSPlotHolder:
    def __init__(self) -> None:
        self.vecX = []
        self.mapData = {}
        # self.vecYLabel = []   #vecY 外层的标签
        self.title = ""
        self.xlabel = ""
        self.ylabel = ""
        self.vecTwin = []
        self.annoCursor: AnnotatedCursor = None
        self.zoomLevel = 4
        self.zoomVec = [0.1, 0.2, 0.4, 0.8, 1, 1.25, 1.5, 2, 4, 8, 12, 20, 40, 100]
        self.xlim_min = 0
        self.xlim_max = 0
        self.ylim_min = 0
        self.ylim_max = 0
        self.dragging_zoom = False
        self.dragging_startx = 0
        self.dragging_starty = 0
        self.dragging_rect = None

        self.invert_yaxis = False

    def to_timestamp(self, date: str)->int:
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        return date_obj.timestamp()
    
    def to_timestr(self, timestamp: int)->str:
        date_obj = datetime.datetime.fromtimestamp(timestamp)
        date = datetime.datetime.strftime(date_obj, '%Y-%m-%d')
        return date

    def Print(self):
        print("title: ", self.title)
        # print("vecYLabel: ", self.vecYLabel)
        print("xlabel: ", self.xlabel)
        print("ylabel: ", self.ylabel)
        # print("vecX: ", self.vecX)
        print("mapData size: ", len(self.mapData))

    def LoadFromFile(self, file):
        with open(file, 'r', encoding='utf-8') as file:
            file_content = file.read()

        vRoot = json.loads(file_content)
        self.title = vRoot["title"]
        self.xlabel = vRoot["xlabel"]
        self.ylabel = vRoot["ylabel"]
        self.mapData = vRoot["plotdata"]
    
    def GetColorByIndex(self, index: int):
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
                  , '#b4771f', '#0e7fff', '#2ca02c', '#2827d6', '#bd6794', '#4b568c', '#c277e3', '#347f89', '#a2bdbc', '#ffbe47']
        maxIndex = len(colors)
        index = index % maxIndex
        return colors[index]

    def _ShowPlot(self, fig, ax):
        sslogger.info(f"_ShowPlot")
        plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment='right')

        colorIndex = 0
        plot_size = len(self.mapData)
        sslogger.info(f"len(self.mapData)={plot_size}")
        ax2 = None
        xticks_tm = []
        mapLine = {}
        ylimMin = 0
        ylimMax = 0
        for gjkCode, vData in self.mapData.items():
            vecX = vData["dates"]
            vecTm = [self.to_timestamp(x) for x in vecX]
            vecY = vData["values"]
            xticks_tm = list(set(xticks_tm + vecTm))
            if gjkCode in self.vecTwin:
                axes = fig.get_axes()
                if len(axes) == 3:
                    ax2 = ax.twinx()
                    ax2.set_ylabel("次坐标轴")
                elif len(axes) == 4:
                    ax2 = axes[3]
                line, = ax2.plot(vecTm, vecY, '.-', label=gjkCode, color=self.GetColorByIndex(colorIndex))
            else:
                # sslogger.info(vecX)
                line, = ax.plot(vecTm, vecY, '.-', label=gjkCode, color=self.GetColorByIndex(colorIndex))  
            colorIndex += 1
            ylimMinTmp = min(vecY)
            ylimMaxTmp = max(vecY)
            if ylimMin == 0 or ylimMinTmp < ylimMin:
                ylimMin = ylimMinTmp
            if ylimMax == 0 or ylimMaxTmp > ylimMax:
                ylimMax = ylimMaxTmp
            if self.annoCursor is None:
                mapLine[gjkCode] = line
            
        xticks_tm.sort()
        sslogger.info(xticks_tm)

        if self.xlim_min == 0  and self.xlim_max == 0 and len(xticks_tm) > 0:
            self.xlim_min = xticks_tm[0]
            self.xlim_max = xticks_tm[-1]
        self.ylim_min = ylimMin
        self.ylim_max = ylimMax
        sslogger.info(f"xlim_min:{self.xlim_min}, xlim_max:{self.xlim_max}, ylim_min:{self.ylim_min}, ylim_max:{self.ylim_max}")

        if self.annoCursor is None:
            xticks_tm_copy = deepcopy(xticks_tm)
        while len(xticks_tm) > 24:
            xticks_tm = [x for i, x in enumerate(xticks_tm)  if i % 2 == 0 ]
        sslogger.info(xticks_tm)

        xticks = [self.to_timestr(x) for x in xticks_tm]
        sslogger.info(xticks)
        ax.set_xticks(xticks_tm, xticks) 

        ax.set_xlabel(self.xlabel)  # Add an x-label to the axes.
        ax.set_ylabel(self.ylabel)  # Add a y-label to the axes.
        ax.set_title(self.title)  # Add a title to the axes.  添加轴域对象标题
        
        ax.grid(color='b', ls = '-.', lw = 0.15)
        ax.legend(bbox_to_anchor=(0.004, 1), loc='upper left', borderaxespad=0.)

        if ax2 is not None:
            sslogger.info("ax2.legend()")
            ax2.legend(bbox_to_anchor=(0.842, 1), loc='upper left', borderaxespad=0.)

        axCursor = ax
        if ax2 is not None:
            axCursor = ax2      #如果用ax, AnnotatedCursor::onmove中, 会进这个判断event.inaxes != self.ax, 并return
        if self.annoCursor is None:
            sslogger.info("Create AnnotatedCursor")
            sslogger.info(f"mapLine keys:{mapLine.keys()}")
            self.annoCursor = AnnotatedCursor.AnnotatedCursor(
                xticks=xticks_tm_copy,
                mapLine=mapLine,
                numberformat="{0:.2f}\n{1:.2f}",
                dataaxis='x', offset=[10, 10],
                textprops={'color': 'black', 'fontweight': 'bold'},
                ax=axCursor,
                useblit=True,
                color='grey',
                linewidth=0.4)

        plt.show(block=True)
        
    def ShowPlot(self):
        sslogger.info(f"ShowPlot")
        plt.rcParams['font.sans-serif'] = ['SimSun']
        fig, ax = plt.subplots(figsize=(12, 6))
        plt.subplots_adjust(left=0.24, right=0.94, top=0.95, bottom=0.10)
        print(ax)
        
        rc = [0.02, 0.92, 0.08, 0.04]
        ax_btn = plt.axes(rc)
        btnTest1 = Button(ax_btn, '倒序', color='lightblue')

        def onBtn1Click(event):
            self.invert_yaxis = not self.invert_yaxis
            ax.invert_yaxis()
            fig.canvas.draw()
        btnTest1.on_clicked(onBtn1Click)

        def onCheckClick(gjkCode: str):
            if gjkCode in self.vecTwin:
                self.vecTwin.remove(gjkCode)
            else:
                self.vecTwin.append(gjkCode)
            print(self.vecTwin)

            vecAxes = fig.get_axes()
            print(len(vecAxes))
            if len(vecAxes) == 3:
                vecAxes[0].clear()
            elif len(vecAxes) == 4:
                fig.delaxes(vecAxes[3])
                vecAxes[0].clear()
            del(self.annoCursor)
            self.annoCursor = None

            self._ShowPlot(fig, ax)
            fig.canvas.draw()

        # plot_size = len(self.mapData)
        gjkCodes = []
        for gjkCode, _ in self.mapData.items():
            gjkCodes.append(gjkCode)
        rc = [0.02, 0.92 -  0.03 * len(gjkCodes) - 0.01, 0.16, 0.03 * len(gjkCodes)]
        ax_check = plt.axes(rc)
        print(gjkCodes)
        btnCheck = CheckButtons(ax_check, gjkCodes)
        btnCheck.on_clicked(onCheckClick)

        def scroll_event(event):
            if event.button == "down":
                self.zoomLevel -= 1
            elif event.button == "up":
                self.zoomLevel += 1
            if self.zoomLevel < 0:
                self.zoomLevel = 0
            if self.zoomLevel >= len(self.zoomVec):
                self.zoomLevel = len(self.zoomVec) - 1
            xlim_min = self.xlim_min * self.zoomVec[self.zoomLevel] * 0.8
            xlim_max = self.xlim_max * self.zoomVec[self.zoomLevel] * 1.04
            if xlim_min < xlim_max:
                ax.set_xlim(xlim_min, xlim_max)
                fig.canvas.draw()
        # fig.canvas.mpl_connect('scroll_event', scroll_event)

        def mouse_click_event(event):
            if event.inaxes is None:
               return
            if len(self.vecTwin) > 0:
                return
            if event.button == 3:       #右键
                if self.xlim_min < self.xlim_max and self.ylim_min < self.ylim_max:
                    disx = self.xlim_max - self.xlim_min
                    disy = self.ylim_max - self.ylim_min
                    ax.set_xlim(self.xlim_min - disx/20, self.xlim_max + disx/20)
                    # ax.set_ylim(self.ylim_min - disy/20, self.ylim_max + disy/20)
                    if self.invert_yaxis:
                        ax.set_ylim(self.ylim_max + disy/20, self.ylim_min - disy/20)
                    else:
                        ax.set_ylim(self.ylim_min - disy/20, self.ylim_max + disy/20)
                    fig.canvas.draw()
            elif event.button == 1:     #左键
               self.dragging_zoom = True
               self.dragging_startx = event.xdata
               self.dragging_starty = event.ydata
               print(f"start drag {self.dragging_startx},{self.dragging_starty}")
               if self.annoCursor is not None:
                   self.annoCursor.set_disable(True)
        fig.canvas.mpl_connect('button_press_event', mouse_click_event)

        def mouse_click_release(event):
            print(f"stop drag")
            if self.dragging_zoom:
                startx = self.dragging_startx
                starty = self.dragging_starty
                endx = event.xdata
                endy = event.ydata
                if startx > endx:
                    print(startx, endx)
                    startx, endx = endx, startx
                    print(startx, endx)
                if starty > endy:
                    print(starty, endy)
                    starty, endy = endy, starty
                    print(starty, endy)
                print(f"startx:{startx}, starty:{starty}, endx:{endx}, endy:{endy}")
                if startx < self.xlim_min:
                    startx = self.xlim_min
                if endx > self.xlim_max:
                    endx = self.xlim_max
                if starty < self.ylim_min:
                    starty = self.ylim_min
                if endy > self.ylim_max:
                    endy = self.ylim_max
                print(f"startx:{startx}, starty:{starty}, endx:{endx}, endy:{endy}")

                start_pt = ax.transData.transform((startx, starty))
                end_pt = ax.transData.transform((endx, endy))
                print(f"start_pt:{start_pt}, end_pt:{end_pt}")
                if end_pt[0] - start_pt[0] > 30:
                    disx = endx - startx
                    disy = endy - starty
                    ax.set_xlim(startx - disx/20, endx + disx/20)
                    if self.invert_yaxis:
                        ax.set_ylim(endy+ disy/20, starty - disy/20)
                    else:
                        ax.set_ylim(starty - disy/20, endy+ disy/20)
                    fig.canvas.draw()
                
            self.dragging_zoom = False
            if self.dragging_rect is not None:
                self.dragging_rect.remove()
                self.dragging_rect = None
            if self.annoCursor is not None:
                self.annoCursor.set_disable(False)
        fig.canvas.mpl_connect("button_release_event", mouse_click_release)

        def mouse_move(event):
            if event.inaxes is None:
                return
            if not self.dragging_zoom:
                return
            print("mouse_move")

            startx = self.dragging_startx
            starty = self.dragging_starty
            endx = event.xdata
            endy = event.ydata
            if startx > endx:
                startx, endx = endx, startx
            if starty > endy:
                starty, endy = endy, starty
            print(f"startx:{startx}, starty:{starty}, endx:{endx}, endy:{endy}")
            if startx < self.xlim_min:
                startx = self.xlim_min
            if endx > self.xlim_max:
                endx = self.xlim_max
            if starty < self.ylim_min:
                starty = self.ylim_min
            if endy > self.ylim_max:
                endy = self.ylim_max
            print(f"startx:{startx}, starty:{starty}, endx:{endx}, endy:{endy}")
            if self.dragging_rect is not None:
                self.dragging_rect.remove()
            dragging_rect = mptch.Rectangle((startx, starty), 
                            width = endx - startx, 
                            height = endy - starty, 
                            linewidth=0.6, 
                            edgecolor='gray', 
                            facecolor='none'
                            )
            self.dragging_rect = ax.add_patch(dragging_rect)
            fig.canvas.draw()
        fig.canvas.mpl_connect("motion_notify_event", mouse_move)

        self._ShowPlot(fig, ax)

    def TestPlot_MouseCursor(self):
        from matplotlib.backend_tools import Cursors
        fig, axs = plt.subplots(len(Cursors), figsize=(6, len(Cursors) + 0.5), gridspec_kw={'hspace': 0})
        fig.suptitle('Hover over an Axes to see alternate Cursors')
        for cursor, ax in zip(Cursors, axs):
            ax.cursor_to_use = cursor
            ax.text(0.5, 0.5, cursor.name,
                    horizontalalignment='center', verticalalignment='center')
            ax.set(xticks=[], yticks=[])
        def hover(event):
            if fig.canvas.widgetlock.locked():
                # Don't do anything if the zoom/pan tools have been enabled.
                return
            fig.canvas.set_cursor(
                event.inaxes.cursor_to_use if event.inaxes else Cursors.POINTER)
        fig.canvas.mpl_connect('motion_notify_event', hover)
        plt.show()

def main():
    sslogger.info(f"sys.argv: {sys.argv}")
    
    scriypFile = ""
    dataFile = ""
    debug = ""
    if len(sys.argv) > 0:
        scriypFile = sys.argv[0]
    if len(sys.argv) > 1:
        dataFile = sys.argv[1]
    if len(sys.argv) > 2:
        debug = sys.argv[2]
    # sslogger.info(scriypFile)

    if len(dataFile) == 0 :
        dataFile = os.path.dirname(scriypFile) + "\\data.dat"

    if debug == "Debug":
        path = os.getenv("path")
        pyHome = os.getenv("PYTHONHOME")
        pyPath = os.getenv("PYTHONPATH")
        sslogger.info(f"Env Path: {path}")
        sslogger.info(f"Env PYTHONHOME: {pyHome}")
        sslogger.info(f"Env PYTHONPATH: {pyPath}")

    plot = SSPlotHolder()
    plot.LoadFromFile(dataFile)
    plot.Print()
    plot.ShowPlot()

    # plot.TestPlot3D()
    # plot.TestPlot_xTick()
    # plot.TestPlot_MouseCursor()

    

if __name__ == '__main__':
    main()
    close_log_queue()