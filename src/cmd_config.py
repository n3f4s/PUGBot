# -*- coding: utf-8 -*-

import logging
from commands import Command
from typing import List, Dict, Union, Optional
from guildconf import LobbyVC
import helper
from bot import MyClient
from dataclasses import dataclass

import discord

# TODO: Add "all categories" option <- test
# TODO: handle unreact
# TODO: being able to remove lobbies
# TODO: notify lobby on update config
# TODO: better printing
# TODO: check permissions when joining guild

@dataclass
class CategoryEntry:
    cat: Union[str, discord.CategoryChannel]
    voice_chan: Dict[str, discord.VoiceChannel]


class CfgReactionHandler:

    def __init__(self, client: MyClient, name: str, buttons: Dict[str, CategoryEntry]):
        self.buttons = buttons
        self.vcs: List[discord.VoiceChannel] = []
        self.name = name
        self.logger = helper.default_logger("CfgReactionHandler-{}".format(name), logging.DEBUG)
        self.config = client.config
        self.logger.info("Creating reaction handler")
        self.logger.debug("Buttons: %s",
                          ", ".join(["{} -> {}".format(k, v)
                                     for k, v in buttons.items()]))
        self.entry: Optional[CategoryEntry] = None


    def _format_update_msg(self) -> str:
        assert(self.entry)
        items = ""
        for emoji, vc in self.entry.voice_chan.items():
            if len(self.vcs) >= 1 and self.vcs[0] == vc:
                items += "{} Lobby: <#{}>\n".format(emoji, vc.id)
            elif len(self.vcs) >= 2 and self.vcs[1] == vc:
                items += "{} Team 1: <#{}>\n".format(emoji, vc.id)
            elif len(self.vcs) >= 3 and self.vcs[2] == vc:
                items += "{} Team 2: <#{}>\n".format(emoji, vc.id)
            else:
                items += "{} <#{}>\n".format(emoji, vc.id)
        return """Select the voice channels for PUG lobby {} in the following order: lobby then team1 then team2
{}""".format(self.name, items)

    async def _select_vc(self, emoji: str,
                   reaction: discord.Reaction,
                   user: Union[discord.Member, discord.User]):
        assert(self.entry)
        if emoji not in self.entry.voice_chan:
            return False
        self.vcs.append(self.entry.voice_chan[emoji])
        self.logger.debug("%d channel registered", len(self.vcs))
        await reaction.message.edit(content=self._format_update_msg())
        if len(self.vcs) >= 3 and reaction.message.guild:
            (self.config[reaction.message.guild.id]
             .lobbies
             .update({self.name: LobbyVC(self.name,
                                          self.vcs[0].id,
                                          self.vcs[1].id,
                                          self.vcs[2].id)}))
            helper.save_config(self.config)
            self.logger.debug("Updating configuration")
            return True
        return False

    def _format_msg(self):
        assert(self.entry)
        items = "\n".join(["{}: <#{}>".format(r, c.id) for r, c in self.entry.voice_chan.items()])
        return """Select the voice channels for PUG lobby {} in the following order: lobby then team1 then team2
{}""".format(self.name, items)

    async def _select_cat(self, emoji: str,
                   reaction: discord.Reaction,
                   user: Union[discord.Member, discord.User]):
        if emoji not in self.buttons:
            return False
        self.logger.debug("Selecting categories")
        self.entry = self.buttons[emoji]
        self.logger.debug("Clearing reactions")
        await reaction.message.clear_reactions()
        self.logger.debug("Editing content")
        await reaction.message.edit(content=self._format_msg())
        self.logger.debug("Adding new reactions")
        for r in self.entry.voice_chan:
            await reaction.message.add_reaction(r)
        return False


    async def __call__(self,
                 reaction: discord.Reaction,
                 user: Union[discord.Member, discord.User]):
        emoji = reaction.emoji
        if not isinstance(emoji, str):
            return False
        self.logger.info("User %s reacted with emoji %s", user.name, emoji)
        if not self.entry:
            return await self._select_cat(emoji, reaction, user)
        else:
            return await self._select_vc(emoji, reaction, user)


class CmdConfigPrint(Command):
    @staticmethod
    def name() -> str:
        return "configbotprint"
    def _format_lobby(self, lobby: LobbyVC) -> str:
        return """- {}:
        __Lobby__: <#{}>
        __Team 1__: <#{}>
        __Team 2__: <#{}>
        """.format(lobby.name, lobby.lobby, lobby.team1, lobby.team2)

    def _format_lobbies(self, lobbies: List[LobbyVC]):
        return "\n".join([self._format_lobby(l) for l in lobbies])

    async def execute(self, message: discord.Message, args: List[str]):
        guild = message.guild
        chan = message.channel
        if not guild:
            return
        if guild.id not in self.client().config:
            return
        if not chan and not isinstance(chan, discord.TextChannel):
            return
        guild_name = guild.name
        res_str = """{}:
**Command prefix:** {}
**PUG lobbies**:
{}
        """.format(guild_name, self.client().config[guild.id].prefix,
                   self._format_lobbies(self.client().config[guild.id].lobbies.values()))
        await chan.send(res_str)

        
class CmdConfigBot(Command):

    logger = helper.default_logger("configbot", logging.DEBUG)

    @staticmethod
    def name() -> str:
        return "configbot"

    reactions = ["🇦", "🇧", "🇨", "🇩", "🇪",
                 "🇫", "🇬", "🇭", "🇮", "🇯",
                 "🇱", "🇲", "🇳", "🇴", "🇵",
                 "🇶", "🇷", "🇸", "🇹", "🇺",
                 "🇻", "🇼", "🇽", "🇾", "🇿"]

    all_category_reaction = "🔠"

    def _list_vc(self, cat: discord.CategoryChannel) -> Dict[str, discord.VoiceChannel]:
        return dict(zip(self.reactions, [vc for vc in cat.voice_channels]))

    def _list_cat(self, guild: discord.Guild) -> Dict[str, CategoryEntry]:
        return dict(zip(self.reactions,
                        [CategoryEntry(cat, self._list_vc(cat))
                         for cat in guild.categories if cat.voice_channels]))

    async def execute(self, message: discord.Message, args: List[str]):
        self.logger.info("Executing command")
        guild = message.guild
        if len(args) < 1:
            await message.channel.send('Not enough arguments')
            return
        if not guild:
            return
        res = ""
        reactions = self._list_cat(guild)
        all_cat = {}
        for entry in reactions.values():
            for name, vc in entry.voice_chan.items():
                all_cat[name] = vc
        reactions[self.all_category_reaction] = CategoryEntry("All Categories", all_cat)
        for emoji, cat in reactions.items():
            if isinstance(cat.cat, str):
                res += "{} {}\n".format(emoji, cat.cat)
            elif isinstance(cat.cat, discord.CategoryChannel):
                res += "{} <#{}>\n".format(emoji, cat.cat.id)
        chan = message.channel
        message = await chan.send("voice channels:\n{}".format(res))
        for r in reactions:
            await message.add_reaction(r)
        self.client().reaction_callbacks[message.id] = CfgReactionHandler(self.client(), args[0], reactions)
