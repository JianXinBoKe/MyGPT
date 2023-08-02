from django.db import models

# Create your models here.
class UsersMessages(models.Model):
    userid = models.CharField(max_length=50,verbose_name='用户id')
    username = models.CharField(max_length=50,verbose_name='用户名字')
    question_text = models.CharField(max_length=600,verbose_name='问题')
    q_timestamp = models.DateTimeField(verbose_name='问题时间')
    result_text = models.TextField(verbose_name='回答')
    r_timestamp = models.DateTimeField(verbose_name='相应时间')

    VALID_CHOICES = (
        (0, '无效'),
        (1, '有效'),
    )
    valid = models.IntegerField(choices=VALID_CHOICES, default=1, verbose_name='有效性')
