# Docker-compose部署多容器项目+pycharm管理项目

## 前述

Django在生产环境的部署还是比较复杂的, 令很多新手望而生畏, 幸运的是使用Docker容器化技术可以大大简化我们Django在生产环境的部署并提升我们应用的可移植性。Docker 是一个开源的应用容器引擎，让开发者可以打包他们的应用以及依赖包到一个可移植的镜像中，然后发布到任何流行的 Linux机器上。

**本文中内容分为两项**

1. 采用docker容器化部署服务，使用docker-compose编排管理容器
2. 采用pycharm远程连接服务器，轻松修改云端项目



### docker-compose概述

Docker-compose是一个用来定义和运行复杂应用的 Docker 工具。使用 docker-compose 后不再需要使用 shell 脚本来逐一创建和启动容器，还可以通过 docker-compose.yml 文件构建和管理复杂多容器组合。

*ubuntu安装*

```python
 # Step 1: 以ubuntu为例，下载docker-compose
 $ sudo curl -L https://github.com/docker/compose/releases/download/1.17.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
 # Step 2: 给予docker-compose可执行权限
 $ sudo chmod +x /usr/local/bin/docker-compose
 # Step 3: 查看docker-compose版本
 $ docker-compose --version
```

注意：安装docker-compose前必需先安装好docker。



### Django + Uwsgi + Nginx + MySQL + Redis组合容器示意图

1. **Django + Uwsgi容器**：核心应用程序，处理动态请求
2. **MySQL 容器**：数据库服务
3. **Redis 容器**：缓存服务
4. **Nginx容器**：反向代理服务并处理静态资源请求

这四个容器的依赖关系是：Django+Uwsgi 容器依赖 Redis 容器和 MySQL 容器，Nginx 容器依赖Django+Uwsgi容器。为了方便容器间的相互访问和通信，我们使用docker-compose时可以给每个容器取个别名，这样访问容器时就可以直接使用别名访问，而不使用Docker临时给容器分配的IP了。

![image-20230409111607389](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409111607389.png)

**项目布局属性图：**

新建了一个compose文件夹，专门存放用于构建其它容器镜像的Dockerfile及配置文件。compose文件夹与django项目的根目录myproject同级。这样做的好处是不同的django项目可以共享compose文件夹。

```
myproject_docker 
├─.idea
│  └─inspectionProfiles
├─compose
│  ├─mysql
│  │  ├─conf
│  │  └─init
│  ├─nginx
│  │  ├─log
│  │  └─ssl
│  ├─redis
│  └─uwsgi
└─myproject
    ├─.idea
    │  └─inspectionProfiles
    ├─apps
    ├─media
    ├─message
    │  ├─migrations
    │  │  └─__pycache__
    │  └─__pycache__
    ├─myproject
    │  └─__pycache__
    ├─openaigpt
    │  └─__pycache__
    ├─static
    └─templates
```

嘿嘿，好不好奇树形图哪里来的？

点个赞再说~_~

```
win+R输入cmd进入dos
tree 项目根目录 > 生成的树形结构文件保存地址
比如：
tree .\myproject_docker\ > .\myproject_docker\tree.txt
```

不胡扯了，接下来正式部署！！！

## 正式部署docker-compose

### 第一步：编写docker-compose.yml文件

修改过的docker-compose.yml的核心内容如下。我们定义了4个数据卷，用于挂载各个容器内动态生成的数据，比如MySQL的存储数据，redis生成的快照、django+uwsgi容器中收集的静态文件以及用户上传的媒体资源。这样即使删除容器，容器内产生的数据也不会丢失。

我们还定义了3个网络，分别为`nginx_network`(用于nginx和web容器间的通信)，`db_network`(用于db和web容器间的通信)和`redis_network`(用于redis和web容器间的通信)。

整个编排里包含4项容器服务，别名分别为`redis`, `db`, `nginx`和`web`，接下来我们将依次看看各个容器的Dockerfile和配置文件。

