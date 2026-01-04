/**
 * Slash command parser and handler for RRC client
 * Implements all commands available in rrcd
 */

import { sendWS } from './websocket.js';
import { get } from 'svelte/store';
import { currentRoom } from './stores.js';

/**
 * Parse and execute a slash command
 * @param {string} input - The full input string starting with /
 * @returns {boolean} - true if command was handled, false if it should be sent as a regular message
 */
export function handleCommand(input) {
    if (!input.startsWith('/')) {
        return false;
    }

    const parts = input.slice(1).trim().split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1);

    switch (command) {
        // Server operator commands
        case 'stats':
            return cmdStats();
        
        case 'reload':
            return cmdReload();
        
        case 'who':
            return cmdWho(args);
        
        case 'kline':
            return cmdKline(args);
        
        // Room moderation commands
        case 'kick':
            return cmdKick(args);
        
        case 'register':
            return cmdRegister(args);
        
        case 'unregister':
            return cmdUnregister(args);
        
        case 'topic':
            return cmdTopic(args);
        
        case 'mode':
            return cmdMode(args);
        
        case 'op':
            return cmdOp(args);
        
        case 'deop':
            return cmdDeop(args);
        
        case 'voice':
            return cmdVoice(args);
        
        case 'devoice':
            return cmdDevoice(args);
        
        case 'ban':
            return cmdBan(args);
        
        case 'invite':
            return cmdInvite(args);
        
        // Built-in client commands (not sent to server)
        case 'join':
            return cmdJoin(args);
        
        case 'part':
        case 'leave':
            return cmdPart(args);
        
        case 'nick':
            return cmdNick(args);
        
        case 'msg':
        case 'query':
            return cmdMsg(args);
        
        case 'help':
            return cmdHelp(args);
        
        default:
            // Unknown command, send to server as-is (might be server-side command)
            return cmdSendToServer(input);
    }
}

// Server operator commands

function cmdStats() {
    sendWS({
        type: 'send_command',
        command: '/stats',
        room: get(currentRoom)
    });
    return true;
}

function cmdReload() {
    sendWS({
        type: 'send_command',
        command: '/reload',
        room: get(currentRoom)
    });
    return true;
}

