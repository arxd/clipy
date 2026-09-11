import { options } from 'preact';

function waitForStableLayout() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          resolve();
        });
      });
  });
}


class CSSManager {
    constructor() {
        this.styles = {}
        this.ref_counts = {}
    }

    el(css, el, key) {
        const style = document.createElement('style')
        if (key) style.setAttribute('data-id', key)
        style.innerHTML = css
        el = el || document.head
        el.append(style)
    }

    use(...keys) {
        for (const key of keys) {
            const r = this.ref_counts[key]
            if (r === undefined) throw `Style '${key}' has not been registered`
            this.ref_counts[key] = r + 1
            if (r === 0) this.el(this.styles[key], document.head, key)
        }
        return () => keys.forEach((key)=>this.unuse(key))
    }

    unuse(key) {
        if (!this.ref_counts[key]) throw `Too many unuse calls for (${key})`
        waitForStableLayout().then(() => {
            this.ref_counts[key] -= 1
            if (this.ref_counts[key] > 0) return
            console.log(`remove ${key}`)
            $(`style[data-id="${key}"`).remove()
        })
    }

    register(key, css) {
        if (this.styles[key]) throw `conflicting style key '${key}': ${this.styles[key]}`
        this.styles[key] = css
        this.ref_counts[key] = 0
    }
}

export const CSS = new CSSManager()


/// Custom elements must be defined before they can be used
export function EL(el, css, name) {
    name = name || (el.name.startsWith('_')? el.name.slice(1): el.name)
    name = name.replace( /([a-z])([A-Z])/g, '$1-$2' ).toLowerCase()
    customElements.define(name, el)
    if (css) CSS.register(name, css)
}


function _attrs(el, attrs) {
    for (const [key, value] of Object.entries(attrs)) {
        if (key === 'children') for (const arg of value) _parse_arg(el, arg)
        else if (key !== 'tag') el.setAttribute(key, value)
    }
    return el
}


function _parse_arg(el, arg) {
    if (arg === null || arg === undefined) return el
    if (typeof arg === 'string') {
        if (arg[0] === '<') {
            const tmpl = document.createElement('template')
            tmpl.innerHTML = arg
            if (el === null) return tmpl.content.firstElementChild
            arg = tmpl.content.firstElementChild
        } else { // normal string is treated as a tag if it is the first arg, otherwise a tet node
            if (el === null) return document.createElement(arg)
            arg = document.createTextNode(arg)
        }
    } else if (arg?.constructor === Object) {
        if (el === null) return _attrs(document.createElement(arg.tag || 'div'), arg)
        if (arg.tag === undefined) return _attrs(el, arg)
        arg = _attrs(document.createElement(arg.tag), arg)
    } else if (el === null) return arg
    el.appendChild(arg)
    return el
}


/// The first argument creates the element.
///  * createElement() if a string tag-name is given
///  * Parsed html template if the string starts with a `<`
///  * <div> element with attributes if an object is given (without a tag attribute)
///  
/// Subsequent arguments modify the inital element.
///  * Append a textNode if a string is given
///  * Add element attributes if an object (without a tag attribute) is given
///  * Append a child element (posibly from another E() call)
///  * Append a child element from an object containing a tag attribute
/// 
/// E('span')  <span></span>
/// E('span', 'hello', 'world')  <span>helloworld</span>
/// E({tag:'input', class:'bob'}, {type:'text', value:'hi'})  <input class="bob" type="text" value="hi" />
/// E('h1', 'Hello', {tag:'span', class:'bob', children:['World']}, '!')  <h1>Hello<span class="bob">World</span>!</h1>
export function E(...args) {
    return args.reduce((el, arg) => _parse_arg(el, arg), null)
}


/// Use this in place of `target.addEventListener(event, callback, args)`
/// It returns a function that can be called to remove the listener.
/// It also adds a 'throttle' argument
export function LSN(target, event, callback, args={}) {
    let tid = null
    let last_evt = null // the latest event recieved while sleeping 
    let listener = callback
    if (args.throttle !== undefined) {
        let ms = args.throttle
        delete args.throttle
        
        listener = (evt) => {
            if (tid == null) { // We haven't been sleeping.  Send the event and start sleeping.
                last_evt = null
                tid = setTimeout(() => {
                    if (last_evt !== null) callback(last_evt)
                    tid = null // Done sleeping
                }, ms)
                callback(evt)
            } else { // We're sleeping.  Make note of the event.
                last_evt = evt
            }
        }
    }
    if (typeof target === 'string') target = $(target)
    target.addEventListener(event, listener, args)
    return () => {
        clearTimeout(tid)
        if (last_evt !== null) callback(last_evt)  // make sure the latest value got received
        target.removeEventListener(event, listener, args)
    }
}


/// Sugar for document.querySelector() 
export function $(dom_path) {
    return document.querySelector(dom_path)
}
