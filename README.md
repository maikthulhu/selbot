<h1>SELBOT</h1>
<h3> A small personal-use IRC Bot written in Python 2.7</h3>
<hr/>
Currently available features:

<h4> Commands </h4>

| Command | Use |
|:-------:|:---:|
| !last | Displays the source of the most recent quote |
| !quote [source] | If provided a source, it will display a random quote from that source, otherwise it picks a random source. |
| !faq source | Displays the FAQ associated with the given search term (source) |
| !relevant search_term | Displays the relevant XKCD comic based on the search term |
| !stats | Displays the bot's current uptime, quotes remaining, and time alive |
| !ballot | Displays a current ballot for "Final 10" Quote-Vote (See below) |

<h4>"Final 10" Quote-Vote</h4>

When selbot reaches the final 10 votes, he will initiate a lottery.  He will display a numbered list of all available quote sources,
and then he will wait for people to vote.
Example vote:

```
selbot:  24
```

This will initiate the sender's vote for the 24th quote source.  Once someone has picked a source, nobody else may pick the same one.
Selbot will announce if a quote has been taken.  Users may use the !ballot command to see a current list of all votes placed.

After the final quote is shown, selbot will announce if there was a winner or not.

<b>NOTE:</b>  Selbot disables !quote during the Final 10, to avoid skipping ahead before people can cast votes.

<h3> Adding New Commands </h3>
The commands implement a Factory Pattern (Gang of Four Design Patterns).  This makes it fairly simple to implement a new command.
Simply create a new class for the command, and have the new class inherit from Command.  Implement the required functions - resolve() should contain
the logic for running the command, and respond() should contain any output logic if there should be a response to the command.  After that, just add 2 lines
to CommandFactory.py to support the new command!