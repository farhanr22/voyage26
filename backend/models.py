import peewee as pw


# Proxy object for initializing the database later
db_proxy = pw.DatabaseProxy()


class BaseModel(pw.Model):
    class Meta:
        database = db_proxy


class Reg_Data(BaseModel):
    SubID = pw.CharField(unique=True)
    SubAt = pw.CharField()
    Name = pw.CharField()
    Phone = pw.CharField()
    Stream = pw.CharField()
    FoodPref = pw.CharField()
    TShirtInt = pw.BooleanField()
    TShirtSize = pw.CharField(null=True)
    PaymentMethod = pw.CharField()
    PaymentScreenshot = pw.TextField(null=True)

    # Admin info
    Status = pw.CharField(default="Pending")  # or Verified or Rejected
    Payable = pw.IntegerField()  # fixed ased on tshirtinterest

    # Below are NULL before verification
    StudentID = pw.CharField(null=True)  # Set to random unique value
    Paid = pw.IntegerField(null=True)  # Set to amount from CR payment or online
    VerifiedBy = pw.CharField(null=True)  # Admin name at approval
    NotificationStatus = pw.CharField(null=True)  # False at approval


class CR_Payments(BaseModel):
    SubID = pw.CharField(unique=True)
    SubAt = pw.CharField()
    CRID = pw.CharField()
    Name = pw.CharField()
    Phone = pw.CharField()
    Amount = pw.IntegerField()
    Status = pw.CharField(default="Pending")  # or matched
    MatchedBy = pw.CharField(null=True)


class CR_Profiles(BaseModel):
    CRID = pw.CharField(unique=True)
    Name = pw.CharField()
    Phone = pw.CharField()
    Batch = pw.CharField()


class Admins(BaseModel):
    username = pw.CharField(unique=True)
    passhash = pw.CharField()


class Booth_Operators(BaseModel):
    Username = pw.CharField(unique=True)
    Name = pw.CharField()
    Phone = pw.CharField()
    AddedBy = pw.CharField()  # name of admin
    RemovedBy = pw.CharField(null=True)


class ItemsTaken(BaseModel):
    StudentID = pw.CharField()  ## actually studentID
    GivenBy = pw.CharField()
    Item = pw.CharField()
    TakenAt = pw.CharField()

class UpdateMetadata(BaseModel):
    LastModified = pw.DateTimeField(null=True)
    LastUpdated = pw.DateTimeField(null=True)