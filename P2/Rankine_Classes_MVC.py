#Used Dr.Smay's code and class lecture to modify this code to HW requirements
#Used ChatGPT to help debug and test logic for filling in missing code to meet HW requirements
#region imports
import math
from Calc_state import *
from UnitConversions import UnitConverter as UC
import numpy as np
from matplotlib import pyplot as plt
from copy import deepcopy as dc
#these imports are necessary for drawing a matplot lib graph on my GUI
#no simple widget for this exists in QT Designer, so I have to add the widget in code.
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
#endregion

#region class definitions
class rankineModel():
    def __init__(self):
        '''
        Constructor for rankine power cycle data (in the Model-View-Controller design pattern).  This class
        is for storing data only.  The Controller class should update the model depending on input from the user.
        The View class should display the model data depending on the desired output.
        :param p_low: the low pressure isobar for the cycle in kPa
        :param p_high: the high pressure isobar for the cycle in kPa
        :param t_high: optional temperature for State1 (turbine inlet) in degrees C
        :param eff_turbine: isentropic efficiency of the turbine
        :param name: a convenient name
        '''
        self.p_low=None
        self.p_high=None
        self.t_high=None
        self.name=None
        self.efficiency=None
        self.turbine_eff=None
        self.turbine_work=None
        self.pump_work=None
        self.heat_added=None
        self.steam=Steam_SI()  # Instantiate a steam object for calculating state
        # Initialize the states as stateProps objects (i.e., stateProperties)
        self.state1 = stateProps()
        self.state2s = stateProps()
        self.state2 = stateProps()
        self.state3 = stateProps()
        self.state4 = stateProps()
        self.SI=True  # If False, convert pressures from psi to kPa and T from F to C for inputs
        #the following are a place to store data for plotting
        self.satLiqPlotData = StateDataForPlotting()
        self.satVapPlotData = StateDataForPlotting()
        self.upperCurve = StateDataForPlotting()
        self.lowerCurve = StateDataForPlotting()