```

version: "3"

volumes: # 自定义数据卷
  db_vol: #定义数据卷同步存放容器内mysql数据
  redis_vol: #定义数据卷同步存放redis数据
  media_vol: #定义数据卷同步存放web项目用户上传到media文件夹的数据
  static_vol: #定义数据卷同步存放web项目static文件夹的数据

networks: # 自定义网络(默认桥接), 不使用links通信
  nginx_network:
    driver: bridge
  db_network:
    driver: bridge
  redis_network: 
    driver: bridge

services:
  redis:
    image: redis:latest
    command: redis-server /etc/redis/redis.conf # 容器启动后启动redis服务器
    networks:
      - redis_network
    volumes:
      - redis_vol:/data # 通过挂载给redis数据备份
      - ./compose/redis/redis.conf:/etc/redis/redis.conf # 挂载redis配置文件
    ports:
      - "6379:6379"
    restart: always # always表容器运行发生错误时一直重启

  db:
    image: mysql
    env_file:  
      - ./myproject/.env # 使用了环境变量文件
    networks:  
      - db_network
    volumes:
      - db_vol:/var/lib/mysql:rw # 挂载数据库数据, 可读可写
      - ./compose/mysql/conf/my.cnf:/etc/mysql/my.cnf # 挂载配置文件
      - ./compose/mysql/init:/docker-entrypoint-initdb.d/ # 挂载数据初始化sql脚本
    ports:
      - "3306:3306" # 与配置文件保持一致
    restart: always

  web:
    build: ./myproject
    expose:
      - "8000"
    volumes:
      - ./myproject:/var/www/html/myproject # 挂载项目代码
      - static_vol:/var/www/html/myproject/static # 以数据卷挂载容器内static文件
      - media_vol:/var/www/html/myproject/media # 以数据卷挂载容器内用户上传媒体文件
      - ./compose/uwsgi:/tmp # 挂载uwsgi日志
    networks:
      - nginx_network
      - db_network  
      - redis_network 
    depends_on:
      - db
      - redis
    restart: always
    tty: true
    stdin_open: true

  nginx:
    build: ./compose/nginx
    ports:
      - "80:80"
      - "443:443"
    expose:
      - "80"
    volumes:
      - ./compose/nginx/nginx.conf:/etc/nginx/conf.d/nginx.conf # 挂载nginx配置文件
      - ./compose/nginx/ssl:/usr/share/nginx/ssl # 挂载ssl证书目录
      - ./compose/nginx/log:/var/log/nginx # 挂载日志
      - static_vol:/usr/share/nginx/html/static # 挂载静态文件
      - media_vol:/usr/share/nginx/html/media # 挂载用户上传媒体文件
    networks:
      - nginx_network
    depends_on:
      - web
    restart: always
```

### 第二步：编写Web (Django+Uwsgi)镜像和容器所需文件

构建Web镜像(Django+Uwsgi)的所使用的Dockerfile如下所示:

```
# 建立 python 3.9环境
FROM python:3.9

# 安装netcat
RUN apt-get update && apt install -y netcat

# 镜像作者魏什码
MAINTAINER WSM

# 设置 python 环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 可选：设置镜像源为国内
COPY pip.conf /root/.pip/pip.conf

# 容器内创建 myproject 文件夹
ENV APP_HOME=/var/www/html/myproject
RUN mkdir -p $APP_HOME
WORKDIR $APP_HOME

# 将当前目录加入到工作目录中（. 表示当前目录）
ADD . $APP_HOME

# 更新pip版本
RUN /usr/local/bin/python -m pip install --upgrade pip

# 安装项目依赖
RUN pip install -r requirements.txt

# 移除\r in windows
RUN sed -i 's/\r//' ./start.sh

# 给start.sh可执行权限
RUN chmod +x ./start.sh

# 数据迁移，并使用uwsgi启动服务
ENTRYPOINT /bin/bash ./start.sh
```