function cmdWho(args) {
    const room = args.length > 0 ? args[0] : get(currentRoom);
    sendWS({
        type: 'send_command',
        command: `/who ${room}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdKline(args) {
    if (args.length < 1) {
        addLocalError('Usage: /kline <add|del|list> [target]');
        return true;
    }

    const subcommand = args[0];
    const target = args.slice(1).join(' ');

    if (subcommand === 'list') {
        sendWS({
            type: 'send_command',
            command: '/kline list',
            room: get(currentRoom)
        });
    } else if (subcommand === 'add' && target) {
        sendWS({
            type: 'send_command',
            command: `/kline add ${target}`,
            room: get(currentRoom)
        });
    } else if (subcommand === 'del' && target) {
        sendWS({
            type: 'send_command',
            command: `/kline del ${target}`,
            room: get(currentRoom)
        });
    } else {
        addLocalError('Usage: /kline <add|del|list> [target]');
    }
    return true;
}

// Room moderation commands

function cmdKick(args) {
    if (args.length < 2) {
        addLocalError('Usage: /kick <room> <nick|hashprefix>');
        return true;
    }

    const room = args[0];
    const target = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/kick ${room} ${target}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdRegister(args) {
    const room = args.length > 0 ? args[0] : get(currentRoom);
    sendWS({
        type: 'send_command',
        command: `/register ${room}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdUnregister(args) {
    const room = args.length > 0 ? args[0] : get(currentRoom);
    sendWS({
        type: 'send_command',
        command: `/unregister ${room}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdTopic(args) {
    if (args.length === 0) {
        addLocalError('Usage: /topic <room> [topic]');
        return true;
    }

    const room = args[0];
    const topic = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/topic ${room}${topic ? ' ' + topic : ''}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdMode(args) {
    if (args.length < 2) {
        addLocalError('Usage: /mode <room> <mode> [args]');
        return true;
    }

    const room = args[0];
    const mode = args[1];
    const modeArgs = args.slice(2).join(' ');

    sendWS({
        type: 'send_command',
        command: `/mode ${room} ${mode}${modeArgs ? ' ' + modeArgs : ''}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdOp(args) {
    if (args.length < 2) {
        addLocalError('Usage: /op <room> <nick|hashprefix|hash>');
        return true;
    }

    const room = args[0];
    const target = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/op ${room} ${target}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdDeop(args) {
    if (args.length < 2) {
        addLocalError('Usage: /deop <room> <nick|hashprefix|hash>');
        return true;
    }

    const room = args[0];
    const target = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/deop ${room} ${target}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdVoice(args) {
    if (args.length < 2) {
        addLocalError('Usage: /voice <room> <nick|hashprefix|hash>');
        return true;
    }

    const room = args[0];
    const target = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/voice ${room} ${target}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdDevoice(args) {
    if (args.length < 2) {
        addLocalError('Usage: /devoice <room> <nick|hashprefix|hash>');
        return true;
    }

    const room = args[0];
    const target = args.slice(1).join(' ');

    sendWS({
        type: 'send_command',
        command: `/devoice ${room} ${target}`,
        room: get(currentRoom)
    });
    return true;
}

function cmdBan(args) {
    if (args.length < 2) {
        addLocalError('Usage: /ban <room> <add|del|list> [target]');
        return true;
    }

    const room = args[0];
    const subcommand = args[1];
    const target = args.slice(2).join(' ');

    if (subcommand === 'list') {
        sendWS({
            type: 'send_command',
            command: `/ban ${room} list`,
            room: get(currentRoom)
        });
    } else if ((subcommand === 'add' || subcommand === 'del') && target) {
        sendWS({
            type: 'send_command',
            command: `/ban ${room} ${subcommand} ${target}`,
            room: get(currentRoom)
        });
    } else {
        addLocalError('Usage: /ban <room> <add|del|list> [target]');
    }
    return true;
}

function cmdInvite(args) {
    if (args.length < 2) {
        addLocalError('Usage: /invite <room> <add|del|list> [target]');
        return true;
    }

    const room = args[0];
    const subcommand = args[1];
    const target = args.slice(2).join(' ');

    if (subcommand === 'list') {
        sendWS({
            type: 'send_command',
            command: `/invite ${room} list`,
            room: get(currentRoom)
        });
    } else if ((subcommand === 'add' || subcommand === 'del') && target) {
        sendWS({
            type: 'send_command',
            command: `/invite ${room} ${subcommand} ${target}`,
            room: get(currentRoom)
        });
    } else {
        addLocalError('Usage: /invite <room> <add|del|list> [target]');
    }
    return true;
}

// Client-side commands (handled locally)

function cmdJoin(args) {
    if (args.length === 0) {
        addLocalError('Usage: /join <room>');
        return true;
    }

    const room = args[0];
    sendWS({
        type: 'join_room',
        room: room
    });
    return true;
}

function cmdPart(args) {
    const room = args.length > 0 ? args[0] : get(currentRoom);
    
    if (room === '[Hub]') {
        addLocalError('Cannot part from [Hub]');
        return true;
    }

    sendWS({
        type: 'part_room',
        room: room
    });
    return true;
}

function cmdNick(args) {
    if (args.length === 0) {
        addLocalError('Usage: /nick <nickname>');
        return true;
    }

    const nick = args.join(' ');
    sendWS({
        type: 'set_nickname',
        nickname: nick
    });
    return true;
}

function cmdMsg(args) {
    if (args.length < 2) {
        addLocalError('Usage: /msg <room> <message>');
        return true;
    }

    const room = args[0];
    const message = args.slice(1).join(' ');

    sendWS({
        type: 'send_message',
        text: message,
        room: room
    });
    return true;
}

function cmdHelp(args) {
    const helpText = `
Available commands (rrcd v0.1+):

Room Moderation Commands:
  /kick <room> <nick>           - Remove user from room
  /register <room>              - Persist room settings
  /unregister <room>            - Remove room settings
  /topic <room> [topic]         - Show or set room topic
  /mode <room> <flags>          - Set room modes (+m, +i, +k, +t, +n, +r)
  /op <room> <nick>             - Grant operator status
  /deop <room> <nick>           - Revoke operator status
  /voice <room> <nick>          - Grant voice (in moderated rooms)
  /devoice <room> <nick>        - Revoke voice
  /ban <room> add <nick>        - Ban user from room
  /ban <room> del <nick>        - Remove room ban
  /ban <room> list              - List room bans
  /invite <room> add <nick>     - Invite user to room
  /invite <room> del <nick>     - Remove room invite
  /invite <room> list           - List room invites

Client Commands:
  /join <room>                  - Join a room
  /part [room]                  - Leave a room (current room if not specified)
  /nick <nickname>              - Change your nickname
  /msg <room> <message>         - Send message to specific room
  /help                         - Show this help message

Room Modes:
  +m  Moderated (only voiced/ops can speak)
  +i  Invite-only
  +k  Key/password required
  +t  Topic ops-only
  +n  No outside messages
  +r  Registered
    `.trim();

    addLocalNotice(helpText);
    return true;
}

function cmdSendToServer(command) {
    // Send unknown commands to server (might be server-side commands we don't know about)
    sendWS({
        type: 'send_command',
        command: command,
        room: get(currentRoom)
    });
    return true;
}

// Helper functions

function addLocalError(message) {
    // Import rooms store dynamically to avoid circular dependencies
    import('./stores.js').then(({ rooms, currentRoom }) => {
        const room = get(currentRoom);
        rooms.update(r => {
            const roomData = r.get(room);
            if (roomData) {
                roomData.messages.push({
                    type: 'error',
                    text: message,
                    timestamp: new Date().toLocaleTimeString()
                });
            }
            return new Map(r);
        });
    });
}

function addLocalNotice(message) {
    // Import rooms store dynamically to avoid circular dependencies
    import('./stores.js').then(({ rooms, currentRoom }) => {
        const room = get(currentRoom);
        rooms.update(r => {
            const roomData = r.get(room);
            if (roomData) {
                roomData.messages.push({
                    type: 'notice',
                    text: message,
                    timestamp: new Date().toLocaleTimeString()
                });
            }
            return new Map(r);
        });
    });
}