class rankineView():
    def __init__(self):
        """
        Empty constructor by design
        """

    def setWidgets(self, *args):
        #create class variables for the input widgets
        self.rb_SI, self.le_PHigh, self.le_PLow, self.le_TurbineInletCondition, self.rdo_Quality, self.le_TurbineEff, self.cmb_XAxis, self.cmb_YAxis, self.chk_logX, self.chk_logY=args[0]
        #create class variables for the display widgets
        self.lbl_PHigh, self.lbl_PLow, self.lbl_SatPropLow,self.lbl_SatPropHigh, self.lbl_TurbineInletCondition, self.lbl_H1, self.lbl_H1Units, self.lbl_H2, self.lbl_H2Units, self.lbl_H3, self.lbl_H3Units, self.lbl_H4, self.lbl_H4Units, self.lbl_TurbineWork, self.lbl_TurbineWorkUnits, self.lbl_PumpWork, self.lbl_PumpWorkUnits, self.lbl_HeatAdded, self.lbl_HeatAddedUnits, self.lbl_ThermalEfficiency, self.canvas, self.figure, self.ax=args[1]

    def selectQualityOrTHigh(self, Model=None):
        """
        Action to take when selecting one of the radio buttons for Quality or THigh
        :return:
        """
        # region Code for P1.1
        SI = self.rb_SI.isChecked()
        if self.rdo_Quality.isChecked():
            self.le_TurbineInletCondition.setText("1.0")
            self.le_TurbineInletCondition.setEnabled(False)
        else:
            # When THigh radio button is selected:
            # Step 1: Get saturated properties at p_high
            satPropsHigh = Model.steam.getsatProps_p(Model.p_high)
            # Step 2: Convert the saturation temperature if working in English units
            T_sat = satPropsHigh.tsat if SI else UC.C_to_F(satPropsHigh.tsat)
            # Step 3: Update the turbine inlet condition widget with the saturation temperature
            self.le_TurbineInletCondition.setText("{:.2f}".format(T_sat))
            self.le_TurbineInletCondition.setEnabled(True)

        # endregion
        x = self.rdo_Quality.isChecked()
        self.lbl_TurbineInletCondition.setText(
            ("Turbine Inlet: {}{} =".format('x' if x else 'THigh', '' if x else ('(C)' if SI else '(F)'))))

    def setNewPHigh(self, Model=None):
        """
                 This function checks the self.rb_SI.isChecked() to see which units are used.
                 Then, it sets the text of lbl_SatPropHigh using SatPropsIsobar(float(self.le_PHigh.text())*PCF, SI=SI).txtOut
                 here, PCF is the pressure conversion factor
                 finally, we need to call the function self.SelectQualityOrTHigh()
                 :return:
                 """
        SI = self.rb_SI.isChecked()
        # Use a pressure conversion factor (PCF): input is bar in SI or psi in English
        PCF = 1 if SI else UC.psi_to_bar
        try:
            p_high_input = float(self.le_PHigh.text())
            p_high_SI = p_high_input * PCF
            # Retrieve saturation properties at the new high pressure
            satPropsHigh = Model.steam.getsatProps_p(p_high_SI)
            # Update the high-pressure saturation properties label
            self.lbl_SatPropHigh.setText(satPropsHigh.getTextOutput(SI=SI))
        except Exception as e:
            self.lbl_SatPropHigh.setText("Invalid Input")
        # Also update the turbine inlet condition in case THigh is used
        self.selectQualityOrTHigh(Model)

    def setNewPLow(self, Model=None):
        SI = self.rb_SI.isChecked()
        PCF = 1 if SI else UC.psi_to_bar
        try:
            p_low_input = float(self.le_PLow.text())
            p_low_SI = p_low_input * PCF
            # Retrieve saturation properties at the new low pressure
            satPropsLow = Model.steam.getsatProps_p(p_low_SI)
            # Update the low-pressure saturation properties label
            self.lbl_SatPropLow.setText(satPropsLow.getTextOutput(SI=SI))
        except Exception as e:
            self.lbl_SatPropLow.setText("Invalid Input")

    def outputToGUI(self, Model=None):
        #unpack the args
        if Model.state1 is None:  # means the cycle has not been evaluated yet
            return
        #update the line edits and labels
        HCF=1 if Model.SI else UC.kJperkg_to_BTUperlb # Enthalpy conversion factor (HCF)
        self.lbl_H1.setText("{:0.2f}".format(Model.state1.h * HCF))
        self.lbl_H2.setText("{:0.2f}".format(Model.state2.h * HCF))
        self.lbl_H3.setText("{:0.2f}".format(Model.state3.h * HCF))
        self.lbl_H4.setText("{:0.2f}".format(Model.state4.h * HCF))
        self.lbl_TurbineWork.setText("{:0.2f}".format(Model.turbine_work*HCF))
        self.lbl_PumpWork.setText("{:0.2f}".format(Model.pump_work*HCF))
        self.lbl_HeatAdded.setText("{:0.2f}".format(Model.heat_added*HCF))
        self.lbl_ThermalEfficiency.setText("{:0.2f}".format(Model.efficiency))
        satPropsLow=Model.steam.getsatProps_p(p=Model.p_low)
        satPropsHigh=Model.steam.getsatProps_p(p=Model.p_high)
        self.lbl_SatPropLow.setText(satPropsLow.getTextOutput(SI=Model.SI))
        self.lbl_SatPropHigh.setText(satPropsHigh.getTextOutput(SI=Model.SI))

        #update the plot
        self.plot_cycle_XY(Model=Model)

    def updateUnits(self, Model=None):
        """
        Updates the units on the GUI to match choice of SI or English
        :param Model:  a reference to the model
        :return:
        """
        SI = Model.SI

        # Step 0: Refresh outputs (this updates labels and the plot)
        self.outputToGUI(Model=Model)

        # Step 1: Update the pressure input fields using the base values from the model.
        # Assume Model.p_high and Model.p_low are stored in SI (bar).
        if Model.p_high is not None:
            # Convert from SI (bar) to English (psi) if necessary.
            p_high_display = Model.p_high if SI else Model.p_high * UC.bar_to_psi
            self.le_PHigh.setText("{:.2f}".format(p_high_display))
        if Model.p_low is not None:
            p_low_display = Model.p_low if SI else Model.p_low * UC.bar_to_psi
            self.le_PLow.setText("{:.2f}".format(p_low_display))

        # Step 2: Update turbine inlet temperature if not in quality mode.
        if not self.rdo_Quality.isChecked():
            # If Model.t_high is provided, it is stored in SI.
            # Otherwise, recalc from saturated properties.
            if Model.t_high is not None:
                T_base = Model.t_high
            else:
                satPropsHigh = Model.steam.getsatProps_p(Model.p_high)
                T_base = satPropsHigh.tsat
            T_display = T_base if SI else UC.C_to_F(T_base)
            self.le_TurbineInletCondition.setText("{:.2f}".format(T_display))

        # Step 3: Update the unit labels for output fields.
        if SI:
            self.lbl_H1Units.setText("kJ/kg")
            self.lbl_H2Units.setText("kJ/kg")
            self.lbl_H3Units.setText("kJ/kg")
            self.lbl_H4Units.setText("kJ/kg")
            self.lbl_TurbineWorkUnits.setText("kJ/kg")
            self.lbl_PumpWorkUnits.setText("kJ/kg")
            self.lbl_HeatAddedUnits.setText("kJ/kg")
        else:
            self.lbl_H1Units.setText("BTU/lb")
            self.lbl_H2Units.setText("BTU/lb")
            self.lbl_H3Units.setText("BTU/lb")
            self.lbl_H4Units.setText("BTU/lb")
            self.lbl_TurbineWorkUnits.setText("BTU/lb")
            self.lbl_PumpWorkUnits.setText("BTU/lb")
            self.lbl_HeatAddedUnits.setText("BTU/lb")

        # Final refresh to ensure that the plot and labels are up to date.
        self.outputToGUI(Model=Model)

    def print_summary(self, Model=None):
        """
        Prints to CLI.
        :param Model: a rankineModel object
        :return: nothing
        """
        if Model.efficiency==None:
            Model.calc_efficiency()
        print('Cycle Summary for: ', Model.name)
        print('\tEfficiency: {:0.3f}%'.format(Model.efficiency))
        print('\tTurbine Eff:  {:0.2f}'.format(Model.turbine_eff))
        print('\tTurbine Work: {:0.3f} kJ/kg'.format(Model.turbine_work))
        print('\tPump Work: {:0.3f} kJ/kg'.format(Model.pump_work))
        print('\tHeat Added: {:0.3f} kJ/kg'.format(Model.heat_added))
        Model.state1.print()
        Model.state2.print()
        Model.state3.print()
        Model.state4.print()

    def plot_cycle_TS(self, axObj=None, Model=None):
        """
        I want to plot the Rankine cycle on T-S coordinates along with the vapor dome and shading in the cycle.
        I notice there are several lines on the plot:
        saturated liquid T(s) colored blue
        saturated vapor T(s) colored red
        The high and low isobars and lines connecting state 1 to 2, and 3 to saturated liquid at phigh
        step 1:  build data for saturated liquid line
        step 2:  build data for saturated vapor line
        step 3:  build data between state 3 and sat liquid at p_high
        step 4:  build data between sat liquid at p_high and state 1
        step 5:  build data between state 1 and state 2
        step 6:  build data between state 2 and state 3
        step 7:  put together data from 3,4,5 for top line and build bottom line
        step 8:  make and decorate plot

        Note:  will plot using pyplot if axObj is None else just returns

        :param axObj:  if None, used plt.subplot else a MatplotLib axes object.
        :return:
        """
        SI=Model.SI
        steam=Model.steam
        #region step 1&2:
        ts, ps, hfs, hgs, sfs, sgs, vfs, vgs = np.loadtxt('sat_water_table.txt', skiprows=1,
                                                          unpack=True)  # use np.loadtxt to read the saturated properties
        ax = plt.subplot() if axObj is None else axObj

        hCF = 1 if Model.SI else UC.kJperkg_to_BTUperlb
        pCF = 1 if Model.SI else UC.kpa_to_psi
        sCF = 1 if Model.SI else UC.kJperkgK_to_BTUperlbR
        vCF = 1 if Model.SI else UC.kgperm3_to_lbperft3

        sfs *= sCF
        sgs *= sCF
        hfs *= hCF
        hgs *= hCF
        vfs *= vCF
        vgs *= vCF
        ps *= pCF
        ts = [t if Model.SI else UC.C_to_F(t) for t in ts]

        xfsat = sfs
        yfsat = ts
        xgsat = sgs
        ygsat = ts

        ax.plot(xfsat, yfsat, color='blue')
        ax.plot(xgsat, ygsat, color='red')
        #endregion

        #step 3:  I'll just make a straight line between state3 and state3p
        st3p=steam.getState(Model.p_high,x=0) #saturated liquid state at p_high
        svals=np.linspace(Model.state3.s, st3p.s, 20)
        hvals=np.linspace(Model.state3.h, st3p.h, 20)
        pvals=np.linspace(Model.p_low, Model.p_high,20)
        vvals=np.linspace(Model.state3.v, st3p.v, 20)
        tvals=np.linspace(Model.state3.T, st3p.T, 20)
        line3=np.column_stack([svals, tvals])

        #step 4:
        sat_pHigh=steam.getState(Model.p_high, x=1.0)
        st1=Model.state1
        svals2p=np.linspace(st3p.s, sat_pHigh.s, 20)
        hvals2p = np.linspace(st3p.h, sat_pHigh.h, 20)
        pvals2p = [Model.p_high for i in range(20)]
        vvals2p = np.linspace(st3p.v, sat_pHigh.v, 20)
        tvals2p=[st3p.T for i in range(20)]
        line4=np.column_stack([svals2p, tvals2p])
        if st1.T>sat_pHigh.T:  #need to add data points to state1 for superheated
            svals_sh=np.linspace(sat_pHigh.s,st1.s, 20)
            tvals_sh=np.array([steam.getState(Model.p_high,s=ss).T for ss in svals_sh])
            line4 =np.append(line4, np.column_stack([svals_sh, tvals_sh]), axis=0)
        #plt.plot(line4[:,0], line4[:,1])

        #step 5:
        svals=np.linspace(Model.state1.s, Model.state2.s, 20)
        tvals=np.linspace(Model.state1.T, Model.state2.T, 20)
        line5=np.array(svals)
        line5=np.column_stack([line5, tvals])
        #plt.plot(line5[:,0], line5[:,1])

        #step 6:
        svals=np.linspace(Model.state2.s, Model.state3.s, 20)
        tvals=np.array([Model.state2.T for i in range(20)])
        line6=np.column_stack([svals, tvals])
        #plt.plot(line6[:,0], line6[:,1])

        #step 7:
        topLine=np.append(line3, line4, axis=0)
        topLine=np.append(topLine, line5, axis=0)
        xvals=topLine[:,0]
        y1=topLine[:,1]
        y2=[Model.state3.T for s in xvals]

        if not SI:
            xvals*=UC.kJperkgK_to_BTUperlbR
            for i in range(len(y1)):
                y1[i]=UC.C_to_F(y1[i])
            for i in range(len(y2)):
                y2[i]=UC.C_to_F(y2[i])

        ax.plot(xvals, y1, color='darkgreen')
        ax.plot(xvals, y2, color='black')
        # ax.fill_between(xvals, y1, y2, color='gray', alpha=0.5)

        if SI:
            ax.plot(Model.state1.s, Model.state1.T, marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state2.s, Model.state2.T, marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state3.s, Model.state3.T, marker='o', markeredgecolor='k', markerfacecolor='w')
        else:
            ax.plot(Model.state1.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state1.T), marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state2.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state2.T), marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state3.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state3.T), marker='o', markeredgecolor='k', markerfacecolor='w')

        tempUnits=r'$\left(^oC\right)$' if SI else r'$\left(^oF\right)$'
        entropyUnits=r'$\left(\frac{kJ}{kg\cdot K}\right)$' if SI else r'$\left(\frac{BTU}{lb\cdot ^oR}\right)$'
        ax.set_xlabel(r's '+entropyUnits, fontsize=18)  #different than plt
        ax.set_ylabel(r'T '+tempUnits, fontsize=18)  #different than plt
        ax.set_title(Model.name)  #different than plt
        ax.grid(visible='both', alpha=0.5)
        ax.tick_params(axis='both', direction='in', labelsize=18)

        sMin=min(sfs)
        sMax=max(sgs)
        ax.set_xlim(sMin, sMax)  #different than plt

        tMin=min(ts)
        tMax=max(max(ts),st1.T)
        ax.set_ylim(tMin,tMax*1.05)  #different than plt

        energyUnits=r'$\frac{kJ}{kg}$' if SI else r'$\frac{BTU}{lb}$'
        energyCF = 1 if SI else UC.kJperkg_to_BTUperlb

        if axObj is None:  # this allows me to show plot if not being displayed on a figure
            plt.show()

    def plot_cycle_XY(self, Model=None):
        """
        I want to plot any two thermodynaimc properties on X and Y
        :param X: letter for which variable to plot on X axis
        :param Y: letter for which variable to plot on Y axis
        :return:
        """
        ax=self.ax
        X = self.cmb_XAxis.currentText()
        Y = self.cmb_YAxis.currentText()
        logx = self.chk_logX.isChecked()
        logy = self.chk_logY.isChecked()
        SI=Model.SI
        if X == Y:
            return
        QTPlotting = True  # assumes we are plotting onto a QT GUI form
        if ax == None:
            ax = plt.subplot()
            QTPlotting = False  # actually, we are just using CLI and showing the plot

        ax.clear()
        ax.set_xscale('log' if logx else 'linear')
        ax.set_yscale('log' if logy else 'linear')
        YF = Model.satLiqPlotData.getDataCol(Y, SI=SI)
        YG = Model.satVapPlotData.getDataCol(Y, SI=SI)
        XF = Model.satLiqPlotData.getDataCol(X, SI=SI)
        XG = Model.satVapPlotData.getDataCol(X, SI=SI)
        # plot the vapor dome
        ax.plot(XF, YF, color='b')
        ax.plot(XG, YG, color='r')
        # plot the upper and lower curves
        ax.plot(Model.lowerCurve.getDataCol(X, SI=SI), Model.lowerCurve.getDataCol(Y, SI=SI), color='k')
        ax.plot(Model.upperCurve.getDataCol(X, SI=SI), Model.upperCurve.getDataCol(Y, SI=SI), color='g')
        # ax.fill_between(Model.upperCurve.getDataCol(X), Model.upperCurve.getDataCol(Y), self.lowerCurve.getDataCol(Y), color='grey', alpha=0.2)

        # add axis labels
        ax.set_ylabel(Model.lowerCurve.getAxisLabel(Y, SI=SI), fontsize='large' if QTPlotting else 'medium')
        ax.set_xlabel(Model.lowerCurve.getAxisLabel(X, SI=SI), fontsize='large' if QTPlotting else 'medium')
        # put a title on the plot
        Model.name = 'Rankine Cycle - ' + Model.state1.region + ' at Turbine Inlet'
        ax.set_title(Model.name, fontsize='large' if QTPlotting else 'medium')

        # modify the tick marks
        ax.tick_params(axis='both', which='both', direction='in', top=True, right=True,
                       labelsize='large' if QTPlotting else 'medium')  # format tick marks

        # plot the circles for states 1, 2, 3, and 4
        ax.plot(Model.state1.getVal(X, SI=SI), Model.state1.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state2.getVal(X, SI=SI), Model.state2.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state3.getVal(X, SI=SI), Model.state3.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state4.getVal(X, SI=SI), Model.state4.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        # set limits on x and y
        xmin = min(min(XF), min(XG), min(Model.upperCurve.getDataCol(X, SI=SI)), max(Model.lowerCurve.getDataCol(X, SI=SI)))
        xmax = max(max(XF), max(XG), max(Model.upperCurve.getDataCol(X, SI=SI)), max(Model.lowerCurve.getDataCol(X, SI=SI)))
        ymin = min(min(YF), min(YG), min(Model.upperCurve.getDataCol(Y, SI=SI)), max(Model.lowerCurve.getDataCol(Y, SI=SI)))
        ymax = max(max(YF), max(YG), max(Model.upperCurve.getDataCol(Y, SI=SI)),
                   max(Model.lowerCurve.getDataCol(Y, SI=SI))) * 1.1
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        deltax = xmax - xmin
        deltay = ymax - ymin
        # add the summary text to the plot

        # show the plot
        if QTPlotting == False:
            plt.show()
        else:
            self.canvas.draw()

class rankineController():
    def __init__(self, *args):
        """
        Create rankineModel object.  The rankineController class updates the model based on user input
        and updates the rankineView as well
        :param *args: a tuple containing widgets that get updated in the View
        """
        self.Model=rankineModel()  # In MVC pattern, the controller should hold a reference to the model
        self.View=rankineView()  # In MVC pattern, the controller should hold a reference to the view
        self.IW=args[0]  # an array of widgets that are for user input
        self.DW=args[1]  # an array of widgets that are for display
        self.View.setWidgets(self.IW, self.DW)
        self.buildVaporDomeData()

    def updateModel(self):
        """
        I'm expecting a tuple of input widgets from the GUI.  Read and apply them here.
        :param args: a tuple of input widgets, other arguments such as SI or ENG
        :return: nothing
        """
        #read from the input widgets
        self.Model.SI=self.View.rb_SI.isChecked()

        #update the model
        #$UNITS$ since inputs can be SI or English, I need to convert to SI here for pressures and temperature
        PCF=1 if self.Model.SI else UC.psi_to_bar #$UNITS$ input is bar for SI and psi for English
        self.Model.p_high = float(self.View.le_PHigh.text()) * PCF  # get the high pressure isobar in kPa
        self.Model.p_low = float(self.View.le_PLow.text()) * PCF  # get the low pressure isobar in kPa
        T=float(self.View.le_TurbineInletCondition.text()) #$UNITS$
        self.Model.t_high = None if self.View.rdo_Quality.isChecked() else (T if self.Model.SI else UC.F_to_C(T)) #$UNITS$
        self.Model.turbine_eff = float(self.View.le_TurbineEff.text())
        #do the calculation
        self.calc_efficiency()
        self.updateView()

    def updateUnits(self):
        #Switching units should not change the model, but should update the view
        self.Model.SI=self.View.rb_SI.isChecked()
        self.View.updateUnits(Model=self.Model)

    def selectQualityOrTHigh(self):
        self.View.selectQualityOrTHigh(self.Model)

    def setNewPHigh(self):
        self.View.setNewPHigh(self.Model)

    def setNewPLow(self):
        self.View.setNewPLow(self.Model)

    def calc_efficiency(self):
        """
        I've modified this on 4/15/2022 to use a single SI_Steam object that is held in the model for calculating
        various states along the path of the Rankine cycle.  I use the getState function to retrieve a deep copy of
        a stateProps object.
        :return:
        """
        steam=self.Model.steam

        # calculate the 4 states
        # state 1: turbine inlet (p_high, t_high) superheated or saturated vapor
        if (self.Model.t_high == None):
            self.Model.state1 = steam.getState(P=self.Model.p_high, x=1.0, name='Turbine Inlet')
        else:
            self.Model.state1 = steam.getState(P=self.Model.p_high, T=self.Model.t_high, name='Turbine Inlet')
        # state 2: turbine exit (p_low, s=s_turbine inlet) two-phase
        self.Model.state2s = steam.getState(P=self.Model.p_low, s=self.Model.state1.s, name="Turbine Exit")
        if self.Model.turbine_eff < 1.0:  # eff=(h1-h2)/(h1-h2s) -> h2=h1-eff(h1-h2s)
            h2 = self.Model.state1.h - self.Model.turbine_eff * (self.Model.state1.h - self.Model.state2s.h)
            self.Model.state2 = steam.getState(P=self.Model.p_low, h=h2, name="Turbine Exit")
        else:
            self.Model.state2 = self.Model.state2s
        # state 3: pump inlet (p_low, x=0) saturated liquid
        self.Model.state3 = steam.getState(P=self.Model.p_low, x=0, name='Pump Inlet')
        # state 4: pump exit (p_high,s=s_pump_inlet) typically sub-cooled, but estimate as saturated liquid
        self.Model.state4 = steam.getState(P=self.Model.p_high, s=self.Model.state3.s, name='Pump Exit')

        self.Model.turbine_work = self.Model.state1.h - self.Model.state2.h  # calculate turbine work
        self.Model.pump_work = self.Model.state4.h - self.Model.state3.h  # calculate pump work
        self.Model.heat_added = self.Model.state1.h - self.Model.state4.h  # calculate heat added
        self.Model.efficiency = 100.0 * (self.Model.turbine_work - self.Model.pump_work) / self.Model.heat_added
        return self.Model.efficiency

    def updateView(self):
        """
        This is a pass-through function that calls and identically named function in the View, but passes along the
        Model as an argument.
        :param args: A tuple of Widgets that get unpacked and updated in the view
        :return:
        """
        self.buildDataForPlotting()
        self.View.outputToGUI(Model=self.Model)

    def setRankine(self,p_low=8, p_high=8000, t_high=None, eff_turbine=1.0, name='Rankine Cycle'):
        '''
        Set model values for rankine power cycle.  If t_high is not specified, the State 1
        is assigned x=1 (saturated steam @ p_high).  Otherwise, use t_high to find State 1.
        :param p_low: the low pressure isobar for the cycle in kPa
        :param p_high: the high pressure isobar for the cycle in kPa
        :param t_high: optional temperature for State1 (turbine inlet) in degrees C
        :param eff_turbine: isentropic efficiency of the turbine
        :param name: a convenient name
        '''
        self.Model.p_low=p_low
        self.Model.p_high=p_high
        self.Model.t_high=t_high
        self.Model.name=name
        self.Model.efficiency=None
        self.Model.turbine_eff=eff_turbine
        self.Model.turbine_work=0
        self.Model.pump_work=0
        self.Model.heat_added=0
        self.Model.state1=None  # entrance to turbine
        self.Model.state2s=None  # entrance to condenser (isentropic turbine)
        self.Model.state2=None  # entrance to condenser (non-isentropic turbine)
        self.Model.state3=None  # entrance to pump (saturated liquid at plow)
        self.Model.state4=None  # entrance to boiler (isentropic)

    def print_summary(self):
        """
        A pass-thrugh method for accessing View and passing Model.
        :return:
        """
        self.View.print_summary(Model=self.Model)

    def buildVaporDomeData(self, nPoints=500):
        """
        I'll build the vapor dome from just above the triple point up to the critical point
        :param nPoints:
        :return:
        """
        steam=self.Model.steam
        tp=triplePt_PT()
        cp=criticalPt_PT()
        steam.state.p=cp.p
        steam.state.t=cp.t
        steam.calcState_1Phase()
        critProps=dc(steam.state)
        P=np.logspace(math.log10(tp.p*1.001), math.log10(cp.p*0.99),nPoints)
        for p in P:
            sat=steam.getsatProps_p(p)
            self.Model.satLiqPlotData.addPt((sat.tsat, p, sat.uf, sat.hf, sat.sf, sat.vf))
            self.Model.satVapPlotData.addPt((sat.tsat, p, sat.uf, sat.hg, sat.sg, sat.vg))
        self.Model.satLiqPlotData.addPt((critProps.t, critProps.p, critProps.u, critProps.h, critProps.s, critProps.v))
        self.Model.satVapPlotData.addPt((critProps.t, critProps.p, critProps.u, critProps.h, critProps.s, critProps.v))

    def buildDataForPlotting(self):
        """
        I want to create data for plotting the Rankine cycle.  The key states are:
        State 1.  Entrance to Turbine (either saturated vapor or superheated steam at p_High)
        State 2.  Entrance to Condenser (probably two-phase at p_Low)
        State 3.  Entrance to the pump (saturated liquid at p_Low)
        State 4.  Entrance to the boiler (sub-cooled liquid at p_High, isentropic pump)
        
        I want to create h, s, v, p, T data between states 1-2, 2-3, 3-4, 4-1
        I'll piece together an upperCurve data set from 3-4 + 4-1 + 1-2
        The lowerCurve data set is 2-3
        :return:
        """
        # clear out any old data
        self.Model.upperCurve.clear()
        self.Model.lowerCurve.clear()
        
        #get saturated properties at PHigh and PLow
        satPLow=self.Model.steam.getsatProps_p(self.Model.p_low)
        satPHigh=self.Model.steam.getsatProps_p(self.Model.p_high)
        
        steam = self.Model.steam

        #region build upperCurve
        #region states from 3-4
        nPts = 15
        DeltaP = (satPHigh.psat - satPLow.psat)
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(P=(satPLow.psat + z * DeltaP), s=satPLow.sf)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        # endregion

        #region states from 4-1
        #first from T4 to T5 where T5 is the saturated liquid at p_High
        T4 = state.t
        T5 = satPHigh.tsat
        DeltaT = (T5 - T4)
        nPts = 20
        P = satPHigh.psat
        for n in range(nPts-1):
            z = n * 1.0 / (nPts - 2)
            T = T4 + z * DeltaT
            if T<T5:
                state = steam.getState(P=P, T=T)
                self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(satPHigh.psat,x=z)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        if self.Model.state1.t > (satPHigh.tsat+1):
            T6 = satPHigh.tsat
            DeltaT = self.Model.state1.t - T6
            for n in range(0, nPts):
                z = n * 1.0 / (nPts - 1)
                if z>0:
                    state = steam.getState(satPHigh.psat, T=T6+z*DeltaT)
                    self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        # endregion

        #region states between 1 and 2
        #I'm assuming a linear change in Pressure from P1 to P2, along with linear change in s,
        #but not sure of details inside the turbine, so this is just a guess.
        s1=self.Model.state1.s
        s2=self.Model.state2.s
        P1=self.Model.state1.p
        P2=self.Model.state2.p
        Deltas=s2-s1
        DeltaP=P2-P1
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(P=P1+z*DeltaP, s=s1+z*Deltas)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        #endregion
        #endregion

        #region build lowerCurve between states 2 and 3
        x2=self.Model.state2.x
        state=self.Model.state2
        #account for possibility that T>TSatPHigh
        if state.t>satPLow.tsat:
            nPts=20
            DeltaT=(state.t-satPLow.tsat)/nPts
            self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
            for n in range(nPts):
                t=self.Model.state2.t-n*DeltaT
                if t>satPLow.tsat:
                    state=steam.getState(P=satPLow.psat,T=t)
                    self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))

        nPts= len(self.Model.upperCurve.t)
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state=steam.getState(P=satPLow.psat, x=(1.0-z)*x2)
            self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        #endregion
        pass

    def updatePlot(self):
        self.View.plot_cycle_XY(Model=self.Model)
#endregion

#region function definitions
def main():
    RC=rankineController()
    RC.setRankine(8*UC.kpa_to_bar,8000*UC.kpa_to_bar,t_high=500, eff_turbine=0.9,name='Rankine Cycle - Superheated at turbine inlet')
    #t_high is specified
    #if t_high were not specified, then x_high = 1 is assumed
    eff=RC.calc_efficiency()
    print(eff)
    RC.print_summary()
    RC.plot_cycle_TS()
#endregion

#region function calls
if __name__=="__main__":
    main()
#endregion