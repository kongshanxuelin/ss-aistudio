import os, sys
import datetime
from sslog import sslogger, close_log_queue
import ssplot

def main():
    scriypFile = ""
    dataFile = ""
    debug = ""
    if len(sys.argv) > 0:
        scriypFile = sys.argv[0]
    if len(sys.argv) > 1:
        dataFile = sys.argv[1]
    if len(sys.argv) > 2:
        debug = sys.argv[2]
    print(scriypFile)
    sslogger.info(scriypFile)

    if len(dataFile) == 0 :
        dataFile = os.path.dirname(scriypFile) + "\\data.dat"
    #print(dataFile)
    sslogger.info(dataFile)
    sslogger.info(f"debug: {debug}")

    if debug == "Debug":
        path = os.getenv("path")
        pyHome = os.getenv("PYTHONHOME")
        pyPath = os.getenv("PYTHONPATH")
        sslogger.info(f"Env Path: {path}")
        sslogger.info(f"Env PYTHONHOME: {pyHome}")
        sslogger.info(f"Env PYTHONPATH: {pyPath}")

    try:
        plot = ssplot.SSPlotHolder()
        plot.LoadFromFile(dataFile)
        plot.Print()
        plot.ShowPlot()
    except Exception as e:
        sslogger.error(str(e))
    close_log_queue()

if __name__ == '__main__':
    main()
    