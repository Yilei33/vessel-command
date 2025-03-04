import socket
import struct
import time

# 配置信息
SOURCE_IP = '192.168.2.1'  # 信源主机IP地址（岸基指控）
DEST_IP = '192.168.2.2'    # 信宿主机IP地址（无人艇控制） 
DEST_PORT = 0x6198         # 信宿协议端口 (十进制为25000)

# 无人艇编码列表
VESSEL_CODES = {
    1: 0x5001,
    2: 0x5002,
    3: 0x5003,
    4: 0x5004,
    5: 0x5005
}

def get_timestamp():
    """获取当前时间戳(当日)，精度0.1ms"""
    # 获取今日0点的时间戳
    now = time.time()
    today_midnight = now - (now % 86400)
    # 计算从0点到现在的毫秒数（精度0.1ms）
    ms_since_midnight = int((now - today_midnight) * 10000)
    return ms_since_midnight

def create_speed_packet(seq_num, vessel_id, speed, direction):
    """创建航速航向命令数据包"""
    
    # 1. 信息单元序号 (1字节)
    unit_seq = seq_num & 0xFF
    
    # 2. 信息单元标识 (1字节): 01H
    unit_id = 0x01
    
    # 3. 信息单元长度 (2字节): 1CH (28字节)
    unit_length = 0x001C
    
    # 4. 时戳 (4字节)
    timestamp = get_timestamp()
    
    # 5. 发送无人系统节点编码 (2字节): 0701H
    sender_code = 0x0701
    
    # 6. 二级信息单元标识 (2字节): 0340H
    secondary_id = 0x0340
    
    # 7. 接收无人系统节点编码 (2字节)
    receiver_code = VESSEL_CODES.get(vessel_id, 0x5001)
    
    # 8. 信息单元数据来源标识 (1字节): 1(岸基控制台)
    data_source = 0x01
    
    # 9. 信息单元参数扩展标识 (1字节): 7(航向航速指令)
    param_id = 0x07
    
    # 10. 航速指令 (2字节): 有符号16位短整型，精度0.1节
    speed_value = int(speed * 10)
    
    # 11. 航向指令 (2字节): 无符号16位短整型，精度0.1度
    direction_value = int(direction * 10) & 0xFFFF
    
    # 12. 命令生成下达时间 (4字节): 不用
    command_time = 0
    
    # 13. 命令流水号 (2字节): 不用
    command_seq = 0
    
    # 14. 命令执行平台编码 (2字节)
    platform_code = receiver_code
    
    # 打包数据
    packet = struct.pack(
        '>BBHIHHHBBHHHIH',  # 大端序格式
        unit_seq,           # 1字节
        unit_id,            # 1字节
        unit_length,        # 2字节
        timestamp,          # 4字节
        sender_code,        # 2字节
        secondary_id,       # 2字节
        receiver_code,      # 2字节
        data_source,        # 1字节
        param_id,           # 1字节
        speed_value,        # 2字节
        direction_value,    # 2字节
        command_time,       # 4字节
        command_seq,        # 2字节
        platform_code       # 2字节
    )
    
    return packet

