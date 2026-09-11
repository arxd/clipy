import { createContext } from 'preact'
import { useCallback, useContext } from 'preact/hooks'
import { signal } from '@preact/signals'
import { html } from 'htm/preact'


/** The route_ctx is used to track the top-level url page
 */
const route_ctx = createContext()
export const useRoute = () => useContext(route_ctx)


/** The url_state is used to track the top-level url page
 */
export const url_state = signal({path:document.location.pathname, hash:document.location.hash})
const set_url_state = function(new_state) {
    if (JSON.stringify(url_state.peek()) !== JSON.stringify(new_state)) url_state.value = new_state
}
window.onpopstate = (e) => set_url_state({path:document.location.pathname, hash:document.location.hash, ...e.state})


/** perform a pushState and also change url_state so routes are updated
*/
export function goto(route, data={}) {
    if (typeof route === 'string') route = {path:route}
    route = {...route, ...data}
    const replace = route.replace
    delete route.replace
    if (replace) history.replaceState(route, '', route.path); else history.pushState(route, '', route.path)
    set_url_state({...route, path:document.location.pathname})
}


/** This is an anchor tag but the default browser load is blocked and a soft pushState is used instead
 */
export const A = ({children, ...props}) => {
    const click = useCallback((e) => {
        e.preventDefault()
        goto(props.href)
    }, [props.href])

    return html`<a onClick=${click} ...${props}>${children}<//>`
}


/** A router watches for changes to the `route_ctx` context and then chooses the first matching route from it's `routes` prop.
 */
export const Router = (props) => {

    let route = useRoute()
    if (!route) {
        // We are the root router, so watch the `url_state` signal and the auth.
        route = {...url_state.value}
    }
    
    for (let option of props.routes) {
        let sub_route = option.match(route)
        if (sub_route?.replace && sub_route.path != document.location.pathname) goto(sub_route)
        if (sub_route) return html`<${route_ctx.Provider} value=${sub_route}>${option.html(sub_route)}<//>`
    }
}


/** A helper to match a route path and return the groups as the sub route
*/
export const match_re = (re) => ({path, ...route}) => {
    const match = re.exec(path || '')
    return match && {...route, ...(match.groups || {})}
}