本Django项目所依赖的`requirements.txt`内容如下所示：

```
# django
django==4.1.7
# uwsgi
uwsgi==2.0.18
# mysql
mysqlclient==1.4.6
# redis
django-redis==4.12.1
redis==3.5.3
# for images
Pillow==8.2.0
openai==0.27.4
djangorestframework==3.14.0
PyMySQL==1.0.2
django-cors-headers==3.14.0
python-dotenv==0.21.1
```

`start.sh`脚本文件内容如下所示。最重要的是最后一句，使用uwsgi.ini配置文件启动Django服务。

```
#!/bin/bash
# 从第一行到最后一行分别表示：
# 1. 等待MySQL服务启动后再进行数据迁移。nc即netcat缩写
# 2. 收集静态文件到根目录static文件夹，
# 3. 生成数据库可执行文件，
# 4. 根据数据库可执行文件来修改数据库
# 5. 用 uwsgi启动 django 服务
# 6. tail空命令防止web容器执行脚本后退出
while ! nc -z db 3306 ; do
    echo "Waiting for the MySQL Server"
    sleep 3
done

python manage.py collectstatic --noinput&&
python manage.py makemigrations&&
python manage.py migrate&&
uwsgi --ini /var/www/html/myproject/uwsgi.ini&&
tail -f /dev/null

exec "$@"
```

`uwsgi.ini`配置文件如下所示： 

```
[uwsgi]

project=myproject
uid=www-data
gid=www-data
base=/var/www/html

chdir=%(base)/%(project)
module=%(project).wsgi:application
master=True
processes=2

socket=0.0.0.0:8000
chown-socket=%(uid):www-data
chmod-socket=664

vacuum=True
max-requests=5000

pidfile=/tmp/%(project)-master.pid
daemonize=/tmp/%(project)-uwsgi.log

#设置一个请求的超时时间(秒)，如果一个请求超过了这个时间，则请求被丢弃
harakiri = 300
post buffering = 8192
buffer-size= 65535
#当一个请求被harakiri杀掉会，会输出一条日志
harakiri-verbose = true

#开启内存使用情况报告
memory-report = true

#设置平滑的重启（直到处理完接收到的请求）的长等待时间(秒)
reload-mercy = 10

#设置工作进程使用虚拟内存超过N MB就回收重启
reload-on-as= 1024
```

### 第三步：编写Nginx镜像和容器所需文件

构建Nginx镜像所使用的Dockerfile如下所示：

```
# nginx镜像compose/nginx/Dockerfile

FROM nginx:latest

# 删除原有配置文件，创建静态资源文件夹和ssl证书保存文件夹
RUN rm /etc/nginx/conf.d/default.conf \
&& mkdir -p /usr/share/nginx/html/static \
&& mkdir -p /usr/share/nginx/html/media \
&& mkdir -p /usr/share/nginx/ssl

# 设置Media文件夹用户和用户组为Linux默认www-data, 并给予可读和可执行权限,
# 否则用户上传的图片无法正确显示。
RUN chown -R www-data:www-data /usr/share/nginx/html/media \
&& chmod -R 775 /usr/share/nginx/html/media

# 添加配置文件
ADD ./nginx.conf /etc/nginx/conf.d/

# 关闭守护模式
CMD ["nginx", "-g", "daemon off;"]
```

Nginx的配置文件如下所示

