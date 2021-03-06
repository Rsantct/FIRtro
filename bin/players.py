#!/usr/bin/python
# -*- coding: utf-8 -*-
""" modulo auxiliar llamado por server_inputs.py
    para pausar/reaundar los players integrados
    al objeto de poder ahorrar %CPU en máquinas pequeñas.
"""
# v1.0b
# - En algunos sistemas con escritorio, puede que mpd no arranque con FIRtro, aunque 
#   si arrancará si FIRtro se reinicia durante la sesión de escritorio (under investigation).
#   Para salvar este inconveniente se relanza MPD si resume_players=True.
# v1.0c
# - revisión: se llama a mpd según el path indicado audio/config
# - se evalua que mpc indique que MPD está "paused" para poder reanudar la reproducción.


# NOTAS para mplayer:
#   Si ordenamos "stop", mplayer desaparecerá de jack (noconnect en .mplayer/config),
#   por tanto ordenaremos pausas.
#   Pero OjO el pausado es singular, ya que en Mplayer "pause" funciona como un 'pauseToggle'
#   La solución es recurrir a los prefixes 'pausing' detallados en:
#   http://www.mplayerhq.hu/DOCS/tech/slave.txt

from subprocess import Popen, check_output
from getconfig import *
from getstatus import *
from wait4 import wait4result

def manage_pauses(input_name):
    """ Gestiona pausas opcionales de players integrados,
    """

    if pause_players:

        if 'mpd'    not in input_name.lower() and load_mpd:
            print "(players) Pausando MPD."
            Popen("mpc pause > /dev/null 2>&1 &", shell=True)

        if 'mopidy' not in input_name.lower() and load_mopidy:
            print "(players) Pausando MOPIDY."
            Popen("mpc -p 7700 pause > /dev/null 2>&1", shell=True)

        if 'tdt'    not in input_name.lower() and load_mplayer_tdt:
            print "(players) Pausando  MPLAYER_TDT."
            Popen("echo pausing pause > " + HOME + "/tdt_fifo", shell=True)

        if 'tdt'    not in input_name.lower() and load_mplayer_cdda:
            print "(players) Pausando  MPLAYER_CDDA."
            Popen("echo pausing pause > " + HOME + "/cdda_fifo", shell=True)

    if pause_players and resume_players:

        if 'mpd'    in input_name.lower() and load_mpd:
            try:
                check_output("pgrep mpd", shell=True)
            except:
                Popen(mpd_path + " > /dev/null 2>&1", shell=True)
                wait4result("jack_lsp", "mpd", tmax=10, quiet=True)
            if "paused" in check_output("mpc", shell=True):
                print "(players) Reanudando MPD."
                Popen("mpc play > /dev/null 2>&1", shell=True)

        if 'mopidy' in input_name.lower() and load_mopidy:
            if "paused" in check_output("mpc -p 7700", shell=True):
                print "(players) Reanudando MOPIDY."
                Popen("mpc -p 7700 play > /dev/null 2>&1", shell=True)

        if 'tdt'    in input_name.lower() and load_mplayer_tdt:
            if wait4result("jack_lsp", "mplayer_tdt", tmax=2, quiet=True):
                # resucita la reproducción (basta con dar un comando)
                print "(players) Consultando la emisora de Mplayer:"
                Popen("echo get_file_name > " + HOME + "/tdt_fifo", shell=True)
            else:
                print "(players) Resintonizando TDT presintonía: " + radio
                Popen("radio_channel.py " + radio, shell=True)

        if 'cd'     in input_name.lower() and load_mplayer_cdda:
            print "(players) Reanudando  MPLAYER_CDDA."
            Popen("echo pausing_toggle pause > " + HOME + "/cdda_fifo", shell=True)


if __name__ == "__main__":
    print __doc__
