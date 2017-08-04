# TerminalView

[![Build Status](https://travis-ci.org/Wramberg/TerminalView.svg?branch=master)](https://travis-ci.org/Wramberg/TerminalView)

A Linux/macOS plugin for Sublime Text 3 that allows for terminals inside editor views. The plugin uses a pseudo-terminal to start the underlying shell which means it supports

* Interactive applications (less, man, ipython, ssh, etc.)
* Auto-completion
* Terminal shortcuts (`ctrl`+`c`, etc.)
* Password prompts
* Basically everything you would expect from a terminal

**Note, if you encounter any issues please check the "Common problems" section at the bottom for a solution.**

![example.gif](https://raw.githubusercontent.com/Wramberg/TerminalView/master/example.gif "TerminalView Demonstration")

## Dependencies
To run this plugin you need

* Linux-based OS
* Sublime Text 3 (build 3092 or newer)
* bash (this is not required but recommended, see "Changing shell" below for details)

## Installation
To install from https://packagecontrol.io/packages/TerminalView

1. Open the command palette (`ctrl`+`shift`+`p` by default) and find "Package Control: Install Package"
2. Search for TerminalView and hit `enter` to install.

To install manually from github run

```
git clone https://github.com/Wramberg/TerminalView.git $HOME/.config/sublime-text-3/Packages/TerminalView
```

## Usage
Simply bring up your command palette (`ctrl`+`shift`+`p` by default) and search for "Terminal View: Open Bash". This opens a terminal using 'bash -l' as shell. By default there is no keybinding for opening a terminal view but you can bind a key in your keymap to the *terminal_view_open* command:

```
{ "keys": ["ctrl+alt+t"], "command": "terminal_view_open" },
```

which does the same. All configuration for TerminalView is available through the command palette by searching for "Terminal View". Alternatively, it can also be accessed through the menu: *Preferences->Package Settings->TerminalView*. The configuration includes

* Keybindings
* Settings
* Palette commands
* Color scheme

These are all discussed further in the remainder of this readme.

## Keybindings
The following keys are forwarded to the shell by default:

* All single characters and numbers
* All signs (create an issue if some are missing)
* Arrow keys
* `home`, `end`, `delete`, `insert`, `pageup`, `pagedown`
* `escape`, `tab`, `space`, `backspace`, `enter`
* Any `ctrl`+`<char>` combination except `ctrl`+`k` (see below if you want this to go to the shell instead of ST3)
* Any `alt`+`<char>` combination
* Any `ctrl`+`<arrow key>` combination

Note that `ctrl`+`<sign>` combinations are not forwarded as they depend on keyboard layout. The keybindings can be configured through the menu or the command palette.

**If some of the keybindings are not working they are probably shadowed by keybindings in your user keymap.** To fix this find the missing keybindings in the default keymap and copy them into your user keymap. For example, if you have bound `alt`+`f` in your user keymap you need to insert the following in your user keymap:

```
{"keys": ["alt+f"], "command": "terminal_view_keypress", "args": {"key": "f", "alt": true}, "context": [{"key": "setting.terminal_view"}]},
```

Similarly, if you want to override some of the default TerminalView keybindings like e.g. `ctrl`+`w` move the following into your user keymap

```
{ "keys": ["ctrl+w"], "command": "close" },
```

Lastly TerminalView also includes a few utility keybindings:

Shortcut | Description
--- | ---
`ctrl` + `shift` + `c` | Copy the selection/line in the terminal into the clipboard
`ctrl` + `shift` + `v` | Paste the contents of the clipboard into the terminal
`alt` + `mouse wheel up` / `mouse wheel down` | Scroll back/forward in terminal history (only works on Linux - see [#28](../../issues/28) for details)
`shift` + `pageup` / `pagedown` | Scroll back/forward in terminal history
`ctrl` + `shift` + `t` / `n` | Open a new file
`ctrl` + `shift` + `w` / `q` | Close the terminal view
`ctrl` + `shift` + `up` / `down` / `left` / `right` | Move the ST3 cursor (not the terminal cursor)
`ctrl` + `shift` + `home` / `end` | Move the ST3 cursor to beginning/end of line
`escape` | If ST3 cursor is located elsewhere than the terminal cursor move it back - otherwise send escape to shell.

Note that standard ST3 keybindings for selection are **not** shadowed which mean you can use `shift` + `keys` for selection in the terminal in case you prefer to use the keyboard. These keybindings do not move the actual terminal cursor however so whenever the terminal is updated the cursor will snap back to its point of origin.

## Settings
The settings are available in the menu or through the command palette. The settings include options for adjusting colors, scrollback history and margins (to avoid scrollbars). Simply copy the settings you want to change into your user settings.

## Changing shell
If you want to use another shell it is highly recommended to do this through bash with the -c command line argument. You can control the shell command through the *cmd* argument to the *terminal_view_open* command. In addition, you can also alter the title of the terminal view to reflect which shell is running.

If you e.g. want to run an IPython shell when hitting `ctrl`+`alt`+`t`, add the following to your keymap file:

```
{ "keys": ["ctrl+alt+t"], "command": "terminal_view_open", "args": {"cmd": "/bin/bash -l -c /usr/bin/ipython", "title": "Terminal (IPython)"}},
```

If you really want to avoid using bash you can also run your shell directly:

```
{ "keys": ["ctrl+alt+t"], "command": "terminal_view_open", "args": {"cmd": "/usr/bin/ipython", "title": "Terminal (IPython)"}},
```

but this is **very experimental**. Some future development regarding this is planned, but at the moment only bash is tested.

When you are done you can close the terminal by closing the view (`ctrl`+`shift`+`q` or `ctrl`+`shift`+`w` as default) or exiting the shell (by e.g. hitting `ctrl`+`d`).

## Palette Commands
Additional palette commands can be added through the menu or the command palette. These are simply included as an alternative to keybindings.

## Color scheme
The color scheme is used for both dynamic coloring (colors set by the shell) and static coloring (colors set by syntax highlighting). The color scheme itself can be tweaked by copying the default color scheme into the user color scheme file. Both of these files are available in the menu or through the command palette.

## Syntax highlighting
The plugin supports user provided syntax highlighting for static coloring. To use this feature create a *\<name\>.sublime-syntax* file in your *Packages/User* folder. The *packages* folder can accessed through the menu: *Preferences->Browse Packages*. The content of the file depends entirely on your needs - see https://www.sublimetext.com/docs/3/syntax.html for details. As an example consider the following which highlights the prompt in bash.

```
%YAML 1.2
---
name: TerminalViewBash
hidden: true
file_extensions:
  - terminal_view
scope: text.terminal_view
contexts:
  main:
    - match: '\w+@[A-z,\-_]+(?=:)'
      scope: terminalview.black_green
    - match: '([A-z,\-_/~0-9.]+\$)'
      scope: terminalview.black_blue
```

The matching could be improved upon but it will do for the purpose of this example. Note that the scope names are chosen so they match with scopes that are already defined in the color scheme. To change the color scheme see the "color scheme" section above. In this example the syntax file was saved as *bash.sublime-syntax* under the *Packages/User* folder. To use it when opening a bash terminal pass it to the *terminal_view_open* command with the *syntax* argument:

```
{ "keys": ["ctrl+alt+t"], "command": "terminal_view_open", "args": {"cmd": "/bin/bash -l", "title": "Bash Terminal", "syntax": "bash.sublime-syntax"}},
```

There are currently no syntax-files provided with the plugin so users must create their own. Note that any colors set by shell (except the black/white default) override colors set by the syntax highlighting.

## Project switching and ST3 startup
When switching projects or (re)starting ST3 the plugin restarts all terminals views. Unfortunately, there is no obvious way of restoring earlier sessions so the views are completely reset.

## Running executables interactively through a Sublime build system

In a Sublime build system, you can use the `terminal_view_exec` command for the
`"target"` key. You can then use the keyboard to give input to whatever
executable that you're running.

For example, consider this `.sublime-project`:

```
{
  "build_systems":
  [
    {
      "name": "My Build",
      "shell_cmd": "c++ program.c -o program",
      "working_dir" "$project_path"
      "variants":
      [
        {
          "name": "Run program",
          "shell_cmd": "./program",
          "working_dir": "$project_path"
        }
      ]
    }
  ],
  "folders":
  [
    {
      "path": "."
    }
  ],
  "settings":
  {
  }
}
```
When you click on *Tools* -> *Build With...* in the menu, you may select the
*My Build - Run program* variant. This will open an output panel and run your
program. Unfortunately, if the program wants input from user, you cannot type
on your keyboard to send that input to the program. To solve this you can change
the variant to:
```
        {
          "name": "Run program",
          "target": "terminal_view_exec",
          "shell_cmd": "./program",
          "working_dir": "$project_path"
        }
```
This will run your program inside a TerminalView instead. You will be able to
supply input with the keyboard.
<sup>Note: the default value for the `"target"` is the `"exec"` command.</sup>

At this point, a custom `"env"` key is not yet supported.

## Common problems
List of common problems you may encounter when using this plugin.

#### A keybinding is not working even though it is listed in the keybindings section
This is most likely because you have the key bound to something else in your user keymap file. To make it work find the missing keybinding in the TerminalView keymap and copy it to your user keymap. For details see the keybindings section above.

#### The terminal is responsive but acts weird (prints weird sequences, cursor located in the wrong place, etc.)
Ensure you do not have a bash_profile file or similar that changes the value of the `TERM` environment variable. This is set to "linux" by the plugin and must stay that way. You can check it by calling `env | grep TERM` inside the terminal view in ST3. If the `TERM` value is correct feel free to open an issue for further investigation.

#### The terminal is sluggish and/or uses a lot of memory
You may have other plugins that conflict with TerminalView. TerminalView does a lot of modifications to the buffer which can conflict with plugins like e.g. GotoLastEditEnhanced. In this particular case a history of all modifications are saved causing unbound memory usage. Please test TerminalView in isolation to see if the issue persists.

## Future development
Development is performed ad-hoc and current plans include:

* Using ST3 scrolling instead of pyte scrolling (requires decent amount of work but would make scrolling and copying better)
* Functionality for dynamic amount of scrolling (right now its a fixed ratio only adjustable through settings)
* Support for "editor" mode where cursor can move freely and standard ST3 keybindings can be used
* 256 color support
* Support for more shells
* QOL shortcut that can find and open filepaths in the terminal window
* Experimentation with Windows support (through WSL)

## Acknowledgments
The pyte terminal emulator (https://github.com/selectel/pyte) is an integral part of this plugin and deserves some credit for making this plugin possible.

During development the SublimePTY plugin (https://github.com/wuub/SublimePTY) was a good source of inspiration for some of the problems that occurred. You can probably find a few bits and pieces from it in this plugin.

For testing stubs and general test structure the Javatar plugin (https://github.com/spywhere/Javatar) was a good point of origin.