```

# nginx配置文件
# compose/nginx/nginx.conf

upstream django {
    ip_hash;
    server web:8000; # Docker-compose web服务端口
}

# 配置http请求，80端口
server {
    listen 80; # 监听80端口
    server_name 127.0.0.1; # 可以是nginx容器所在ip地址或127.0.0.1，不能写宿主机外网ip地址

    charset utf-8;
    client_max_body_size 10M; # 限制用户上传文件大小

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    location /static {
        alias /usr/share/nginx/html/static; # 静态资源路径
    }

    location /media {
        alias /usr/share/nginx/html/media; # 媒体资源，用户上传文件路径
    }

    location / {
        include /etc/nginx/uwsgi_params;
        uwsgi_pass django;
        uwsgi_read_timeout 600;
        uwsgi_connect_timeout 600;
        uwsgi_send_timeout 600;

        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_redirect off;
        proxy_set_header X-Real-IP  $remote_addr;
       # proxy_pass http://django;  # 使用uwsgi通信，而不是http，所以不使用proxy_pass。
    }
}
```

### 第四步：编写Db (MySQL)容器配置文件

启动MySQL容器我们直接使用官方镜像即可，不过我们需要给MySQL增加配置文件。

```
# compose/mysql/conf/my.cnf
[mysqld]
user=mysql
default-storage-engine=INNODB
character-set-server=utf8
secure-file-priv=NULL # mysql 8 新增这行配置
default-authentication-plugin=mysql_native_password  # mysql 8 新增这行配置

port            = 3306 # 端口与docker-compose里映射端口保持一致
#bind-address= localhost #一定要注释掉，mysql所在容器和django所在容器不同IP

basedir         = /usr
datadir         = /var/lib/mysql
tmpdir          = /tmp
pid-file        = /var/run/mysqld/mysqld.pid
socket          = /var/run/mysqld/mysqld.sock
skip-name-resolve  # 这个参数是禁止域名解析的，远程访问推荐开启skip_name_resolve。

[client]
port = 3306
default-character-set=utf8

[mysql]
no-auto-rehash
default-character-set=utf8
```

我们还需设置MySQL服务启动时需要执行的脚本命令, 注意这里的用户名和password必需和docker-compose.yml里与MySQL相关的环境变量(.env)保持一致。

```
# compose/mysql/init/init.sql
Alter user 'dbuser'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
GRANT ALL PRIVILEGES ON myproject.* TO 'dbuser'@'%';
FLUSH PRIVILEGES;
```

***`.env`文件内容如下所示：***

```
MYSQL_ROOT_PASSWORD=123456
MYSQL_USER=dbuser
MYSQL_DATABASE=myproject
MYSQL_PASSWORD=password
```

### 第五步：编写Redis 容器配置文件

启动redis容器我们直接使用官方镜像即可，不过我们需要给redis增加配置文件。大部分情况下采用默认配置就好了，这里我们只做出了如下几条核心改动：

```
# compose/redis/redis.conf
# Redis 5配置文件下载地址
# https://raw.githubusercontent.com/antirez/redis/5.0/redis.conf

# 请注释掉下面一行，变成#bind 127.0.0.1,这样其它机器或容器也可访问
bind 127.0.0.1

# 取消下行注释，给redis设置登录密码。这个密码django settings.py会用到。
requirepass yourpassword
```

### 第六步：修改Django项目settings.py

在你准备好docker-compose.yml并编排好各容器的Dockerfile及配置文件后，请先不要急于使用Docker-compose命令构建镜像和启动容器。这时还有一件非常重要的事情要做，那就是修改Django的settings.py, 提供mysql和redis服务的配置信息。最重要的几项配置如下所示：

