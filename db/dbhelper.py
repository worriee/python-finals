from sqlite3 import connect,Row

database:str = "db/school.db"

def getprocess(sql:str,vals:list)->list:
    conn:any = None
    cursor:any = None
    data:list = []
    try:
        conn = connect(database)
        conn.row_factory = Row
        cursor = conn.cursor()
        cursor.execute(sql,vals)
        data=cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return data
        
        
def postprocess(sql:str,vals:list)->bool:
    conn:any = None
    cursor:any = None
    try:
        conn = connect(database)
        cursor = conn.cursor()
        cursor.execute(sql,vals)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return True if cursor.rowcount>0 else False   
        
def getall(table:str)->list:
    sql:str = f"SELECT * FROM `{table}`"
    return getprocess(sql,[])
    
def getrecord(table:str,**kwargs)->list:
    keys:list = list(kwargs.keys())
    vals:list = list(kwargs.values())
    flds:list = []
    for key in keys:
        flds.append("`"+key+"`=?")
    fld:str = " AND ".join(flds)
    sql:str = f"SELECT * FROM `{table}` WHERE {fld}"
    return getprocess(sql,vals)
    
def deleterecord(table:str,**kwargs)->bool:
    keys:list = list(kwargs.keys())
    vals:list = list(kwargs.values())
    sql:str = f"DELETE FROM `{table}` WHERE `{keys[0]}`=?"
    return postprocess(sql,vals)
    
def addrecord(table:str,**kwargs)->bool:
    keys:list = list(kwargs.keys())
    vals:list = list(kwargs.values())
    #insert into `student`(`idno`,`name`,`course`) values(?,?,?)
    q:list = ['?']*len(keys)
    qmarks:str = ",".join(q)
    flds:str = "`,`".join(keys)
    sql:str = f"INSERT INTO `{table}`(`{flds}`) VALUES({ qmarks})"
    return postprocess(sql,vals)
    
def updaterecord(table:str,**kwargs)->bool:
    keys:list = list(kwargs.keys())
    vals:list = list(kwargs.values())
    #update `students` SET `lastname`=?,`firstname`=? WHERE `idno`='1000'
    flds:list = []
    newvals:list = []
    for i in range(1,len(keys)):
        flds.append("`"+keys[i]+"`=?")
        newvals.append(vals[i])
    fld:str = ",".join(flds)
    newvals.append(vals[0])
    sql:str = f"UPDATE `{table}` SET {fld} WHERE `{keys[0]}`=?"
    return postprocess(sql,newvals)
 