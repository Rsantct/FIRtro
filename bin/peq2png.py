#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" 
    Módulo para hacer la gráfica de un ecualizador paramétrico
    del FIRtro (archivo XXXX.peq)
    
    Uso desde la línea de comandos:
    peq2png.py "/path/to/XXX.peq" [-i  para mostrar la gráfica de cada canal]
                                  [-t  para mostrar la gráfica de los canales] 
    
    Se generan archivos PNG en la carpeta del altavoz del FIRtro:
        channels_peq.png  left_peq.png  right_peq.png
"""
import peq2fr
import numpy as np
import matplotlib.pyplot as plt
from sys import argv as sys_argv, path as sys_path
import ConfigParser

# esto es para los modulos del FIRtro
from os import path as os_path
HOME = os_path.expanduser("~")
sys_path.append(HOME + "/bin")
from basepaths import config_folder, loudspeaker_folder
from getconfig import loudspeaker
status = ConfigParser.ConfigParser()
status.read(config_folder + "/status")
Fs = float(status.get("general", "fs"))
altavoz_folder = loudspeaker_folder + loudspeaker

def plotEQs(Fs, FRs, name, plotea=False):
    """ plotea unas pocas de FRs en un gráfico
        se resalta la última FR entregada, global de las anteriores.
    """
    plt.close()
    plt.figure(figsize=(16/2, 9/2))
    plt.title(name + " (parametric filters)")
    plt.xlim((20, 20000))
    plt.ylim((-18, +9))
    plt.yticks(np.linspace(-15, 6, 8, endpoint=True))
    plt.xscale("log")
    plt.grid()
    
    # ploteamos las Frs de cada filtro individual (dejamos la última)
    for (w, h) in FRs[:-1]:
        frecs = w * Fs/(2*np.pi)
        gaindB = 20*np.log10(np.abs(h))
        plt.plot(frecs, gaindB, linestyle="--")

    # ploteamos la FR de la respuesta global (es la última FR facilitada)
    (w, h) = FRs[-1]
    frecs = w * Fs/(2*np.pi)
    gaindB = 20*np.log10(np.abs(h))
    plt.plot(frecs, gaindB, linestyle="-", linewidth=2.0) 

    plt.savefig(altavoz_folder + "/" + name + "_peq.png")
    if plotea:
        plt.show()

def plotFR_canales(Fs, FR_canales, plotea=False):
    """ plotea las Frequency Responses de cada canal
        en un gráfico doble
    """
    plt.close()
    plt.figure(figsize=(16/2, 9/2))
    plt.title('PEQ parametric filters')
    plt.xlim((20, 20000))
    plt.ylim((-18, +9))
    #plt.yticks(np.linspace(-15, 6, 8, endpoint=True))
    plt.xscale("log")
    plt.grid()
    
    colors = ["blue", "red"]
    channels = ["left", "right"]
    for FRs in FR_canales:
        label=channels.pop(0)
        color=colors.pop(0)
        for w, h in FRs:
            frecs = w * Fs/(2*np.pi)
            gaindB = 20*np.log10(np.abs(h))
            plt.plot(frecs, gaindB, color = color, label = label, 
                     linestyle="-", linewidth=2.0)

    plt.legend(loc='lower right')
    plt.savefig(altavoz_folder + "/" + "channels_peq.png")
    if plotea:
        plt.show()

def leePEQ_canal(peqfile, canal):
    """ Lee un canal de un fichero XXX.peq de parametricos del FIRtro
        y devuelve las tripletas de los EQs ACTIVOS del canal (Frec, BW, Gain)
    """
    # leemos el archivo de EQs XXXX.peq (es una estructura INI)
    PEQs = ConfigParser.ConfigParser()
    PEQs.read(peqfile)
    # lista de almacenamiento de tripletas de EQs paramétricos
    peqs = []
    # leemos los PEQ del canal indicado:
    for option in PEQs.options(canal):
        # descartamos los ajustes de ganacia global de cada plugin
        if not "global" in option:
            # f1       = 1      47.4    0.0818    -6.2 , etc...
            peq = PEQs.get(canal, option).split()
            # lo añadimos a la lista si está activado.
            if peq[0] == "1":
                peqs.append( [ float(peq[1]), float(peq[2]), float(peq[3]) ] )

    # Ejemplo:
    #    peqs =  [
    #            ( 47.4  ,  0.0818  ,  -6.2 ),
    #            ( 50.6  ,  0.1884  ,   4.0 ),
    #            ( 56.2  ,  0.1033  ,  -9.9 ),
    #            (  100  ,  0.1318  ,  -4.6 ),
    #            (  144  ,  0.1294  ,  -6.6 ),
    #            (  173  ,  0.0722  ,  -4.7 ),
    #            (  215  ,  0.2880  ,  -3.5 ),
    #            (  263  ,  0.2880  ,  -1.7 ),
    #            (  301  ,  0.2897  ,   3.1 ),
    #            (  534  ,  0.4771  ,  -4.0 ),
    #            ]

    return peqs

def main(fname, ploteaI=False, ploteaT=False):
    
    FR_canales = [] # lista con la FR total de cada canal
    
    for canal in "left", "right":
        # leemos los parametricos que hay definidos en un archivo
        # (active, F0, BW, dB) 
        PEQs = leePEQ_canal(fname, canal)
        
        # y los convertimos a Frequency Responses [w, h]
        FRs = peq2fr.peqBW_2_fr(Fs, PEQs)
        
        # computamos la FR resultante de todos los paramétricos,
        # la guardamos para después.
        FR_canales.append([peq2fr.frSum(Fs, FRs)])

        # (i) y añadimos la fr total para ser visualizada también
        FRs.append(peq2fr.frSum(Fs, FRs))        

        # Generamos una gráfica de los paramétricos del canal
        plotEQs(Fs, FRs, canal, ploteaI)
            
    # ploteamos la FR resultante en cada canal
    plotFR_canales(Fs, FR_canales, ploteaT)
    
if __name__ == "__main__":

    ploteaI, ploteaT = False, False
    try:
        fname = sys_argv[1]
        try:
            if sys_argv[2] == "-i": ploteaI = True
            if sys_argv[2] == "-t": ploteaT = True
        except:
            pass    
        main(fname, ploteaI, ploteaT)
 
    except:
        print __doc__