```
# 生产环境设置 Debug = False 
Debug = False

# 设置ALLOWED HOSTS 
ALLOWED_HOSTS = ['your_server_IP', 'your_domain_name']

# 设置STATIC ROOT 和 STATIC URL 
STATIC_ROOT = os.path.join(BASE_DIR, 'static') 
STATIC_URL = "/static/"

# 设置MEDIA ROOT 和 MEDIA URL 
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 
MEDIA_URL = "/media/"


# 设置数据库。这里用户名和密码必需和docker-compose.yml里mysql环境变量保持一致  DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.mysql',
         'NAME': 'myproject', # 数据库名
         'USER':'dbuser', # 你设置的用户名 - 非root用户
         'PASSWORD':'password', # # 换成你自己密码
         'HOST': 'db', # 注意：这里使用的是db别名，docker会自动解析成ip
         'PORT':'3306', # 端口
     }
 }
# 设置redis缓存。这里密码为redis.conf里设置的密码 
 CACHES = {
     "default": {
         "BACKEND": "django_redis.cache.RedisCache",
         "LOCATION": "redis://redis:6379/1", #这里直接使用redis别名作为host ip地址
         "OPTIONS": {
             "CLIENT_CLASS": "django_redis.client.DefaultClient",
             "PASSWORD": "yourpassword", # 换成你自己密码
         },
     }
 }
```

### 第七步：使用docker-compose 构建镜像并启动容器组服务

现在我们可以使用docker-compose命名构建镜像并启动容器组了。

```
 # 进入docker-compose.yml所在文件夹，输入以下命令构建镜像
 sudo docker-compose build
 # 启动容器组服务    -d  表示后台运行服务
 sudo docker-compose up     
 #关闭
 sudo docker-compose down
 #查看镜像启动情况
 sudo docker ps
 
 #重启
 sudo docker-compose restart
```

> 默认情况下，`docker-compose up`启动的容器都在前台，控制台将会同时打印所有容器的输出信息，可以很方便进行调试。当通过`Ctrl+c`停止命令时，所有容器将会停止。如果希望在后台启动并运行所有的容器，使用`docker-compose up -d`。

如果一切顺利，此时你应该可以看到四个容器都已经成功运行了。

![image-20230409112934553](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409112934553.png)

此时打开你的浏览器，输入你服务器的ip地址或域名指向地址，你就应该可以看到网站已经上线啦。



滴滴！！！如此项目即部署成功了。原来上云这么简单~_~



## pycharm连接服务器

### 为啥要扯一嘴这个呢？

我上面部署好了服务，接下来我修改Django项目，升级Django项目的时间，每次我都要经过代码托管平台，或者是用xftp连接上传文件，感觉真的是太太太太太太麻烦了，所以说呢，不如在pycharm上将项目绑定！！！！

经过本人许久的搜集文档，最终在官方文档上找到了这个方法，嘎嘎受益。

### 前提

- pycharm专业版
- 远程服务器

倘若你没有专业版，就不行！社区版不支持此功能。

如果你是学生的话，你可以用学校邮箱申请出来一个！

### 1、首先，我们要找到设置，通过file-settings得到

![image-20230409113853817](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409113853817.png)

### 2、打开设置以后，通过Build, Execution, Deployment找到Deployment

![image-20230409113942910](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409113942910.png)

### 3、添加选择选项sftp

![image-20230409114005876](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114005876.png)

### 4、新建一个服务

（名字随您意）

![image-20230409114246793](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114246793.png)

### 5、测试按钮测试是否成功

![image-20230409114338137](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114338137.png)

### 6、确定以后，就返回Root Path步骤，这个是设置服务器的根路径，你可以选择一个根路径，也可以只写/

![image-20230409114549198](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114549198.png)

### 7、设置映射，Local Path需要填写本地的项目路径，Deployment Pat需要填写的服务器的路径，

**注意**，服务器的路径是从之前设置的服务器根路径开始写的相对路径。

![image-20230409114526138](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114526138.png)

### 8、设置好之后，应当来说，就已经配置成功了。你在本地写的文件就会被同步上传到服务器上。如果没有及时自动上传，你也可以右键点击你要上传的文件，通过Deployment手动选择upload

![image-20230409114712816](%E8%85%BE%E8%AE%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.assets/image-20230409114712816.png)

如果以上步骤你都已经照着一模一样做好了，那么，恭喜你，本地和服务器的连接已经建立成功了。此时你写代码就可以同步到服务器上了。

### 代码运行

