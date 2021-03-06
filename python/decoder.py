import pyModeS as pms
import socket
import time
import mysql.connector
import threading

plane=[]
planedata=[]

db=mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="airplane"

)
dbcur=db.cursor()


reset_sql=f"DELETE FROM `airplane`"
dbcur.execute(reset_sql)
db.commit()


class Position:
    def __init__(self,icao):
        self.icao=icao
        self.msg1=None
        self.msg2=None
        self.live=1
    def msgeven(self,msg,dt):
        self.tc1=dt
        self.msg1=msg
    
    def msgodd(self,msg,dt):
        self.tc2=dt
        self.msg2=msg 

    def cal_pos(self):
        if self.msg1 and self.msg2:
            position=pms.adsb.position(self.msg1,self.msg2,self.tc1,self.tc2)
            altitude=pms.adsb.altitude(self.msg1)
            print(f'ICAO:{self.icao} Position:{position,altitude}')
            position_sql=f"UPDATE `airplane` SET `latitude` = '{position[0]}', `longitude` = '{position[1]}', `altitude` = '{altitude}' WHERE ICAO = '{self.icao}'"
            dbcur.execute(position_sql)
            db.commit()
            

def data():
    
    print("listening")
    while True:
        data_byte = socket.recv(512)
        data_str = bytes.decode(data_byte)
        data = data_str.replace('*', '').replace(';', '').replace('\r\n', '')
        datatime=time.time()
        # print(data)
        decode(data,datatime)


def decode(msg,dt):
    db=mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="airplane"

        )
    dbcur=db.cursor()
    
    if len(msg) == 28:           # wrong data length
        # print(msg,end='\n')
        df = pms.df(msg)
        if df == 17:
            icao = pms.adsb.icao(msg)
            if icao in plane:
                pass
            else:
                # insert icao to db
                icaosql=f"Insert Into airplane(ICAO) Value ('{icao}')"
                dbcur.execute(icaosql)
                
                # insert plane to list
                plane.append(icao)
                # create Position obj
                planedata.append(Position(icao))
                
            plane_index=plane.index(icao)

            tc = pms.adsb.typecode(msg)
            if 1 <= tc <= 4:
                callsign = pms.adsb.callsign(msg)
                print("ICAO: {} Callsign: {}".format(icao, callsign), end="\n")
                # update callsign to db
                callsign_sql=f"UPDATE `airplane` SET `callsign` = '{callsign}' WHERE `ICAO` = '{icao}'"
                dbcur.execute(callsign_sql)
                
            if tc == 19:
                airborne_velocity = pms.adsb.velocity(msg)
                print("ICAO: {} Speed: {} ".format(
                    icao, airborne_velocity), end="\n")
                velocity_sql=f"UPDATE `airplane` SET `ground_speed` = '{airborne_velocity[0]}', `heading` = '{airborne_velocity[1]}', `rate_of_climb` = '{airborne_velocity[2]}' WHERE `airplane`.`ICAO` = '{icao}'"
                dbcur.execute(velocity_sql)
                
            if 5 <= tc <= 18:
                
                if pms.adsb.oe_flag(msg):
                    planedata[plane_index].msgodd(msg,dt)
                else:
                    planedata[plane_index].msgeven(msg,dt)
                
                planedata[plane_index].cal_pos()
            
            planedata[plane_index].live=1
            live_sql=f"UPDATE `airplane` SET `live` = '{1}' WHERE `ICAO` = '{icao}'"
            dbcur.execute(live_sql)
            db.commit() 

def live():
    db=mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="airplane"

)
    dbcur=db.cursor()
    print('counting')
    while True:
        time.sleep(1)
        for i,item in enumerate(planedata):
            item.live+=1
            if(item.live>300):
                delete_sql=f"DELETE FROM `airplane` WHERE `airplane`.`ICAO` = '{item.icao}'"
                dbcur.execute(delete_sql)
                    
                del plane[i]
                del planedata[i]
            else:
                live_sql=f"UPDATE `airplane` SET `live` = {item.live} WHERE `ICAO` = '{item.icao}'"
                dbcur.execute(live_sql)
        db.commit()    
        

            
        
        

                



print("strat")
socket = socket.socket()
socket.connect(('localhost', 47806))
t1=threading.Thread(target=data,daemon=True)
t2=threading.Thread(target=live,daemon=True)
t1.start()
t2.start()

t1.join()
t2.join()

print('end')
