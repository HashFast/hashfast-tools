#! /usr/bin/env python

# Copyright (c) 2014, HashFast Technologies LLC
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   1.  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#   3.  Neither the name of HashFast Technologies LLC nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL HASHFAST TECHNOLOGIES LLC BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import csv
from collections import OrderedDict

from numpy import *
# If the package has been installed correctly, this should work:
import Gnuplot, Gnuplot.funcutils

def main(argv):
  csvfilename  = argv[0]
  print(csvfilename)
  with open(csvfilename, 'r') as csvfile:
    #fn = OrderedDict([('die',None),('frequency',None),('voltage',None),('hashrate',None),('hashes',None),('nonces',None),
    #                  ('lhw',None),('dhw',None),('chw',None),('temperature',None),('core_voltage',None),('thermal_cutoff',None)])
    csvreader = csv.DictReader(csvfile) #, fn)

    # A straightforward use of gnuplot.  The `debug=1' switch is used
    # in these examples so that the commands that are sent to gnuplot
    # are also output on stderr.
    g = Gnuplot.Gnuplot(debug=0)

    # frequency on the x-axis
    fmin  = 800
    fmax  = 1050
    fstep = 12.5
    f = arange(fmin, fmax, fstep)
    def findex(frq):
      assert frq >= fmin and frq < fmax
      return int( (frq - fmin +1) / fstep )

    # voltage on the y-axis
    vmin  = 840
    vmax  = 1100
    vstep = 5
    v = arange(vmin, vmax, vstep)
    def vindex(vlt):
      assert vlt >= vmin and vlt < vmax
      return (vlt - vmin) / vstep

    dies = [ {'die':i, 'results':None, 'x':None, 'y':None, 'hashrate':None } for i in range(4)]
    for i in range(4):
      die = dies[i]
      x = f[:,newaxis]
      y = v[newaxis,:]
      die['results']      = []
      die['x']            = f
      die['y']            = v
      die['hashrate']     = (x * y).astype(float)
      die['hashrate'].fill(nan)
      die['temperature']  = (x * y).astype(float)
      die['temperature'].fill(nan)

    for result in csvreader:

      # data
      die = result['die']         = int(result['die'])
      frq = result['frequency']   = int(result['frequency'])
      vlt = result['voltage']     = int(result['voltage'])
      result['core_voltage']      = float(result['core_voltage'])

      # did the die hit thermal
      result['thermal_cutoff'] = int(result['thermal_cutoff'])
      if result['thermal_cutoff'] is not 1:
        result['temperature']     = float(result['temperature'])
      else:
        result['temperature']     = nan

      # did the die compute enough hashes to compare
      result['hashes']            = int(result['hashes']) / 10**9
      if result['hashes'] > 30000:
        result['hashrate']        = float(result['hashrate']) / 10**9
        result['nonces']          = int(result['nonces'])
        result['lhw']             = int(result['lhw'])
        result['dhw']             = int(result['dhw'])
        result['chw']             = int(result['chw'])
      else:
        result['hashes']          = nan
        result['hashrate']        = nan
        result['nonces']          = nan
        result['lhw']             = nan
        result['dhw']             = nan
        result['chw']             = nan

      # fill each die properties
      die = dies[die]
      die['results'].append(result)
      die['hashrate'][findex(frq), vindex(vlt)] = result['hashrate']
      die['temperature'][findex(frq), vindex(vlt)] = result['temperature']

    # make output 
    try:
      os.mkdir('{0}'.format(csvfilename[:-4]))
    except OSError:
      pass

    for d in dies:

      g.title('HashFast HashRate Die {}'.format(d['die']))
      g.xlabel('Frequency (MHz)')
      g.ylabel('Voltage (mV)')
      g.zlabel('HR (GH/s)')

      # set gnuplot options
      g('set parametric')
      g('set style data pm3d')
      #g('set hidden')
      g('set contour base')
      g('set datafile missing "nan"')
      #g('set palette rgbformulae 31,-11,32')
      g('set zrange [80:180]')
      g('set xtics 25')
      g('set mxtics 2')
      g('set grid xtics mxtics ytics ztics')

      # The `binary=1' option would cause communication with gnuplot to
      # be in binary format, which is considerably faster and uses less
      # disk space.  (This only works with the splot command due to
      # limitations of gnuplot.)  `binary=1' is the default, but here we
      # disable binary because older versions of gnuplot don't allow
      # binary data.  Change this to `binary=1' (or omit the binary
      # option) to get the advantage of binary format.
      data_hashrate     = Gnuplot.GridData(d['hashrate'], d['x'], d['y'], binary=0)
      data_temperature  = Gnuplot.GridData(d['temperature'], d['x'], d['y'], binary=0, with_="pm3d at b")
      g.splot(data_hashrate, data_temperature)

      #g('set pm3d at b')

      #g.splot(Gnuplot.GridData(d['temperature'], d['x'], d['y'], binary=0))

      # show the plot to allow reposition
      #raw_input('Please press return to save plot...\n')

      # Save what we just plotted as a color postscript file.
      #g.hardcopy("{0}_die{1}.ps".format(csvfilename[:-4], d['die']), enhanced=1, color=1)
      g.hardcopy("{0}/{0}_die{1}.eps".format(csvfilename[:-4], d['die']), enhanced=1, color=1, mode='eps')
      g.hardcopy("{0}/{0}_die{1}.png".format(csvfilename[:-4], d['die']), terminal='png', fontsize='small')
      print('\n******** Saved plot to file ********\n')


    for d in dies:

      g.title('HashFast HashRate Die {}'.format(d['die']))
      g.xlabel('Voltage (mV)')
      g.ylabel('HashRate (GH/s)')
      
      # set gnuplot options
      #g('set parametric')
      g('set style data lines')
      #g('set hidden')
      g('set datafile missing "nan"')
      g('set yrange [140:190]')
      g('set key left')
      g('set mxtics 4')
      g('set mytics 10')
      g('set grid xtics mxtics ytics lw 1')

      frqs = [nan]*len(f)
      for frq in f:
        i = findex(frq)
        frqs[i] = Gnuplot.Data(v, d['hashrate'][i], title='{}MHz'.format(int(frq)))#, with_='')

      # Plot data alongside the Data PlotItem defined above:
      g.plot(*frqs)

      #g('set pm3d at b')

      #g.splot(Gnuplot.GridData(d['temperature'], d['x'], d['y'], binary=0))

      # show the plot to allow reposition
      #raw_input('Please press return to save plot...\n')

      # Save what we just plotted as a color postscript file.
      #g.hardcopy("{0}_die{1}_flat.ps".format(csvfilename[:-4], d['die']), enhanced=1, color=1)
      g.hardcopy("{0}/{0}_die{1}_flat.eps".format(csvfilename[:-4], d['die']), enhanced=1, color=1, mode='eps')
      g.hardcopy("{0}/{0}_die{1}_flat.png".format(csvfilename[:-4], d['die']), terminal='png', fontsize='small')
      print('\n******** Saved plot to file ********\n')

if __name__ == "__main__":
   main(sys.argv[1:])
