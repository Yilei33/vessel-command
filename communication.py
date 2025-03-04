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

def create_command_packet(seq_num, vessel_id, speed, direction):
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

def send_command(packet):
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

def main():
    """主程序"""
    seq_num = 1  # 初始序列号
    
    print("=== 航速航向命令发送程序 ===")
    print("岸基指控 -> 无人艇控制")
    
    while True:
        try:
            # 获取用户输入
            vessel_id = int(input("\n请输入无人艇编号 (1-5): "))
            if not 1 <= vessel_id <= 5:
                print("错误: 无人艇编号必须在1-5之间")
                continue
                
            speed = float(input("请输入航速 (节, 负值表示反向): "))
            direction = float(input("请输入航向 (度, 0-359.9): "))
            
            if not 0 <= direction < 360:
                print("错误: 航向必须在0-359.9度之间")
                continue
            
            # 创建并发送命令
            packet = create_command_packet(seq_num, vessel_id, speed, direction)
            if send_command(packet):
                # 命令发送成功后递增序列号
                seq_num = (seq_num + 1) & 0xFF
            
            # 询问是否继续
            choice = input("\n是否继续发送命令? (y/n): ").lower()
            if choice != 'y':
                break
                
        except ValueError:
            print("输入错误: 请输入有效的数值")
        except KeyboardInterrupt:
            print("\n程序已终止")
            break
    
    print("程序结束")

if __name__ == "__main__":
    main()