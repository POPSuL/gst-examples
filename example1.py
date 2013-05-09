#env python2
# coding=utf-8

import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GObject

import os
import signal
import argparse

Gst.init("")
signal.signal(signal.SIGINT, signal.SIG_DFL)
GObject.threads_init()


def parse_args():
    parser = argparse.ArgumentParser(prog='example1.py')
    parser.add_argument('--volume', help='Указать громкость (0-100)', type=int, default=100)
    parser.add_argument('location')
    args = parser.parse_args()
    return args


class Player():

    def __init__(self, args):
        self.pipeline = self.create_pipeline(args)

        ## получаем шину по которой рассылаются сообщения
        ## и вешаем на нее обработчик
        message_bus = self.pipeline.get_bus()
        message_bus.add_signal_watch()
        message_bus.connect('message', self.message_handler)

        ## устанавливаем громкость
        self.pipeline.get_by_name('volume').set_property('volume', args.volume / 100.)

    def create_source(self, location):
        """create_source(str) -> Gst.Element"""
        if not args.location.startswith('http') and not os.path.exists(args.location):
            raise IOError("File %s doesn't exists" % args.location)

        if location.startswith('http'):
            source = Gst.ElementFactory.make('souphttpsrc', 'source')
        else:
            source = Gst.ElementFactory.make('filesrc', 'source')
        source.set_property('location', location)
        return source

    def create_pipeline(self, args):
        """create_pipeline() -> Gst.Pipeline"""

        pipeline = Gst.Pipeline()
        ## Создаем нужные элементы для плеера
        source = self.create_source(args.location)
        decodebin = Gst.ElementFactory.make('decodebin', 'decodebin')
        audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert')
        volume = Gst.ElementFactory.make('volume', 'volume')
        audiosink = Gst.ElementFactory.make('autoaudiosink', 'autoaudiosink')

        ## decodebin имеет динамические pad'ы, которые так же динамически
        ## необходимо линковать
        def on_pad_added(decodebin, pad):
            pad.link(audioconvert.get_static_pad('sink'))
        decodebin.connect('pad-added', on_pad_added)

        ## добавляем все созданные элементы в pipeline
        [pipeline.add(k) for k in [source, decodebin, audioconvert, volume, audiosink]]

        ## линкуем элементы между собой по схеме:
        ## *src* -> (decodebin + audioconvert) -> volume -> autoaudiosink
        source.link(decodebin)
        audioconvert.link(volume)
        volume.link(audiosink)
        return pipeline

    def play(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def message_handler(self, bus, message):
        """Обработчик сообщений"""
        struct = message.get_structure()
        if message.type == Gst.MessageType.EOS:
            print('Воспроизведение окончено.')
            Gtk.main_quit()
        elif message.type == Gst.MessageType.TAG and message.parse_tag() and struct.has_field('taglist'):
            print('GStreamer обнаружил в потоке мета-теги')
            taglist = struct.get_value('taglist')
            for x in range(taglist.n_tags()):
                name = taglist.nth_tag_name(x)
                print('  %s: %s' % (name, taglist.get_string(name)[1]))
        else:
            pass


if __name__ == "__main__":
    args = parse_args()
    player = Player(args)
    player.play()
    Gtk.main()
