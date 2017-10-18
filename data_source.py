from peewee import *
import os.path

db = SqliteDatabase('javlibrary.db')


class Choice(Model):
    zip_id = CharField(unique=True)
    name = CharField(null=True)
    name_CN = CharField(null=True)
    star = CharField(null=True)
    category = CharField(null=True)
    score = FloatField(null=True)
    image = TextField(null=True)
    torrent = TextField(null=True)
    remark = CharField(null=True)

    class Meta:
        database = db


if __name__ == '__main__':
    db.connect()
    db.create_tables([Choice])
    db.close()
    if os.path.exists('image') is False:
        os.mkdir('image')
