"""First-run launcher with splash, main menu, settings and loading screen."""
from __future__ import annotations
import json, sys, time, os, traceback
from pathlib import Path
import pygame
import config

BASE=Path(__file__).resolve().parent
if getattr(sys,"frozen",False):
    SETTINGS_PATH=Path(os.environ.get("APPDATA",Path.home()/"AppData"/"Roaming"))/"SpaceEmpire"/"settings.json"
else:
    SETTINGS_PATH=BASE/"saves"/"settings.json"
RESOLUTIONS=[(1280,720),(1366,768),(1600,900),(1920,1080)]


def has_continue_save():
    """True only if a valid campaign save or backup is available."""
    try:
        from save_system import SaveManager
        return SaveManager().load() is not None
    except Exception:
        return False

def read_settings():
    defaults={"resolution":[1600,900],"fullscreen":False,"music":True,"sound":True,"volume":0.35}
    try:
        data=json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data,dict): defaults.update(data)
    except (OSError,ValueError): pass
    if tuple(defaults["resolution"]) not in RESOLUTIONS: defaults["resolution"]=[1600,900]
    return defaults

def write_settings(settings):
    SETTINGS_PATH.parent.mkdir(parents=True,exist_ok=True)
    tmp=SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(SETTINGS_PATH)

def draw_text(screen,text,pos,size=22,color=(218,234,247),bold=False):
    font=pygame.font.SysFont("segoeui",size,bold=bold)
    screen.blit(font.render(text,True,color),pos)

def button(screen,rect,label,hover=False):
    pygame.draw.rect(screen,(17,57,82) if hover else (10,27,47),rect,border_radius=7)
    pygame.draw.rect(screen,(72,190,228) if hover else (39,91,122),rect,2,border_radius=7)
    f=pygame.font.SysFont("segoeui",19,True); t=f.render(label,True,(225,243,252))
    screen.blit(t,t.get_rect(center=rect.center))

