#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    FIRtro 2.0 Módulo de gestión de presets usado por server_process.
    Uso informativo en línea de comando:
        presets.py [all | preset*]  (*: filtra los que coincidan)
"""
# v1.1: 
# - Permite indicar "dirac_pulse" en vías full range (en ese caso no existe un pcm real).
# v1.2
# - Gestiona PEQ (EQ paramétrico basado en Ecasound).
# v1.3:
# - Se incorpora la atenuacion y el delay para cada vía.
# v1.3b
# - Se simplifica el archivo presets.ini con el nombre descriptivo del preset en la propia sección INI.
# - Se implementa línea de comandos para búsquedas.

import subprocess
import os
from sys import path as sys_path, argv as sys_argv, exit as sys_exit
import socket
import ConfigParser
# para conectar solo las salidas de brutefir de las VIAS EN USO a la tarjeta de sonido
import jack
# El módulo "read_brutefir_process.py" proporciona la relación de coeficientes
# cargados en Brutefir y los filtros con los coeficientes que tienen asignados,
# y tambien proporciona el mapeo de salidas de Brutefir en Jack
import read_brutefir_process  as brutefir
# Para que funcione la cosa actualizamos las listas: 
# brutefir.outputs, brutefir.coeffs, brutefir.filters_at_start y brutefir.filters_running
brutefir.lee_config()
brutefir.lee_running_config()

# modulos del FIRtro:
HOME = os.path.expanduser("~")
sys_path.append(HOME + "/bin")
from basepaths import loudspeaker_folder, config_folder
from getconfig import loudspeaker
from getstatus import drc_eq as drc_status

status = ConfigParser.ConfigParser()
status.read(config_folder + "/status")
# carpeta del altavoz/fs
altavoz_folder = loudspeaker_folder + loudspeaker + "/"

# archivo de definición de nuestros presets para este altavoz:
presets = ConfigParser.ConfigParser()
presets.read(altavoz_folder + "/presets.ini")
# recopilador de avisos para printar
avisos = []

def configura_preset(presetID, filter_type):
    """ Esta función se encarga de configurar en el proceso brutefir el coeff de los xover 
        y subwoofer si procede, como se haya definido en el archivo de presets de usuario.
        Y devuelve los siguientes valores a server_process para que se actualize en el sistema:
        - la descripción del preset
        - el numero de drc requerido
        - la configuración de PEQ
        - el ajuste de balance
    """
    global avisos

    if presets.has_section(presetID):
        avisos += [ "(presets) Ha seleccionado preset: " + presetID ]
        viasActivas = []

        for opcion in presets.options(presetID):
            valor = presets.get(presetID, opcion)
            
            if opcion in ["drc"]:
                drc_num = configura_drc_coeff(valor)

            if opcion in ["fr", "lo", "mi", "hi", "sw"]:
                via = opcion # solo para legibilidad
                atten, delay, pcm_name = valor.split()
                configura_via_coeff(via, pcm_name, filter_type)
                configura_via_atten(via, atten)
                configura_via_delay(via, delay)
                viasActivas.append(via)
                avisos += [ "(presets) Se configura la via " + via + " " + filter_type + ":\t" \
                            + atten + "\t" + delay + "\t" + pcm_name ]

            if opcion in ["balance"]:
                balance = ajusta_balance(valor)

            if opcion in ["peq"]:
                peq = ajusta_peq(valor)
        
        avisos += ["(presets) Enjoy!"]
        # Conectamos a la tarjeta solo las vias definidas en el preset:      
        conecta_tarjeta(viasActivas)

    else:
        presetID = "ERROR PRESET NO VALIDO"
        drc_num = drc_status
        balance = "0"
        peq = None
        
    for aviso in avisos:
        print aviso
    avisos = []
    
    return presetID, drc_num, balance, peq

def busca_preset(presetID):
    if presets.has_section(presetID):
        return presetID
    else:
        return None

def ajusta_balance(balance):
    # para ajustar el balance hay que hablar con el FIRtro para que quede reflejado en la web y en status
    # o sea que esta función no hace nada :-)
    return balance
           
def ajusta_peq(peq):
    # para ajustar el PEQ hay que hablar con el FIRtro para que quede reflejado en la web y en status
    # o sea que esta función no hace nada :-)
    return peq
           
def configura_drc_coeff(fName):
    """ funcion auxiliar para cargar el drc del preset seleccionado
    """
    global avisos
    # El DRC dedica un pcm para cada canal
    drc_coeffs = []
    for channel in "L", "R":
        filtro_pcm = channel + " " + fName + ".pcm"
        for coeff in brutefir.coeffs:
        # e.g.: [6, 'c_drc2_L', 'L RRreq FR_60Hz1st.pcm']
            if filtro_pcm == coeff[2]:
                drc_coeffs.append(coeff[1])

    # aquí vamos a hablar con el FIRtro en lugar de directamente con Brutefir
    # al objeto de respetar la gestión de DRCs integrada en el FIRtro.
    drc_nums = []            

    for drc_coeff in drc_coeffs:
        # e.g.: 'c_drc2_L' --> '2'
        drc_nums.append(drc_coeff[5])

    try:
        if drc_nums[0] == drc_nums[1]:
            # devolvemos el drc que hay que configurar para que se ocupe server_process.py
            return drc_nums[0]
            avisos += ["(presets) se configura drc num." + drc_nums[0] + " con filtro: " + fName]

    except:
        return "0"
        avisos += ["(presets) algo no ha ido bien localizando el drc"]
                
def configura_via_coeff(via, fName, filter_type):
    """ funcion auxiliar para cargar en Brutefir (orden CLI: cfc) el filtro de xover del preset seleccionado
    """
    #global avisos
    if "dirac" in fName:
        filtro_pcm = "dirac pulse"
    else:
        filtro_pcm = filter_type + "-" + fName + ".pcm"
        
    for coeff in brutefir.coeffs[2:]:           # eludimos recorrer los primeros coeff del EQ

        if filtro_pcm == coeff[2]:              # coeff[2] es el nombre del pcm
            
            bCoeff = coeff[1]                   # coeff[1] es el nombre del coeff en Brutefir
            
            for bFilter in vias_como_esta(via):
                
                tmp = "echo 'cfc \"" + bFilter + "\" \"" + bCoeff + "\";quit;' \
                       | nc localhost 3000"
                subprocess.check_output([tmp], shell=True)
                #avisos += [ "(presets) se configura la salida '" + bFilter + "' con filtro: " \
                #            + filter_type + " " + fName ]

def configura_via_atten(via, atten):
    """ funcion auxiliar para configurar la atten de una vía en Brutefir (orden CLI: cfoa) 
    """
    #global avisos
    for bFilter in vias_como_esta(via):
        
        atten = str(float(atten))
        
        tmp = "echo 'cfoa \"" + bFilter + "\" \"" + bFilter[2:] + "\" " + atten + ";quit;' \
               | nc localhost 3000"
        subprocess.check_output([tmp], shell=True)
        #avisos += [ "(presets) se configura el filter '" + bFilter + "' con atten: " + atten ]
    
def configura_via_delay(via, delay):
    """ funcion auxiliar para configurar el retardo de una vía en Brutefir (orden CLI: cod) 
    """
    #global avisos
    for bFilter in vias_como_esta(via):
        
        bOutput = bFilter[2:]
        delaySamples = str(int(float(delay)/1000*44100))
        
        tmp = "echo 'cod \"" + bOutput + "\" " + delaySamples + ";quit;' \
               | nc localhost 3000"
        subprocess.check_output([tmp], shell=True)
        #avisos += [ "(presets) se configura la salida '" + bOutput + "' con delay: " + delaySamples ]

# Subfuncion auxiliar para recorrer las etapas de filtrado
# del tipo indicado (fr, hi, mi, lo o sw):
def vias_como_esta(tipoVia):
    """ funcion auxiliar que proporciona las vias de subwoofer definidas en brutefir
    """ 
    viasComoEsta = []
    for filtroRunning in brutefir.filters_running:
        if tipoVia in filtroRunning[0]:
            viasComoEsta.append(filtroRunning[0])
    return viasComoEsta

def conecta_tarjeta(viasActivas):
    jack.attach("tmp")

    # disponemos de la funcion brutefir.outputs que contiene el mapeo de vias
    for output in brutefir.outputs:
        
        brutefirPort = "brutefir:" + output.split("/")[1].replace('"', '')
        jackPort     =               output.split("/")[0].replace('"', '')
    
    
        # ahora debemos evaluar si es una salida de una via activa
        salidaActiva = False
        for viaActiva in viasActivas:
            if viaActiva in output:
                salidaActiva = True
        if salidaActiva:
            jack.connect(brutefirPort, jackPort)
        else:
            jack.disconnect(brutefirPort, jackPort)

    jack.detach()
    
# OjO no simplificar, usado en server_process para pasarla a la web via json
def lista_de_presets():
    """ devuelve la lista de presets
    """
    return presets.sections()
    
# Para uso en la línea de comandos
def printa_presets(x="all"):
    """ muestra los presets definidos en el archivo presets.ini del altavoz
    """
    if x == "all":
        print "\n--- Presets disponibles:"
        for preset in presets.sections():
            print preset
    else:
        for preset in lista_de_presets():
            if x in preset:
                print "\n[" + preset + "]"
                for option in presets.options(preset):
                    print option.ljust(12), "=".ljust(4), presets.get(preset, option) 
    print

if __name__ == '__main__':
    if sys_argv[1:]:
        printa_presets(sys_argv[1].lower())
    else:
        print __doc__
        sys_exit(0)
