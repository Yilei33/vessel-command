import socket
import struct
import time
import threading
import sys
from datetime import datetime

# 配置信息
MULTICAST_GROUP = '226.100.100.101'  # 平台状态信息组播地址
TARGET_GROUP = '226.100.100.102'     # 水面目标信息组播地址
PORT = 0x6688                        # 组播端口(十进制为26760)
PACKET_LENGTH = 44                   # 平台状态信息包长度
MIN_TARGET_PACKET_LENGTH = 17     

# 无人艇编码字典（方便显示）
VESSEL_CODES = {
    0x5001: "无人艇 1号",
    0x5002: "无人艇 2号",
    0x5003: "无人艇 3号",
    0x5004: "无人艇 4号",
    0x5005: "无人艇 5号"
}

# 目标类型字典（示例，根据实际情况修改）
TARGET_TYPES = {
    0: "未知",
    1: "舰船",
    2: "小艇",
    3: "浮标",
    # ...其他目标类型
}
def convert_from_geo_format(geo_value):
    """
    将协议经纬度格式转换为度数
    
    参数:
    geo_value -- 按协议格式表示的经纬度值
    
    返回:
    float -- 转换后的度数
    """
    return float(geo_value) * 180.0 / (2**31)

def convert_angular_value(value):
    """
    将角度值从协议格式转换为度数
    
    参数:
    value -- 按协议格式表示的角度值
    
    返回:
    float -- 转换后的度数
    """
    return float(value) * 180.0 / (2**15)