注意，此时只是设置了代码的同步上传，但并没有选择代码在服务器上运行。也就是说，虽然代码会被同步上传到服务器上，但是此时点击运行代码，仍然是在本地运行。

如果你觉得，你非常有必要让代码要在服务器上运行，而非本地的话，那么还需要设置一下python的解释器。

- 同正常设置python解释器一样，找到添加python interpreter，并且，选择ssh interpreter
- 新添加或者选择一个已有的服务器端的python解释器，此时，就可以完成点击运行，在服务器上运行代码。

**注意：要正确的设置服务器端的python解释器的路径地址，以及下边的映射地址，也就是本地地址和服务器上的地址之间的对应关系。**

## 总结

使用docker-compose工具分七步在生成环境下部署Django + Uwsgi + Nginx + MySQL + Redis，过程看似很复杂，但很多Dockerfile，项目布局及docker-compose.yml都是可以复用的。

花时间学习并练习本章内容是非常值得的！

pycharm同步代码的这一功能并非是必须的，但是方便！本人提倡。尤其是体现在你使用flask或者django进行网站的部署上时。

pycharm专业版的这一功能还是非常强大的。如果你正好有远程服务器可以使用的话，建议把这篇文章好好学习一下。





## 序章

#### 当重新构建容器时：

```
  #列出当前所有的 Docker 镜像。
  sudo docker images
  
  #强制删除所有的 Docker 镜像。$(sudo docker images -a -q) 表示将 sudo docker images -a -q 的输出作为 sudo docker rmi -f 命令的参数传递，从而批量删除所有 Docker 镜像。
  sudo docker rmi -f $(sudo docker images -a -q)
  
  #停止并删除 Docker Compose 中定义的所有容器，同时删除所有挂载的数据卷。
  sudo docker-compose down -v
  
  #再次列出当前所有的 Docker 镜像，确认是否已经删除成功。
  sudo docker images
  
  #根据 docker-compose.yml 文件中的配置，构建 Docker 镜像。
  sudo docker-compose build
  
  #再次列出当前所有的 Docker 镜像，确认是否已经成功构建。
  sudo docker images
  
  #启动 Docker Compose 中定义的所有容器，并在前台运行，以便查看容器的输出日志。-d
  sudo docker-compose up
```

#### 关于yml文件MySQL数据库密码配置：

```
在 MySQL 容器 myproject_docker_db_1 中，环境变量中不可同时配置了 MYSQL_USER 和 MYSQL_PASSWORD，而 MYSQL_USER 和 MYSQL_PASSWORD 是用来配置一个普通用户的，不能被用来配置 root 用户。
另外

在这里面yml,注释是无效的，依然会覆盖
  db:
    image: mysql
#    env_file:  
#      - ./myproject/.env # 使用了环境变量文件
    networks:  
      - db_network
    volumes:
      - db_vol:/var/lib/mysql:rw # 挂载数据库数据, 可读可写
      - ./compose/mysql/conf/my.cnf:/etc/mysql/my.cnf # 挂载配置文件
      - ./compose/mysql/init:/docker-entrypoint-initdb.d/ # 挂载数据初始化sql脚本
    environment:
      MYSQL_ROOT_PASSWORD: "@hncj.edu.cn.2020:!"
      MYSQL_DATABASE: myproject
    ports:
      - "3306:3306" # 与配置文件保持一致
    restart: always
```

#### 复用

使用 `docker save` 命令来将所有的镜像打包成一个文件

```
sudo docker save -o myproject_docker_images.tar myproject_docker_nginx myproject_docker_web python nginx redis mysql
```

这将把所有的镜像保存在名为 `myproject_docker_images.tar` 的文件中。你可以在其他机器上使用 `docker load` 命令将这个文件中的镜像导入到 Docker 中：

```
sudo docker load -i myproject_docker_images.tar
```

注意，在导入这些镜像时，你需要先启动一个 Docker 服务。