def send_speed(packet):
    """通过UDP发送命令数据包"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 发送数据包
        sock.sendto(packet, (DEST_IP, DEST_PORT))
        print(f"命令已发送到 {DEST_IP}:{DEST_PORT}")
        
        # 打印十六进制数据包内容（调试用）
        hex_data = ' '.join(f'{b:02X}' for b in packet)
        print(f"数据包内容: {hex_data}")
        
        return True
    except Exception as e:
        print(f"发送失败: {e}")
        return False
    finally:
        sock.close()

def convert_to_geo_format(degree):
    """
    将经纬度转换为协议要求的格式
    数据单位：180/2^31
    
    参数:
    degree -- 经度或纬度，单位为度
    
    返回:
    int -- 按协议格式转换后的整数值
    """
    # 使用公式: degree/180 * 2^31
    return int(degree / 180.0 * 2**31)

def create_route_packet(seq_num, vessel_id, waypoints):
    """
    创建航线作战命令数据包
    
    参数:
    seq_num -- 序列号
    vessel_id -- 无人艇ID (1-5)
    waypoints -- 路径点列表，每个元素是一个包含经度、纬度和航速的元组 [(lon1, lat1, speed1), (lon2, lat2, speed2), ...]
               经度和纬度为度数，航速为节
    
    返回:
    bytes -- 编码后的数据包
    """
    # 路径点数量
    waypoint_count = len(waypoints)
    if waypoint_count < 2 or waypoint_count > 255:
        raise ValueError("路径点数量必须在2-255之间")
    
    # 1. 信息单元序号 (1字节)
    unit_seq = seq_num & 0xFF
    
    # 2. 信息单元标识 (1字节): 01H
    unit_id = 0x01
    
    # 3. 信息单元长度 (2字节): (38+15N)字节
    # 38字节基础长度 + 每个路径点15字节
    unit_length = 38 + 15 * waypoint_count
    
    # 4. 时戳 (4字节)
    timestamp = get_timestamp()
    
    # 5. 发送无人系统节点编码 (2字节): 0701H
    sender_code = 0x0701
    
    # 6. 二级信息单元标识 (2字节): 0340H
    secondary_id = 0x0340
    
    # 7. 接收无人系统节点编码 (2字节)
    receiver_code = VESSEL_CODES.get(vessel_id, 0x5001)
    
    # 8. 信息单元数据来源标识 (1字节): 1(岸基控制台)
    data_source = 0x01
    
    # 9. 信息单元参数扩展标识 (1字节): 1(航线作战)
    param_id = 0x01
    
    # 10. 兵力命令代码 (2字节): 不用
    command_code = 0
    
    # 11. 命令生成下达时间 (2字节): 不用
    command_time = 0
    
    # 12. 命令流水号 (2字节): 不用
    command_seq = 0
    
    # 13. 命令执行平台编码 (2字节)
    platform_code = receiver_code
    
    # 14. 命令执行平台航线号 (2字节): 不用
    route_num = 0
    
    # 15. 航线航向 (2字节): 不用
    route_direction = 0
    
    # 16. 航线路径开始时间 (4字节): 不用
    route_start_time = 0
    
    # 17. 航线路径区间数量 (1字节): 1
    route_section_count = 1
    
    # 18. 路径区预设任务命令 (2字节): 不用
    route_command = 0
    
    # 19. 区间内路径点数量N (1字节)
    waypoint_count_field = waypoint_count
    
    # 构建基本包头 - 确保格式字符串与参数数量匹配
    format_str = '>BBHIHHHBBHHHHHIHBHB'
    header_values = (
        unit_seq,           # 1字节 (1)
        unit_id,            # 1字节 (2)
        unit_length,        # 2字节 (3)
        timestamp,          # 4字节 (4)
        sender_code,        # 2字节 (5)
        secondary_id,       # 2字节 (6)
        receiver_code,      # 2字节 (7)
        data_source,        # 1字节 (8)
        param_id,           # 1字节 (9)
        command_code,       # 2字节 (10)
        command_time,       # 2字节 (11)
        command_seq,        # 2字节 (12)
        platform_code,      # 2字节 (13)
        route_num,          # 2字节 (14)
        route_direction,    # 2字节 (15)
        route_start_time,   # 4字节 (16)
        route_section_count,# 1字节 (17)
        route_command,      # 2字节 (18)
        waypoint_count_field# 1字节 (19)
    )
    
    packet = struct.pack(format_str, *header_values)
    
    # 添加所有路径点数据 - 每个路径点15字节
    for idx, (lon, lat, speed) in enumerate(waypoints):
        # 20. 路径点类型 (1字节): 不用
        waypoint_type = 0
        
        # 21. 路径点经度 (4字节)
        lon_value = convert_to_geo_format(lon)
        
        # 22. 路径点纬度 (4字节)
        lat_value = convert_to_geo_format(lat)
        
        # 23. 路径点航速 (2字节): 精度0.1节
        speed_value = int(speed * 10)
        
        # 24. 路径点到达耗时 (4字节): 不用
        time_value = 0
        
        # 添加当前路径点数据 (共15字节)
        waypoint_data = struct.pack('>BiiHI', waypoint_type, lon_value, lat_value, speed_value, time_value)
        packet += waypoint_data
    
    # 26. 任务重规划时间 (2字节): 不用
    replan_time = 0
    packet += struct.pack('>H', replan_time)
    
    # 检查数据包总长度是否符合预期
    expected_length = 38 + 15 * waypoint_count
    if len(packet) != expected_length:
        print(f"警告: 数据包长度 ({len(packet)}) 与预期长度 ({expected_length}) 不符！")
    print(f"已创建航线命令数据包, 长度: {len(packet)}")
    return packet


def send_route_command(vessel_id, waypoints):
    """
    发送航线作战命令
    
    参数:
    vessel_id -- 无人艇ID (1-5)
    waypoints -- 路径点列表，每个包含经纬度和航速
    
    返回:
    bool -- 命令是否成功发送
    """
    # 获取当前序列号
    seq_num = 1  # 可以改为全局变量或从某处获取
    
    # 创建航线命令数据包
    try:
        packet = create_route_packet(seq_num, vessel_id, waypoints)
        # 发送数据包
        return send_speed(packet)
    except Exception as e:
        print(f"创建航线命令失败: {e}")
        return False
    
def main():
    """主程序"""
    seq_num = 1  # 初始序列号
    
    print("=== 无人艇命令发送程序 ===")
    print("岸基指控 -> 无人艇控制")
    
    while True:
        try:
            print("\n请选择命令类型:")
            print("1. 航速航向命令")
            print("2. 航线作战命令")
            print("0. 退出程序")
            
            choice = input("请输入选择 (0-2): ")
            
            if choice == '0':
                break
                
            vessel_id = int(input("\n请输入无人艇编号 (1-5): "))
            if not 1 <= vessel_id <= 5:
                print("错误: 无人艇编号必须在1-5之间")
                continue
            
            if choice == '1':
                # 航速航向命令
                speed = float(input("请输入航速 (节, 负值表示反向): "))
                direction = float(input("请输入航向 (度, 0-359.9): "))
                
                if not 0 <= direction < 360:
                    print("错误: 航向必须在0-359.9度之间")
                    continue
                
                # 创建并发送航速航向命令
                packet = create_speed_packet(seq_num, vessel_id, speed, direction)
                if send_speed(packet):
                    seq_num = (seq_num + 1) & 0xFF
                
            elif choice == '2':
                # 航线作战命令
                try:
                    waypoint_count = int(input("请输入路径点数量 (2-255): "))
                    if not 2 <= waypoint_count <= 255:
                        print("错误: 路径点数量必须在2-255之间")
                        continue
                        
                    waypoints = []
                    for i in range(waypoint_count):
                        print(f"\n--- 路径点 {i+1} ---")
                        lon = float(input(f"请输入经度 (度, -180~180): "))
                        lat = float(input(f"请输入纬度 (度, -90~90): "))
                        speed = float(input(f"请输入航速 (节): "))
                        
                        if not -180 <= lon <= 180:
                            print("错误: 经度必须在-180~180度之间")
                            raise ValueError("经度值无效")
                            
                        if not -90 <= lat <= 90:
                            print("错误: 纬度必须在-90~90度之间")
                            raise ValueError("纬度值无效")
                        
                        waypoints.append((lon, lat, speed))
                    
                    # 发送航线作战命令
                    if send_route_command(vessel_id, waypoints):
                        seq_num = (seq_num + 1) & 0xFF
                    
                except ValueError as e:
                    print(f"输入错误: {e}")
                    continue
                    
            else:
                print("错误: 无效的选择")
                continue
                
            # 询问是否继续
            continue_choice = input("\n是否继续发送命令? (y/n): ").lower()
            if continue_choice != 'y':
                break
                
        except ValueError:
            print("输入错误: 请输入有效的数值")
        except KeyboardInterrupt:
            print("\n程序已终止")
            break
    
    print("程序结束")

if __name__ == "__main__":
    main()