#!/usr/bin/env python

# Ear Candy - Pulseaduio sound managment tool
# Copyright (C) 2008 Jason Taylor
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import datetime
import re
import os
import copy
import sys
import shutil
from xml.dom.minidom import *

from pulseaudio.PulseAudio import PulseAudio 

class ParCur():

    def __init__(self):
        self.cur = None

        self.pa_samples = {}  # samples by id
        self.pa_clients = {}  # clients by id
        self.pa_sinks = {}
        self.pa_sink_inputs = {}
        self.pa_outputs = {}

        # whether to use dB or linear for numeric volume display
        self.use_dezibel = True
        self.volume_step = 0.05
        self.volume_max_soft = 1.00
        self.volume_max_hard = 1.50

    def run(self, init_cb, server = None):
        self.pa = PulseAudio(init_cb, self.on_new_pa_client, self.on_remove_pa_client, self.on_new_pa_sink, self.on_remove_pa_sink, self.on_new_pa_sink_input, self.on_remove_pa_sink_input, self.on_volume_change, self.on_new_sample, self.on_remove_sample, server)

        # set some helper functions
        self.volume_to_linear = self.pa.volume_to_linear
        self.volume_to_dB = self.pa.volume_to_dB

    def on_init(self):
        if self.cur:
            self.cur.update()

    def on_volume_change(self, level):
        return
        #print self.managed_output_name, level

    def on_remove_pa_output(self, index):
        if self.pa_outputs.has_key(index):
            self.__print("removed pa output", self.pa_outputs[index])
            del self.pa_outputs[index]

    # add new output to ours
    def on_new_pa_output(self, index, struct, startup):
        if not self.pa_outputs.has_key(index):
            output = Output(struct)
            self.__print("new pa output", output)
            self.pa_outputs[index] = output

    def move_all_sinks(self):
        if self.managed_output_name:
            for sink in self.pa_sink_inputs.values():
                if not sink.client.output:
                    self.pa.move_sink(sink.index, self.managed_output_name)

    def on_new_pa_client(self, index, struct, proplist):
        # Link all clients with same name into same object
        if not self.pa_clients.has_key(index):
            self.__print("new client: ", "index:")

            self.pa_clients[index] = Client(index, struct, proplist)
        else:
            self.pa_clients[index].update(index, struct, proplist)
            self.__print("changed client: ", "index:")

        # and update view
        self.update()

    def on_remove_pa_client(self, index):
        if self.pa_clients.has_key(index):
            client = self.pa_clients[index]

            self.__print("remove client", index, client.name)

            # remove from by ID list
            del self.pa_clients[index]

            self.update()

    def on_new_pa_sink(self, index, struct, props):
        if not self.pa_sinks.has_key(index):
            self.__print("new sink:", index, struct.name)
            # create new
            self.pa_sinks[index] = Sink(index, struct, props)
        else:
            self.__print("changed sink:", index, struct.name)
            # update old
            self.pa_sinks[index].update(struct, props)

        self.update()

    def on_remove_pa_sink(self, index):
        self.__print("remove sink", index)
        del self.pa_sinks[index]

        self.update()

    def on_new_pa_sink_input(self, index, struct):
        if not self.pa_sink_inputs.has_key(index):
            self.__print("new sink input:", index, struct.name)
            self.pa_sink_inputs[index] = SinkInput(index, struct)
        else:
            self.__print("changed sink input:", index, struct.name)
            self.pa_sink_inputs[index].update(struct)

        self.update()

    def on_remove_pa_sink_input(self, index):
        if self.pa_sink_inputs.has_key(index):
            self.__print("remove sink input", index)
            del self.pa_sink_inputs[index]

        self.update()

    def on_new_sample(self, index, struct):
        if not self.pa_samples.has_key(index):
            self.__print("new sample:", index, struct.name)
            self.pa_samples[index] = Sample(index, struct)
        else:
            self.__print("changed sample:", index, struct.name)
            self.pa_samples[index].update(struct)

        self.update()
        return

    def on_remove_sample(self, index):
        if self.pa_samples.has_key(index):
            self.__print("remove sample", index)
            del self.pa_samples[index]

        self.update()
        return

    def get_sink_inputs_by_client(self, index):
        result = []
        for input in self.pa_sink_inputs.values():
            if input.client == index:
                result.append(input)
        return result

    def get_sink_inputs_by_sink(self, index):
        result = []
        for input in self.pa_sink_inputs.values():
            if input.sink == index:
                result.append(input)
        return result

    def move_sink_input(self, sink_input_index, sink_index):
        self.pa.move_sink_input(sink_input_index, sink_index)

    def move_client(self, client):
        self.__print("move client", client.name)

        for sink in client.sinks.values(): 
            if client.output:
                self.__print("move", sink.name, "to", sink.client.output)
                self.pa.move_sink(sink.index, sink.client.output)
            else:
                self.__print("move", sink.name, "to", self.managed_output_name)
                self.pa.move_sink(sink.index, self.managed_output_name)

    def set_sink_volume(self, index, volume):
        cvolume = self.pa.volume_from_linear(volume)
        self.pa.set_sink_volume(index, cvolume)

    def set_sink_input_volume(self, index, volume):
        cvolume = self.pa.volume_from_linear(volume)
        self.pa.set_sink_input_volume(index, cvolume)

    def kill_sink_input(self, index):
        self.pa.kill_sink_input(index)

    def update(self):
        print "\a"
        sys.stdout.flush()
        # return
        if self.cur:
            self.cur.redraw()

    def __print(self, *args):
        sys.stderr.write(str(args))
        return

par = ParCur()

from Curses import Curses
from Client import Client
from Sink import Sink
from SinkInput import SinkInput
from Sample import Sample
