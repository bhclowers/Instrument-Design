'''
## SRIG Layout: An Interactive Circuit Layout Tool for Ion Guides and Funnels
* BHC 05.Oct.2025
* [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html)
* This research product was developed with the support of the [NIGMS](https://www.nigms.nih.gov/) R01-GM140129

This is to be placed in the KiCAD 8 plugins folder. 

SAVE A COPY OF YOUR WORK BEFORE EXECUTING THIS SCRIPT

Finally, this does not wire the tracks for you.  That is something that you must do, though the wiring template can surely help as KiCAD
supports Copy and Paste along with grouping. 



'''


import pcbnew
from pcbnew import VECTOR2I, EDA_ANGLE
import re
import datetime
import wx
import os
import json
import csv

def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)

def dumpJSON(outputName, dataDict):
    # Serialization
    with open(outputName, "w") as write_file:
        json.dump(dataDict, write_file)
        print("Done Writing %s to disk"%outputName)
    
def restoreJSON(inputName):
    # Deserialization
    with open(inputName, "r") as read_file:
        dataDict = json.load(read_file)    
        print("Dont reading %s from disk"%inputName)
        return dataDict

def reportDialog(winFrame, message, caption = "Yo!"):
    dlg = wx.MessageDialog(winFrame, message, caption, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


def restoreCSV(inputName):
    """
    Read a CSV with columns: index, X, Y, ID, OD
    Return a dict keyed by stringified index, each value a dict with same keys as your JSON.
    """
    viaDict = {}
    with open(inputName, newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            k = str(int(row["index"]))  # keep behavior close to the JSON keys ("0","1",...)
            viaDict[k] = {
                "X": float(row["X"]),
                "Y": float(row["Y"]),
                "ID": float(row["ID"]),
                "OD": float(row["OD"]),
            }
    return viaDict

def restoreJSON(inputName):
    # Deserialization
    read_file = open(inputName, "r")
    dataDict = json.load(read_file)    
    print("Dont reading %s from disk"%inputName)
    return dataDict

def vec_from_point(pt):
    # pt is wxPoint-like with .x/.y
    return pcbnew.VECTOR2I(int(pt.x), int(pt.y))

def vec_from_size(sz):
    # sz is wxSize-like with .x/.y or .GetWidth()/.GetHeight()
    # wxSize in KiCad bindings usually exposes .x/.y too; fall back if needed.
    w = int(getattr(sz, "x", getattr(sz, "GetWidth")()))
    h = int(getattr(sz, "y", getattr(sz, "GetHeight")()))
    return pcbnew.VECTOR2I(w, h)


def create_via(board, net, xPos, yPos, drillSize, drillWidth, addMaskBool=True):
    newvia = pcbnew.PCB_VIA(board)
    board.Add(newvia)

    newPos = pcbnew.wxPointMM(xPos, yPos)
    newvia.SetPosition(vec_from_point(newPos))

    newvia.SetDrill(int(pcbnew.pcbIUScale.mmToIU(drillSize)))
    newvia.SetWidth(int(pcbnew.pcbIUScale.mmToIU(drillWidth)))
    newvia.SetLayerPair(board.GetLayerID('F.Cu'), board.GetLayerID('F.Cu'))
    newvia.SetViaType(pcbnew.VIATYPE_THROUGH)

    if addMaskBool:
        startX = int(pcbnew.pcbIUScale.mmToIU(xPos))
        circRadius = int(pcbnew.pcbIUScale.mmToIU(drillWidth/2)) + startX

        bMaskCir = pcbnew.PCB_SHAPE()
        bMaskCir.SetShape(pcbnew.S_CIRCLE)
        bMaskCir.SetLayer(pcbnew.B_Mask)
        bMaskCir.SetPosition(vec_from_point(newPos))
        bMaskCir.SetStartX(startX)
        bMaskCir.SetEndX(circRadius)
        bMaskCir.SetFilled(True)
        board.Add(bMaskCir)

        fMaskCir = pcbnew.PCB_SHAPE()
        fMaskCir.SetShape(pcbnew.S_CIRCLE)
        fMaskCir.SetLayer(pcbnew.F_Mask)
        fMaskCir.SetPosition(vec_from_point(newPos))
        fMaskCir.SetStartX(startX)
        fMaskCir.SetEndX(circRadius)
        fMaskCir.SetFilled(True)
        board.Add(fMaskCir)


def funnelFromCSV(winFrame, csvFile, xStep=1.880, yStep=1.630, numCols=10):
    viaDict = restoreCSV(csvFile)

    netDefault = '1'
    pcb = pcbnew.GetBoard()
    origin = pcbnew.wxPointMM(0, 0)

    yMod = 0
    m = 0
    curX = 0
    curY = 0

    # Keep consistent order by key as integers
    keyList = sorted(list(viaDict.keys()), key=lambda s: int(s))

    textLayer = pcbnew.F_SilkS
    textsize = pcbnew.wxSize(pcbnew.FromMM(4), pcbnew.FromMM(4))
    thickness = pcbnew.FromMM(0.5)

    for i, k in enumerate(keyList):
        if i > 0 and i % numCols == 0:
            yMod += yStep
            m = 0

        # CSV values are mm
        curX = float(viaDict[k]['X'])
        curY = float(viaDict[k]['Y'])
        curDiam = float(viaDict[k]['ID'])
        curOD = float(viaDict[k]['OD'])
        curX += pcbnew.ToMM(origin.x)
        curY += pcbnew.ToMM(origin.y)

        curX += xStep * m
        m += 1
        curY += yMod

        # label
        textPos = pcbnew.wxPointMM(curX, curY + curOD/2 + 4)
        text = pcbnew.PCB_TEXT(pcb)
        text.SetPosition(vec_from_point(textPos))
        text.SetLayer(textLayer)
        text.SetVisible(True)
        try:
            text.SetTextSize(textsize)               # KiCad 6
        except TypeError:
            text.SetTextSize(vec_from_size(textsize))  # KiCad 7
        text.SetTextThickness(thickness)
        text.SetText('%d' % (int(k) + 1))
        pcb.Add(text)

        create_via(pcb, netDefault, curX, curY, curDiam, curOD)

    caption = 'Done with Via Placement'
    message = 'Step X Size = %.4f mm\nStep Y Size = %.4f mm\nNum Columns = %d' % (xStep, yStep, numCols)
    reportDialog(winFrame, message, caption)

def convertJSONtoCSV(winFrame):
    # pick JSON
    openFileDialog = wx.FileDialog(
        winFrame, "Open JSON", "", "", "SRIG Via JSON (*.JSON)|*.json",
        wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )
    if openFileDialog.ShowModal() != wx.ID_OK:
        openFileDialog.Destroy()
        return
    json_path = openFileDialog.GetPath()
    openFileDialog.Destroy()

    # save CSV
    saveFileDialog = wx.FileDialog(
        winFrame, "Save CSV", "", "vias.csv",
        "CSV files (*.csv)|*.csv",
        wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    )
    if saveFileDialog.ShowModal() != wx.ID_OK:
        saveFileDialog.Destroy()
        return
    csv_path = saveFileDialog.GetPath()
    saveFileDialog.Destroy()

    # load json, write csv
    jd = restoreJSON(json_path)  # your existing JSON loader
    rows = []
    for k in sorted(jd.keys(), key=lambda s: int(s)):
        v = jd[k]
        rows.append({"index": int(k), "X": v["X"], "Y": v["Y"], "ID": v["ID"], "OD": v["OD"]})
    with open(csv_path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["index", "X", "Y", "ID", "OD"])
        wr.writeheader()
        wr.writerows(rows)

    reportDialog(winFrame, f"Wrote {len(rows)} rows to:\n{csv_path}", "JSON → CSV")



def funnelFromJson(winFrame, jsonFile, xStep=1.880, yStep=1.630, numCols=10):
    viaDict = restoreJSON(jsonFile)

    netDefault = '1'
    pcb = pcbnew.GetBoard()
    origin = pcbnew.wxPointMM(0, 0)

    yMod = 0
    m = 0
    curX = 0
    curY = 0

    keyList = list(viaDict.keys())

    textLayer = pcbnew.F_SilkS
    textsize = pcbnew.wxSize(pcbnew.FromMM(4), pcbnew.FromMM(4))
    thickness = pcbnew.FromMM(0.5)

    for i, k in enumerate(keyList):
        if i > 0 and i % numCols == 0:
            yMod += yStep
            m = 0

        # JSON values (assumed mm)
        curX = float(viaDict[k]['X'])
        curY = float(viaDict[k]['Y'])
        curDiam = float(viaDict[k]['ID'])
        curOD = float(viaDict[k]['OD'])
        curX += pcbnew.ToMM(origin.x)
        curY += pcbnew.ToMM(origin.y)

        curX += xStep * m
        m += 1
        curY += yMod

        # add label
        textPos = pcbnew.wxPointMM(curX, curY + curOD/2 + 4)
        text = pcbnew.PCB_TEXT(pcb)
        text.SetPosition(vec_from_point(textPos))
        text.SetLayer(textLayer)
        text.SetVisible(True)
        # KiCad 6 accepts wxSize; KiCad 7 uses VECTOR2I — try both safely:
        try:
            text.SetTextSize(textsize)
        except TypeError:
            text.SetTextSize(vec_from_size(textsize))
        text.SetTextThickness(thickness)
        text.SetText('%d' % (int(k) + 1))
        pcb.Add(text)

        create_via(pcb, netDefault, curX, curY, curDiam, curOD)

    caption = 'Done with Via Placement'
    message = 'Step X Size = %.4f mm\nStep Y Size = %.4f mm\nNum Columns = %d' % (xStep, yStep, numCols)
    reportDialog(winFrame, message, caption)



def distributeX(winFrame, xStep = 360):


    pcb = pcbnew.GetBoard()
    fpList = pcb.GetFootprints()
    origin = pcbnew.wxPointMils(0, 0)


    selectedList = []
    m = 0
  
    for fp in fpList:
        if fp.IsSelected():

            fpName = str(fp.GetReference())

            curX = fp.GetPosition()[0]
            curY = fp.GetPosition()[1]

            curX = pcbnew.ToMils(curX)
            curX += xStep*m
            m+=1
            curY = pcbnew.ToMils(curY)            

            newPos = pcbnew.wxPointMils(curX, curY)
            # newPos = pcbnew.wxPointMils(curX, curY)
            # fp.SetPosition(VECTOR2I(newPos)) #old version
            fp.SetPosition(VECTOR2I(newPos[0], newPos[1]))


    caption = 'Done with Distribution'
    message = 'Step Size = %d mils'%xStep
    reportDialog(winFrame, message, caption) 

def distributeY(winFrame, yStep = 66):


    pcb = pcbnew.GetBoard()
    fpList = pcb.GetFootprints()
    origin = pcbnew.wxPointMils(0, 0)


    selectedList = []
    m = 0
  
    for fp in fpList:
        if fp.IsSelected():

            fpName = str(fp.GetReference())

            curX = fp.GetPosition()[0]
            curY = fp.GetPosition()[1]

            curY = pcbnew.ToMils(curY)
            curY += yStep*m
            m+=1
            curY = pcbnew.ToMils(curY)            

            newPos = pcbnew.wxPointMils(curX, curY)
            # newPos = pcbnew.wxPointMils(curX, curY)
            # fp.SetPosition(VECTOR2I(newPos)) #old version
            fp.SetPosition(VECTOR2I(newPos[0], newPos[1]))


    caption = 'Done with Distribution'
    message = 'Step Size = %d mils'%yStep
    reportDialog(winFrame, message, caption) 


def distributeXY(winFrame, xStep = 360, yStep = 360, numCols = 10):


    pcb = pcbnew.GetBoard()
    fpList = pcb.GetFootprints()
    origin = pcbnew.wxPointMils(0, 0)


    fpNames = []
    for fp in fpList:
        fpNames.append(str(fp.GetReference()))


    fpNames = natural_sort(fpNames)
    
    sortedFP = [x for _,x in sorted(zip(fpNames,fpList))]

    selectedList = []
    m = 0
    
    yMod = 0

    for i,fp in enumerate(sortedFP):
    # for i,fp in enumerate(fpList):

        if fp.IsSelected():

            fpName = str(fp.GetReference())

            curX = fp.GetPosition()[0]
            curY = fp.GetPosition()[1]

            curX = pcbnew.ToMils(curX)
            curX += xStep*m
            m+=1
            curY = pcbnew.ToMils(curY) 
            curY += yMod           

            newPos = pcbnew.wxPointMils(curX, curY)
            # newPos = pcbnew.wxPointMils(curX, curY)
            # fp.SetPosition(VECTOR2I(newPos)) #old position
            fp.SetPosition(VECTOR2I(newPos[0], newPos[1]))

            if i>0 and i%numCols == 0:
                yMod += yStep
                m = 0

    caption = 'Done with Distribution'
    message = 'Step X Size = %d mils\n Step Y Size = %d mils\n Num Columns = %d '%(xStep, yStep, numCols)
    reportDialog(winFrame, message, caption) 


class distributeVias(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "SRIG Grid Layout"
        self.category = "Modify PCB"
        self.description = "Distribute Vias for Ion Funnel Construction"
 
    def Run(self):
        winFrame = [x for x in wx.GetTopLevelWindows() if 'pcb editor' in x.GetTitle().lower()][0]

        # Choose CSV
        openFileDialog = wx.FileDialog(
            winFrame,
            "Open",
            "",
            "",
            "SRIG Via Table (*.CSV)|*.csv",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        if openFileDialog.ShowModal() != wx.ID_OK:
            openFileDialog.Destroy()
            return
        fileName = openFileDialog.GetPath()
        openFileDialog.Destroy()
        if not os.path.isfile(fileName):
            return

        # One-shot dialog (same as before)
        dlg = ViaGridDialog(
            parent=winFrame,
            default_x_in=1.880,
            default_y_in=1.630,
            default_cols=10,
            default_units="inches"  # or "mm" if you prefer
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        xStep_mm, yStep_mm, numCols = dlg.get_values_mm()
        dlg.Destroy()

        funnelFromCSV(winFrame, fileName, xStep=xStep_mm, yStep=yStep_mm, numCols=numCols)
        return


class ViaGridDialog(wx.Dialog):
    """
    One-shot dialog for via grid settings.
    Returns xStep_mm, yStep_mm, numCols via get_values_mm().
    """

    def __init__(self, parent, default_x_in=1.880, default_y_in=1.630, default_cols=10, default_units="inches"):
        super().__init__(parent, title="Via Grid Settings")
        self._x = None
        self._y = None
        self._cols = None
        self._units = None

        # Controls
        lbl_x = wx.StaticText(self, label="X step:")
        lbl_y = wx.StaticText(self, label="Y step:")
        lbl_cols = wx.StaticText(self, label="# of columns:")
        lbl_units = wx.StaticText(self, label="Units:")

        self.txt_x = wx.TextCtrl(self, value=str(default_x_in))
        self.txt_y = wx.TextCtrl(self, value=str(default_y_in))
        self.spin_cols = wx.SpinCtrl(self, min=1, max=10000, initial=default_cols)
        self.choice_units = wx.Choice(self, choices=["inches", "mm"])
        self.choice_units.SetSelection(0 if default_units.lower()=="inches" else 1)

        # Layout
        grid = wx.FlexGridSizer(rows=0, cols=2, hgap=8, vgap=8)
        grid.AddGrowableCol(1, 1)
        grid.AddMany([
            (lbl_x, 0, wx.ALIGN_CENTER_VERTICAL), (self.txt_x, 1, wx.EXPAND),
            (lbl_y, 0, wx.ALIGN_CENTER_VERTICAL), (self.txt_y, 1, wx.EXPAND),
            (lbl_cols, 0, wx.ALIGN_CENTER_VERTICAL), (self.spin_cols, 0),
            (lbl_units, 0, wx.ALIGN_CENTER_VERTICAL), (self.choice_units, 0),
        ])

        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.ALL | wx.EXPAND, 12)
        if btns: sizer.Add(btns, 0, wx.ALL | wx.EXPAND, 12)
        self.SetSizerAndFit(sizer)

        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, evt):
        try:
            x = float(self.txt_x.GetValue().strip())
            y = float(self.txt_y.GetValue().strip())
            if x <= 0 or y <= 0:
                raise ValueError("Steps must be > 0.")
        except Exception as e:
            reportDialog(self, f"Invalid numeric input:\n{e}", "Input Error")
            return

        cols = self.spin_cols.GetValue()
        if cols < 1:
            reportDialog(self, "Number of columns must be at least 1.", "Input Error")
            return

        self._x, self._y, self._cols = x, y, cols
        self._units = self.choice_units.GetStringSelection() or "inches"
        self.EndModal(wx.ID_OK)

    def get_values_mm(self):
        if self._x is None:
            return None
        if (self._units or "inches").lower() == "inches":
            return self._x*25.4, self._y*25.4, self._cols
        else:
            return self._x, self._y, self._cols

class ChangeDepthDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        super(ChangeDepthDialog, self).__init__(*args, **kw)

        self.InitUI()
        self.SetSize((250, 200))
        self.SetTitle("Change Color Depth")


    def InitUI(self):

        pnl = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        sb = wx.StaticBox(pnl, label='Colors')
        sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        sbs.Add(wx.RadioButton(pnl, label='256 Colors',
            style=wx.RB_GROUP))
        sbs.Add(wx.RadioButton(pnl, label='16 Colors'))
        sbs.Add(wx.RadioButton(pnl, label='2 Colors'))

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(wx.RadioButton(pnl, label='Custom'))
        hbox1.Add(wx.TextCtrl(pnl), flag=wx.LEFT, border=5)
        sbs.Add(hbox1)

        pnl.SetSizer(sbs)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Ok')
        closeButton = wx.Button(self, label='Close')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)

        vbox.Add(pnl, proportion=1,
            flag=wx.ALL|wx.EXPAND, border=5)
        vbox.Add(hbox2, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

        self.SetSizer(vbox)

        okButton.Bind(wx.EVT_BUTTON, self.OnClose)
        closeButton.Bind(wx.EVT_BUTTON, self.OnClose)


    def OnClose(self, e):

        self.Destroy()
