from controller import USVController
import time

def main():
    # 创建控制器实例
    usv = USVController(port='/dev/ttyUSB0', baudrate=115200)
    
    try:
        # 启动通信
        usv.start()
        print("无人艇控制系统启动")
        
        # 请求状态信息
        usv.request_status()
        time.sleep(1)  # 等待状态更新
        
        # 设置直线行驶
        usv.set_movement(throttle=30, steering=0)
        print("无人艇前进...")
        time.sleep(5)
        
        # 向右转弯
        usv.set_movement(throttle=20, steering=30)
        print("无人艇右转...")
        time.sleep(3)
        
        # 向左转弯
        usv.set_movement(throttle=20, steering=-30)
        print("无人艇左转...")
        time.sleep(3)
        
        # 减速停止
        usv.set_movement(throttle=0, steering=0)
        print("无人艇停止")
        time.sleep(2)
        
        # 设置航点导航
        usv.set_waypoint(latitude=39.9042, longitude=116.4074, speed=30)
        print("设置航点导航")
        time.sleep(10)
        
        # 紧急停止
        usv.emergency_stop()
        print("紧急停止")
        
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        # 停止通信
        usv.stop()
        print("无人艇控制系统关闭")

if __name__ == "__main__":
    main()