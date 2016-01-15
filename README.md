==========================================
configuration syntax:
==========================================
### run from shell:
```
    >python2.7 generator.py test.conf  [Enter]

    >python2.7 generator.py test.py    [Enter]
```


### import syntax
```
    from ../tool.conf import *
    from tool.conf import baselist,extlist
```
### template is just a simple string-filling function
### dollar-values in a template means parameters
```
    new tmplate $TmpName
    '''
        $colname:$coltype  $grpname:'dowhat' $grp2:"dowhat"
    '''
        -- this is a comment
        ## also a comment
        
        -not comment,error
        #not comment,error
    for example:
    new template template -- no keywords or name restriction
    '''
    create table if not exists $tablename
    (
    $Cols -- all-case-insensitive
    )
    partition by list($partitionby) (partition default)
    
    '''
```
### list can be filled into template as a string when using as a parameter, 
### list unfolds itself into a comma-separated string
### vars that can be refered in list declaration: $this|$type
``` 
    new list $Listname
    '''
    $col_name:$type $tmpl_name:"max($this)" $tmpl_name2:"min($this)"
    '''
```
### list support + - operations
```
    new list $list2 = $list1 + $list3 - $list4
    new lsit renamed_list = original_list
```
### call templates like a function
```
    new template tnew = grpby($a=$b,$c="static_str")
    new template rnamed_t = tnew
    ## this is an overwrite
    new template grpby = tnew
```
### export clause
```
    export $alias
    export list1, temp2 ,t3,t4
        t5,t6
```
### Use Generator in your python-SQL source file:
```
    from generator import gen
    vars=gen("test.conf")
    print vars['created_table']['content']

```
#### and you will get:
```
    create table smoba
    (
    statis_date bigint,
    uin bigint,
    appid string)
    comment 'created by hendrix'
    partition by list(statis_date,uin)
```

#### embeding syntax
##### embeding lets you put configs into your source file which means you don't need an extra .conf file to manage. 
```
    ##
    ## By XXX 
    ## date 2015
    ##

    #@ from std.conf import *
    #@     ## get simple create select rename
    #@ from smoba_user_stock_lite_preprocess.py import list_preprocess,tablename
    #@ 
    #@ new template preprocess_tablename = tablename
    #@ 
    #@ new template tablename
    #@     '''
    #@     smoba_user_basic_lite
    #@     '''
    #@ export tablename

    from generator import G
    g = G() # no param, means this python file is conf-embeded.

    def py_main():
        print "hello"
        print g['tablename']
```
##### embed-conf will be ignored by python. it won't affect your src