def run_launcher():
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    settings=read_settings()
    flags=pygame.RESIZABLE | (pygame.FULLSCREEN if settings["fullscreen"] else 0)
    screen=pygame.display.set_mode(tuple(settings["resolution"]),flags)
    try:
        pygame.display.set_icon(pygame.image.load(str(BASE/"assets"/"icons"/"space_empire.png")))
    except (pygame.error,OSError):
        pass
    clock=pygame.time.Clock()
    try:
        from audio import AudioManager
        audio=AudioManager()
        audio.set_volume(settings["volume"]); audio.set_music(settings["music"])
        audio.enabled=bool(settings["sound"])
    except Exception:
        audio=None
    state="splash"; started=time.monotonic(); selected=None
    buttons={}
    startup_error=""
    continue_available=has_continue_save()
    running=True
    while running:
        w,h=screen.get_size(); mouse=pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False
            elif event.type==pygame.VIDEORESIZE and not settings["fullscreen"]:
                screen=pygame.display.set_mode((max(960,event.w),max(600,event.h)),pygame.RESIZABLE)
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    if state=="settings": state="menu"
                    elif state=="confirm_new": state="menu"
                    elif state=="menu": running=False
                elif state=="splash": state="menu"
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if audio: audio.play_click()
                if state=="splash": state="menu"
                elif state=="menu":
                    if buttons.get("continue",pygame.Rect(0,0,0,0)).collidepoint(event.pos): selected="continue"; state="loading"
                    elif buttons.get("developer",pygame.Rect(0,0,0,0)).collidepoint(event.pos): selected="developer"; state="loading"
                    elif buttons.get("new",pygame.Rect(0,0,0,0)).collidepoint(event.pos): state="confirm_new"
                    elif buttons.get("settings",pygame.Rect(0,0,0,0)).collidepoint(event.pos): state="settings"
                    elif buttons.get("quit",pygame.Rect(0,0,0,0)).collidepoint(event.pos): running=False
                elif state=="confirm_new":
                    if buttons.get("confirm_yes",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        selected="new"; state="loading"
                    elif buttons.get("confirm_no",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        state="menu"
                elif state=="settings":
                    if buttons.get("resolution",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        idx=RESOLUTIONS.index(tuple(settings["resolution"])); settings["resolution"]=list(RESOLUTIONS[(idx+1)%len(RESOLUTIONS)])
                        if not settings["fullscreen"]: screen=pygame.display.set_mode(tuple(settings["resolution"]),pygame.RESIZABLE)
                    elif buttons.get("fullscreen",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        settings["fullscreen"]=not settings["fullscreen"]
                        screen=pygame.display.set_mode((0,0) if settings["fullscreen"] else tuple(settings["resolution"]),pygame.FULLSCREEN|pygame.RESIZABLE if settings["fullscreen"] else pygame.RESIZABLE)
                    elif buttons.get("music",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        settings["music"]=not settings["music"]
                        if audio: audio.set_music(settings["music"])
                    elif buttons.get("sound",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        settings["sound"]=not settings["sound"]
                        if audio: audio.enabled=settings["sound"]
                    elif buttons.get("volume",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        settings["volume"]=round(max(0,min(1,(event.pos[0]-buttons["volume"].x)/buttons["volume"].width)),2)
                        if audio: audio.set_volume(settings["volume"])
                    elif buttons.get("back",pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                        write_settings(settings); state="menu"
        screen.fill((4,9,22))
        # Subtle animated starfield, deterministic positions.
        for i in range(95):
            x=(i*197+int(time.monotonic()*((i%3)+1)*7))%max(1,w)
            y=(i*113)%max(1,h)
            c=90+(i*17)%110
            screen.fill((c//2,c,c+20),(x,y,2,2))
        if state=="splash":
            draw_text(screen,"SPACE EMPIRE",(w//2-160,h//2-60),42,(105,220,255),True)
            draw_text(screen,"REBUILD. EXPLORE. DISCOVER.",(w//2-145,h//2+2),17)
            draw_text(screen,"Натисніть будь-де, щоб продовжити",(w//2-150,h-90),14,(119,151,177))
            if time.monotonic()-started>2.2: state="menu"
        elif state=="menu":
            # Re-evaluate the campaign save so Continue never appears on a first run.
            continue_available = has_continue_save()
            draw_text(screen,"SPACE EMPIRE",(w//2-170,95),44,(105,220,255),True)
            draw_text(screen,"Космічна імперія починається з одного рішення",(w//2-205,155),17,(119,151,177))
            labels=[]
            if continue_available:
                labels.append(("continue","Продовжити"))
            labels.extend([("new","Нова гра"),("developer","Developer Mode / Тестування"),
                           ("settings","Налаштування"),("quit","Вихід")])
            buttons={}
            menu_top=max(220,(h-len(labels)*66)//2+35)
            for i,(key,label) in enumerate(labels):
                r=pygame.Rect(w//2-150,menu_top+i*66,300,54); buttons[key]=r; button(screen,r,label,r.collidepoint(mouse))
            draw_text(screen,"v1.0.0  •  Python / Pygame-ce",(w//2-115,h-52),13,(90,125,150))
            if startup_error:
                draw_text(screen,startup_error[:100],(w//2-250,h-78),12,(255,145,125))
        elif state=="confirm_new":
            draw_text(screen,"ПОЧАТИ НОВУ ГРУ?",(w//2-165,h//2-105),30,(255,205,115),True)
            draw_text(screen,"Поточне збереження буде замінене новою кампанією.",(w//2-225,h//2-55),15,(190,205,220))
            draw_text(screen,"Старі файли збереження буде скопійовано до saves/archive.",(w//2-250,h//2-27),14,(119,151,177))
            buttons={}
            yes=pygame.Rect(w//2-170,h//2+35,155,52); no=pygame.Rect(w//2+15,h//2+35,155,52)
            buttons["confirm_yes"]=yes; buttons["confirm_no"]=no
            button(screen,yes,"Почати нову",yes.collidepoint(mouse))
            button(screen,no,"Скасувати",no.collidepoint(mouse))
        elif state=="settings":
            draw_text(screen,"НАЛАШТУВАННЯ",(w//2-145,105),30,(105,220,255),True)
            rows=[
                ("resolution",f"Роздільна здатність: {settings['resolution'][0]} × {settings['resolution'][1]}"),
                ("fullscreen",f"Повноекранний режим: {'УВІМК.' if settings['fullscreen'] else 'ВИМК.'}"),
                ("music",f"Музика: {'УВІМК.' if settings['music'] else 'ВИМК.'}"),
                ("sound",f"Звуки: {'УВІМК.' if settings['sound'] else 'ВИМК.'}"),
                ("volume",f"Гучність: {int(settings['volume']*100)}%"),
            ]
            buttons={}
            for i,(key,label) in enumerate(rows):
                r=pygame.Rect(w//2-210,205+i*66,420,48); buttons[key]=r; button(screen,r,label,r.collidepoint(mouse))
                if key=="volume":
                    fill=pygame.Rect(r.x,r.bottom-5,int(r.width*settings["volume"]),4); pygame.draw.rect(screen,(78,203,240),fill)
            r=pygame.Rect(w//2-100,570,200,48); buttons["back"]=r; button(screen,r,"Зберегти й назад",r.collidepoint(mouse))
        elif state=="loading":
            draw_text(screen,"ІНІЦІАЛІЗАЦІЯ ІМПЕРІЇ",(w//2-190,h//2-70),27,(105,220,255),True)
            pygame.draw.rect(screen,(17,39,58),(w//2-200,h//2,400,12),border_radius=6)
            pygame.draw.rect(screen,(74,196,236),(w//2-200,h//2,400,12),border_radius=6)
            draw_text(screen,"Завантаження систем, флоту та галактичних архівів…",(w//2-230,h//2+32),14,(119,151,177))
            pygame.display.flip()
            try:
                config.WINDOW_WIDTH,config.WINDOW_HEIGHT=tuple(settings["resolution"])
                config.START_FULLSCREEN=bool(settings["fullscreen"])
                from game import Game
                game=Game(load_saved=(selected=="continue"),
                          developer_mode=(selected=="developer"))
                game.audio_manager=audio
                run_result=game.run()
                settings=read_settings()
                continue_available=has_continue_save()
                if run_result == "main_menu":
                    pygame.init()
                    flags=pygame.RESIZABLE | (pygame.FULLSCREEN if settings["fullscreen"] else 0)
                    screen=pygame.display.set_mode(tuple(settings["resolution"]),flags)
                    state="menu"
                    selected=None
                    startup_error=""
                    continue
            except Exception as exc:
                traceback.print_exc()
                startup_error=f"Помилка запуску: {type(exc).__name__}: {exc}"
                print(f"Не вдалося запустити Space Empire: {exc}",file=sys.stderr)
                if not pygame.get_init():
                    pygame.init()
                    screen=pygame.display.set_mode(tuple(settings["resolution"]),pygame.RESIZABLE)
                state="menu"
                continue
            running=False
            break
        pygame.display.flip()
        clock.tick(60)
    write_settings(settings)
    if audio: audio.close()
    pygame.quit()
    return 0

if __name__=="__main__": raise SystemExit(run_launcher())
