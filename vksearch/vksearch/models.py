from django.db import models


class CommunityType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'community_type'


class CommunityManager(models.Manager):

    ORDERING_CHOICES = (
        ('members', 'Members'),
        ('audience_sum', 'Audience'),
        ('audience_perc', 'Audience (%)')
    )

    def select(self, ordering, inverted,
               min_members=None, max_members=None, min_audience=None, max_audience=None,
               min_audience_perc=None, max_audience_perc=None, sex_ids=None, age_ranges=None,
               countries=None, apps=None):
        if inverted:
            ordering = '-' + ordering

        members_filter = {}
        if min_members is not None:
            members_filter['members__gte'] = min_members
        if max_members is not None:
            members_filter['members__lte'] = max_members

        audience_filter = {}
        if min_audience is not None:
            audience_filter['audience__gte'] = min_audience
        if max_audience is not None:
            audience_filter['audience__lte'] = max_audience
        if min_audience_perc is not None:
            audience_filter['audience_perc__gte'] = min_audience_perc
        if max_audience_perc is not None:
            audience_filter['audience_perc__lte'] = max_audience_perc

        profile_filter = {}
        if sex_ids:
            profile_filter['audience__profile__sex_vkid__in'] = sex_ids
        if age_ranges:
            profile_filter['audience__profile__age_range__in'] = age_ranges
        if countries:
            profile_filter['audience__profile__country__in'] = countries
        if apps:
            profile_filter['audience__profile__app__in'] = apps

        return self.filter(
            deactivated=False,
            **members_filter,
            **profile_filter
        ).select_related(
            'type'
        ).annotate(
            audience_sum=models.Sum('audience__count'),
            audience_perc=100 * models.F('audience_sum') / models.F('members')
        ).filter(
            audience_sum__isnull=False,
            **audience_filter
        ).order_by(
            ordering
        )


class Community(models.Model):
    vkid = models.IntegerField(primary_key=True)
    deactivated = models.BooleanField()
    type = models.ForeignKey(CommunityType, db_column='type')
    name = models.TextField()
    description = models.TextField()
    members = models.IntegerField(blank=True, null=True)
    status = models.TextField()
    verified = models.NullBooleanField()
    site = models.TextField()
    age_limit = models.SmallIntegerField(blank=True, null=True)
    updated = models.DateTimeField()
    audience_updated = models.DateTimeField()

    objects = CommunityManager()

    def __str__(self):
        return '%s: %s' % (self.vkid, self.name)

    class Meta:
        managed = False
        db_table = 'community'


class AgeRange(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'age_range'


class Country(models.Model):
    vkid = models.SmallIntegerField(primary_key=True)
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'country'


class Application(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'application'


class Profile(models.Model):
    SEX_UNKNOWN = 0
    SEX_FEMALE = 1
    SEX_MALE = 2
    SEX_CHOICES = (
        (SEX_UNKNOWN, 'UNKNOWN'),
        (SEX_FEMALE, 'Female'),
        (SEX_MALE, 'Male')
    )
    id = models.IntegerField(primary_key=True)
    sex_vkid = models.SmallIntegerField(choices=SEX_CHOICES)
    age_range = models.ForeignKey(AgeRange, db_column='age_range_id')
    country = models.ForeignKey(Country, db_column='country_vkid')
    app = models.ForeignKey(Application, db_column='app_id')

    class Meta:
        managed = False
        db_table = 'profile'


class Audience(models.Model):
    community = models.ForeignKey(Community, db_column='community_vkid')
    profile = models.ForeignKey(Profile, db_column='profile_id')
    count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'audience'
