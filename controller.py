from communication import USVCommunication, CommandType
import threading
import struct
import time

class USVController:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.comm = USVCommunication(port, baudrate)
        self.comm.set_rx_callback(self._on_data_received)
        self.status = {
            'latitude': 0.0,
            'longitude': 0.0,
            'heading': 0.0,
            'speed': 0.0,
            'battery': 0,
        }
        self.last_status_update = 0
    
    def start(self):
        """启动通信"""
        self.comm.start()
        # 启动心跳定时器
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()
    
    def stop(self):
        """停止通信"""
        self.comm.stop()
    
    def _heartbeat_loop(self):
        """发送心跳包"""
        while self.comm.running:
            self.send_heartbeat()
            time.sleep(1)
    
    def send_heartbeat(self):
        """发送心跳包"""
        timestamp = int(time.time())
        data = struct.pack("<I", timestamp)
        return self.comm.send_command(CommandType.HEARTBEAT.value, data)
    
    def set_movement(self, throttle, steering):
        """设置运动参数
        
        Args:
            throttle: 油门值 (-100 到 100)
            steering: 转向值 (-100 到 100)
        """
        # 将参数限制在有效范围内
        throttle = max(-100, min(100, throttle))
        steering = max(-100, min(100, steering))
        
        data = struct.pack("<hh", int(throttle * 10), int(steering * 10))
        return self.comm.send_command(CommandType.CONTROL_MOVEMENT.value, data)
    
    def request_status(self):
        """请求状态信息"""
        return self.comm.send_command(CommandType.GET_STATUS.value)
    
    def set_waypoint(self, latitude, longitude, speed=0):
        """设置航点
        
        Args:
            latitude: 纬度 (浮点数)
            longitude: 经度 (浮点数)
            speed: 期望速度 (0-100)
        """
        data = struct.pack("<ddB", latitude, longitude, speed)
        return self.comm.send_command(CommandType.SET_WAYPOINT.value, data)
    
    def emergency_stop(self):
        """紧急停止"""
        return self.comm.send_command(CommandType.EMERGENCY_STOP.value)
    
    def _on_data_received(self, cmd_id, data):
        """处理接收到的数据"""
        try:
            if cmd_id == CommandType.GET_STATUS.value:
                if len(data) >= 17:  # 确保数据长度足够
                    lat, lon, heading, speed, battery = struct.unpack("<ddfHB", data)
                    self.status = {
                        'latitude': lat,
                        'longitude': lon,
                        'heading': heading,
                        'speed': speed / 10.0,  # 转换为实际单位
                        'battery': battery,
                    }
                    self.last_status_update = time.time()
                    print(f"状态更新: {self.status}")
            # 处理其他命令...
            
        except Exception as e:
            print(f"解析数据错误: {e}")