
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

#import packet_watcher
import packet_limiter
import scapy_watcher as packet_watcher

from kivy.config import Config

Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '1000')


class PortInfo(BoxLayout):
    def __init__(self,port, item, **kwargs):
        super(PortInfo, self).__init__(**kwargs)
        i = item#kwargs['item']
        self.net_data = i

        #port = kwargs['port']

        self.port_label = Label(text=str(port))
        self.total_label = Label()
        self.raw_speed_label = Label()
        self.speed_label = Label()
        self.add_widget(self.port_label)
        self.add_widget(self.total_label)
        self.add_widget(self.raw_speed_label)
        self.add_widget(self.speed_label)

        self.up_limit = TextInput()
        self.down_limit = TextInput()
        self.enable_limit = ToggleButton(text="limit?")
        self.add_widget(self.up_limit)
        self.add_widget(self.down_limit)
        self.add_widget(self.enable_limit)

        self.Blue = port & 40
        self.Green = (port >> 8) & 40
        self.Red = (port >> 16) & 40
        with self.canvas.before:
            Color(self.Red/40.0, self.Green/40.0, self.Blue/40.0, .5)  # green; colors range from 0-1 not 0-255
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update(self, v):
        self.net_data = v
        self.speed_label.text = "{:.1f}".format(v['speed'] / 1000.0)
        self.total_label.text = "{:.1f}".format(v['total'] / 1000.0)
        self.raw_speed_label.text = "{:.1f}".format(v['speed_raw'] / 1000.0)

sort_key = 'speed'

class TableHeader(BoxLayout):
    def __init__(self, **kwargs):
        super(TableHeader, self).__init__(**kwargs)

        self.port_label = Button(text="port", on_release=self.set_sort)
        self.port_label.sort_key = "port"
        self.total_label = Button(text="total\nkb", on_release=self.set_sort)
        self.total_label.sort_key = "total"
        self.raw_speed_label = Button(text="raw\nspd kb", on_release=self.set_sort)
        self.raw_speed_label.sort_key = "speed_raw"
        self.speed_label = Button(text="speed\nkb", on_release=self.set_sort)
        self.speed_label.sort_key = "speed"
        self.add_widget(self.port_label)
        self.add_widget(self.total_label)
        self.add_widget(self.raw_speed_label)
        self.add_widget(self.speed_label)

        self.up_limit_label = Label(text="up\nlimit")
        self.down_limit_label = Label(text="down\nlimit")
        self.enable_limit_label = Label(text="enable\nlimit")
        self.add_widget(self.up_limit_label)
        self.add_widget(self.down_limit_label)
        self.add_widget(self.enable_limit_label)

        self.size_hint_y = 0.1

    def set_sort(self, obj):
        global sort_key
        sort_key = obj.sort_key
        print(sort_key)


'''def cmp_PI(ix, iy):
    x = ix.net_data[sort_key]
    y = iy.net_data[sort_key]
    if x > y:
        return 1
    elif x == y:
        return 0
    else:  # x < y
        return -1'''


class MainView(GridLayout):
    def __init__(self, **kwargs):
        kwargs['cols'] = 1
        super(MainView, self).__init__(**kwargs)

        self.main_table = BoxLayout(orientation='vertical')
        self.main_table.add_widget(TableHeader())
        self.main_list = GridLayout(cols=1, spacing=1, row_default_height= '30dp', row_force_default= True, size_hint_y=None)
        self.main_list.bind(minimum_height=self.main_list.setter('height'))
        self.scroll_view = ScrollView()
        self.main_table.add_widget(self.scroll_view)
        self.scroll_view.add_widget(self.main_list)
        self.add_widget(Label(text="LinNetLim\n press apply to limit selected ports", size_hint_y=.15))
        self.add_widget(self.main_table)

        Clock.schedule_interval(self.update_cb, 0.5)

        self.connected_widgets = {}
        self.info_panel = BoxLayout(orientation='vertical', size_hint_x=.2)

        applybtn = Button(text='Apply', size_hint_y=.1)
        applybtn.bind(on_release=self.apply_limits)
        self.add_widget(applybtn)
        unapplybtn = Button(text='Un-Apply', size_hint_y=.1)
        unapplybtn.bind(on_release=self.clear_limits)
        self.add_widget(unapplybtn)
        #self.info_panel.add_widget(clearbtn)

    #generate a list of ports with up/down limit and pass to the packet limiter
    def apply_limits(self, obj):
        indata = []
        for r in self.main_list.children:
            if r.enable_limit.state == 'down':
                indata.append({
                    "port": int(r.port_label.text),
                    "up_limit": int(r.up_limit.text),
                    "down_limit": int(r.down_limit.text)
                })
        packet_limiter.set_from_ports_list(indata)


    def clear_limits(self, obj):
        packet_limiter.reset_all()

    #read list of ports, with raw_speed, total and speed
    def update_cb(self, dt):
        for k in list(packet_watcher.portcounts.keys()):
            v = packet_watcher.portcounts[k]
            w = self.connected_widgets.get(k, None)
            if not w:
                w = PortInfo(port=k, item=v, height=100)
                self.connected_widgets[k] = w
                self.main_list.add_widget(w)
            w.update(v)
        #list(self.main_list.children).sort(key=cmp_PI)
        super(self.main_list.children.__class__, self.main_list.children).sort(key=lambda child: child.net_data[sort_key])


class NetLimitApp(App):
    def build(self):
        parent = MainView()
        packet_watcher.start_background_thread()
        self.mainwidget = parent
        return parent


mainapp = NetLimitApp()

if __name__ == '__main__':
    mainapp.run()
