def elapsed_time(start_hour, start_minute, end_hour, end_minute):
    hour_left = 0
    min_left = 60 - start_minute
    end_hour -= 1
    min_left += end_minute
    if min_left >= 60:
        hour_left += 1
        min_left = min_left - 60
    hour_left = hour_left + (end_hour - start_hour)
    if hour_left < 0:
        hour_left += 24
    return hour_left, min_left

def calculateRemainingTime(prayerHour, prayerMin, hour, minute, fajr):
    localMinLeft = 0
    localHourLeft = 0
    localHours = prayerHour

    if fajr:  # If we're calculating Fajr do this (This is because calculating Fajr is a bit more involved than other prayers)
        if hour == 0:
            localMinLeft = 60 - minute
            localHours -= 1
            localMinLeft += int(prayerMin)
        if localMinLeft >= 60:
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
            localHourLeft += int(prayerHour)

        elif 0 < hour < 5:
            localMinLeft = 60 - minute
            localHourLeft -= 1
            localMinLeft += int(prayerMin)

        if localMinLeft >= 60:
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
            localHourLeft = localHourLeft + (int(prayerHour) - hour())

        else:
            localMinLeft = 60 - minute
            localHourLeft -= 1
            localMinLeft += int(prayerMin)

        if localMinLeft >= 60:
            localHourLeft += 1
            localMinLeft = localMinLeft - 60

        localHourLeft += 24 - hour

        localHourLeft += int(prayerHour)
        if localMinLeft >= 60:
            localHourLeft += 1
            localMinLeft = localMinLeft - 60
        return localHourLeft, localMinLeft
    # If we're not calculating Fajr, we can calculate normally 
    localMinLeft = 60 - minute
    localHours -= 1
    localMinLeft += prayerMin
    if localMinLeft >= 60:
        localHourLeft += 1
        localMinLeft = localMinLeft - 60
    localHourLeft = localHourLeft + (localHours - hour)
    if localHourLeft < 0:
        localHourLeft += 24
    return localHourLeft, localMinLeft

import random 

for i in range(100):
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    nextHour = random.randint(0, 23)
    nextMinute = random.randint(0, 59)
    if elapsed_time(hour, minute, nextHour, nextMinute) != calculateRemainingTime(nextHour, nextMinute, hour, minute, False):
        print("Error, {}:{} to {}:{} should be {}:{} but is {}:{} instead".format(hour, minute, nextHour, nextMinute, *elapsed_time(hour, minute, nextHour, nextMinute), *calculateRemainingTime(nextHour, nextMinute, hour, minute, False)))
        exit()
print("All tests passed")