# tMuslim-Discord-Bot
Discord bot for Server-wide athaans, duaas, Quran, and more! 

tMuslim was a project I took on last Ramadan, however eventually scrapped it due to lack of time. This year, I plan on reviving it and getting it ready for next Ramadan

## Planned Features
* Serverwide Athaans
  * Fill your VCs with the sacred sound of the Islamic Call to Prayer. I plan on giving tMuslim the ability to join VCs for prayer times, and play the Athaan in the VC
* Duaas, Hadiths, and Quran
  * Using a curated set of authentic duaas and hadiths, I plan on making a system where you can request random duaas, hadiths, Quran chapters, etc. and a system where you can select specific Quraan verses/Chapters
* Prayer Times
  * Unlike my previous attempt at a Muslim app - TMMuslim/tMuslim, I plan on making this bot actually work for regions other than the one I currently reside in. That's why I have a fairly rudimentary system setup for servers. I plan on beefind this system up and making it more robust

## Current Features - Even if they're still half-baked

* Prayer Times
  * Prayer times are currently half-functioning. You can request the next prayer, but not much else. I plan on adding more commands (prayerList, prayerTime, etc.) and making the system more robust
  * I might untie the prayer times from the server, and tie it to each user. This might not be the best idea, but I'm not sure yet. I'll have to think about it

## Planned Commands
First and foremost, I must rewrite the bot to function with slash commands, as the current implementation uses the outdated prefix system. I plan on adding the following commands:
* Prayer Times
  * prayerList - Lists all the prayer times for the day
  * nextPrayer - Lists the next prayer
  * prayerTime - Lists the time of a specific prayer
* Duaas/Hadiths/Quran
  * randomDuaa - Gives a random duaa
  * randomHadith - Gives a random hadith
  * randomQuran - Gives a random Quran verse
  * randomQuranChapter - Plays a random Quran chapter if you are in a VC 
  * playQuran - Plays the entire Quran in order, saves the progress of the user, and resumes from where they left off
  * playQuranChapter - Plays a specific Quran chapter if you are in a VC 
    * I need to build an interpreter for the different formats of Quran chapters (Ex: Name, number, etc.) 

* Ramadan Special 
  * ramadanCountdown - Gives the number of days left until Ramadan
  * timeUntilFajr - Gives the time until the next Fajr prayer
  * timeUntilIftaar - Gives the time until Iftaar
  * daysLeft - Gives the number of days left in Ramadan

* Misc
  * help - Lists all the commands
  * invite - Gives the invite link for the bot
  * about - Gives information about the bot
  * setup - Sets up the server for prayer times by obtaining the region and timezone of the server
  * setMode - Sets the mode of bot setup (Ex: Tied to user vs tied to server)