def setup_multicast_socket():
    """
    创建并配置用于接收组播数据的套接字
    
    返回:
    socket -- 配置好的套接字
    """
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    # 允许端口复用
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 绑定到组播端口
    sock.bind(('', PORT))
    
    # 加入组播组
    group = socket.inet_aton(MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    return sock

def parse_vessel_status(data):
    """
    解析无人平台状态信息数据包
    
    参数:
    data -- 接收到的数据包(字节串)
    
    返回:
    dict -- 包含解析后信息的字典
    """
    if len(data) < PACKET_LENGTH:
        return {"error": f"数据包长度不足: {len(data)}/{PACKET_LENGTH}字节"}
    
    try:
        # 1-9. 解析数据包头
        unit_seq, unit_id, unit_length, timestamp, sender_code, secondary_id, receiver_code, \
        data_source, param_id = struct.unpack('>BBHIHHHBB', data[:16])
        
        # 检查数据包标识是否正确
        if unit_id != 0x03:
            return {"error": f"数据包标识错误: 0x{unit_id:02X}，预期: 0x03"}
        
        # 10-23. 解析数据字段
        longitude_raw, latitude_raw, altitude, speed, heading, course, course_rate, \
        cruise_mode, simulation_flag, gimbal_angle, ammo, fuel, body_angle, \
        reserved = struct.unpack('>iihhhhhBBhBBhh', data[16:])
        
        # 计算实际值
        longitude = convert_from_geo_format(longitude_raw)
        latitude = convert_from_geo_format(latitude_raw)
        speed_value = float(speed) / 10.0  # 精度0.1节
        heading_value = convert_angular_value(heading)
        course_value = convert_angular_value(course)
        gimbal_angle_value = convert_angular_value(gimbal_angle)
        body_angle_value = convert_angular_value(body_angle)
        
        # 返回解析结果
        vessel_name = VESSEL_CODES.get(sender_code, f"未知平台 (0x{sender_code:04X})")
        return {
            "序列号": unit_seq,
            "数据包ID": f"0x{unit_id:02X}",
            "长度": unit_length,
            "时间戳": timestamp,
            "平台": vessel_name,
            "二级标识": f"0x{secondary_id:04X}",
            "数据来源": "岸基控制台" if data_source else "无人平台",
            "经度": f"{longitude:.6f}°{'E' if longitude >= 0 else 'W'}",
            "纬度": f"{latitude:.6f}°{'N' if latitude >= 0 else 'S'}",
            "高度/深度": f"{altitude}米",
            "航速": f"{speed_value:.1f}节",
            "航向": f"{heading_value:.1f}°",
            "艏向": f"{course_value:.1f}°",
            "模拟标志": "模拟平台" if simulation_flag else "实装平台",
            "载弹量": ammo,
            "电/油余量": f"{fuel}%",
            "云台角度": f"{gimbal_angle_value:.1f}°",
            "机身角度": f"{body_angle_value:.1f}°"
        }
            
    except Exception as e:
        return {"error": f"解析数据包时出错: {e}"}

def display_status(status):
    """
    显示解析后的状态信息
    
    参数:
    status -- 包含解析后信息的字典
    """
    if "error" in status:
        print(f"\n错误: {status['error']}")
        return
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # 清屏 (ANSI转义序列)
    print("\033c", end="")
    
    # 显示标题
    print(f"=== 无人平台状态信息 | {current_time} ===")
    print(f"平台: {status['平台']} | 数据来源: {status['数据来源']} | {'模拟平台' if status['模拟标志'] == '模拟平台' else '实装平台'}")
    
    # 位置信息
    print(f"\n◆ 位置信息:")
    print(f"  • 经度: {status['经度']}")
    print(f"  • 纬度: {status['纬度']}")
    print(f"  • 高度/深度: {status['高度/深度']}")
    
    # 运动参数
    print(f"\n◆ 运动参数:")
    print(f"  • 航速: {status['航速']}")
    print(f"  • 航向: {status['航向']}")
    print(f"  • 艏向: {status['艏向']}")
    
    # 平台状态
    print(f"\n◆ 平台状态:")
    print(f"  • 电/油余量: {status['电/油余量']}")
    print(f"  • 载弹量: {status['载弹量']}")
    
    # 其他信息
    print(f"\n◆ 其他信息:")
    print(f"  • 云台角度: {status['云台角度']}")
    print(f"  • 机身角度: {status['机身角度']}")
    print(f"  • 序列号: {status['序列号']}")
    print(f"  • 时间戳: {status['时间戳']}")
    
    print(f"\n按 Ctrl+C 退出程序...")

def receiver_thread_func(sock, stop_event):
    """
    接收和处理数据的线程函数
    
    参数:
    sock -- 套接字
    stop_event -- 停止事件
    """
    try:
        sock.settimeout(1.0)  # 设置超时以便定期检查停止事件
        
        while not stop_event.is_set():
            try:
                # 接收数据
                data, addr = sock.recvfrom(PACKET_LENGTH)
                
                # 解析数据
                status = parse_vessel_status(data)
                
                # 显示结果
                display_status(status)
                
            except socket.timeout:
                # 超时，继续循环以检查停止事件
                continue
                
    except Exception as e:
        print(f"接收线程出错: {e}")
    finally:
        sock.close()


def setup_multicast_socket(multicast_group=MULTICAST_GROUP):
    """
    创建并配置用于接收组播数据的套接字
    
    参数:
    multicast_group -- 组播地址
    
    返回:
    socket -- 配置好的套接字
    """
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    # 允许端口复用
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 绑定到组播端口
    sock.bind(('', PORT))
    
    # 加入组播组
    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    return sock


def parse_surface_targets(data):
    """
    解析水面目标信息数据包
    
    参数:
    data -- 接收到的数据包(字节串)
    
    返回:
    dict -- 包含解析后信息的字典
    """
    if len(data) < MIN_TARGET_PACKET_LENGTH:
        return {"error": f"数据包长度不足: {len(data)}/{MIN_TARGET_PACKET_LENGTH}字节"}
    
    try:
        # 1-9. 解析数据包头
        unit_seq, unit_id, unit_length, timestamp, sender_code, secondary_id, receiver_code, \
        data_source, param_id = struct.unpack('>BBHIHHHBB', data[:16])
        
        # 检查数据包标识是否正确
        if unit_id != 0x03:
            return {"error": f"数据包标识错误: 0x{unit_id:02X}，预期: 0x03"}
        
        # 检查二级信息单元标识是否正确(0E20H)
        if secondary_id != 0x0E20:
            return {"error": f"二级信息单元标识错误: 0x{secondary_id:04X}，预期: 0x0E20"}
        
        # 10. 目标数量
        target_count = data[16]
        
        # 计算预期数据包长度
        expected_length = 17 + 26 * target_count
        if len(data) < expected_length:
            return {"error": f"数据包长度不足: {len(data)}/{expected_length}字节"}
        
        # 解析基本信息
        vessel_name = VESSEL_CODES.get(sender_code, f"未知平台 (0x{sender_code:04X})")
        base_info = {
            "序列号": unit_seq,
            "数据包ID": f"0x{unit_id:02X}",
            "长度": unit_length,
            "时间戳": timestamp,
            "平台": vessel_name,
            "二级标识": f"0x{secondary_id:04X}",
            "数据来源": "岸基控制台" if data_source else "无人平台",
            "目标数量": target_count
        }
        
        # 解析每个目标信息
        targets = []
        for i in range(target_count):
            # 计算目标数据在数据包中的起始位置
            offset = 17 + i * 26
            
            # 解析目标数据
            target_id, lon_raw, lat_raw, bearing, distance, speed, heading, target_type, \
            target_feature = struct.unpack('>HiiIHHHI', data[offset:offset+26])
            
            # 转换为实际值
            longitude = convert_from_geo_format(lon_raw)
            latitude = convert_from_geo_format(lat_raw)
            bearing_value = convert_angular_value(bearing)
            speed_value = float(speed) / 10.0  # 精度0.1节
            heading_value = float(heading) / 10.0  # 精度0.1度
            
            # 构建目标信息字典
            target_info = {
                "批号": target_id,
                "经度": f"{longitude:.6f}°{'E' if longitude >= 0 else 'W'}",
                "纬度": f"{latitude:.6f}°{'N' if latitude >= 0 else 'S'}",
                "方位": f"{bearing_value:.1f}°",
                "距离": f"{distance}米",
                "航速": f"{speed_value:.1f}节",
                "航向": f"{heading_value:.1f}°",
                "类型": TARGET_TYPES.get(target_type, f"未知类型({target_type})"),
                "特征": f"0x{target_feature:08X}"  # 十六进制显示特征码
            }
            targets.append(target_info)
        
        return {"基本信息": base_info, "目标列表": targets}
            
    except Exception as e:
        return {"error": f"解析数据包时出错: {e}"}


def display_surface_targets(target_data):
    """
    显示解析后的水面目标信息
    
    参数:
    target_data -- 包含解析后信息的字典
    """
    if "error" in target_data:
        print(f"\n错误: {target_data['error']}")
        return
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # 清屏 (ANSI转义序列)
    print("\033c", end="")
    
    # 显示基本信息
    base_info = target_data["基本信息"]
    print(f"=== 水面目标信息 | {current_time} ===")
    print(f"平台: {base_info['平台']} | 数据来源: {base_info['数据来源']} | 目标数量: {base_info['目标数量']}")
    
    # 显示目标列表
    targets = target_data["目标列表"]
    if not targets:
        print("\n未探测到目标")
    else:
        for i, target in enumerate(targets):
            print(f"\n◆ 目标 {i+1} (批号: {target['批号']}):")
            print(f"  • 位置: {target['经度']}, {target['纬度']}")
            print(f"  • 航行: 航速 {target['航速']}, 航向 {target['航向']}")
            print(f"  • 相对: 方位 {target['方位']}, 距离 {target['距离']}")
            print(f"  • 分类: {target['类型']}, 特征码 {target['特征']}")
    
    print(f"\n按 Ctrl+C 退出程序...")

def receiver_thread_func(sockets, stop_event):
    """
    接收和处理数据的线程函数
    
    参数:
    sockets -- 套接字字典，包含不同组播组的套接字
    stop_event -- 停止事件
    """
    try:
        # 设置所有套接字超时
        for sock in sockets.values():
            sock.settimeout(0.5)  # 设置较短的超时便于轮询多个套接字
        
        while not stop_event.is_set():
            for group, sock in sockets.items():
                try:
                    # 尝试从当前套接字接收数据
                    data, addr = sock.recvfrom(1024)  # 使用较大的缓冲区以适应可变长度的包
                    
                    # 根据组播地址选择解析方法
                    if group == MULTICAST_GROUP:
                        # 平台状态信息
                        status = parse_vessel_status(data)
                        display_status(status)
                    elif group == TARGET_GROUP:
                        # 水面目标信息
                        targets = parse_surface_targets(data)
                        display_surface_targets(targets)
                        
                except socket.timeout:
                    # 超时，检查下一个套接字
                    continue
                    
        # 关闭所有套接字
        for sock in sockets.values():
            sock.close()
                    
    except Exception as e:
        print(f"接收线程出错: {e}")
def main():
    """主程序"""
    print("=== 无人平台信息接收程序 ===")
    print(f"正在监听组播地址:")
    print(f"- {MULTICAST_GROUP}:{PORT} (平台状态信息)")
    print(f"- {TARGET_GROUP}:{PORT} (水面目标信息)")
    print("正在等待数据...\n")
    
    try:
        # 创建套接字字典，监听多个组播地址
        sockets = {
            MULTICAST_GROUP: setup_multicast_socket(MULTICAST_GROUP),
            TARGET_GROUP: setup_multicast_socket(TARGET_GROUP)
        }
        
        # 创建停止事件
        stop_event = threading.Event()
        
        # 创建并启动接收线程
        receiver = threading.Thread(target=receiver_thread_func, args=(sockets, stop_event))
        receiver.daemon = True
        receiver.start()
        
        # 等待用户退出
        try:
            while receiver.is_alive():
                receiver.join(1.0)
        except KeyboardInterrupt:
            print("\n程序中止...")
        finally:
            stop_event.set()  # 通知线程停止
            receiver.join(2.0)  # 等待线程结束
        
    except Exception as e:
        print(f"错误: {e}")
        
    print("程序已退出")

if __name__ == "__main__":
    main()