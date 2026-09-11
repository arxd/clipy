import { signal, effect, createModel, batch } from '@preact/signals'

const max_backoff = 30000
const init_backoff = 1000
const url = `wss://${window.location.host}/ws`
const protocol = 'v0'

export const create_cxn = createModel(() => {
    let backoff = init_backoff
    let ws = null
    let token = null
    let reconnect = null

    const status = signal('logout')
    const user = signal(null)

    const _shutdown = () => {
        console.log(`[ws] shutdown timer?${!!reconnect}. ws?${!!ws} ${ws?.readyState}`)
        if (reconnect) {
            clearTimeout(reconnect)
            reconnect = null
        }
        if (!ws) return

        ws.onopen = null
        ws.onclose = null
        ws.onerror = null
        ws.onmessage = null

        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close()
        ws = null
    }

    const _connect = () => {
        if (ws) throw "ws is not null in _connect"
        console.log(`[ws] _connect ${url}`)
        status.value = 'connecting'
        ws = new WebSocket(url, [protocol, token])

        ws.onopen = () => {
            console.log('[ws] connected')
            backoff = init_backoff
        }

        ws.onmessage = (event) => {
            console.log(event.data)
            status.value = 'ok'
        }

        ws.onclose = (event) => {
            console.log(`[ws] closed ${event.code}`)
            ws = null

            if (event.code === 1006) { 
                status.value = 'error'
                user.value = null
                token = null // retrying won't help
            } 
            
            if (token) { // attempt to reconnect
                status.value = 'connecting'
                console.log(`[ws] reconnect in ${backoff}`)
                reconnect = setTimeout(() => { _connect() }, backoff)
                backoff = Math.min(max_backoff, backoff * 1.6 + Math.random() * 314)
            }
        }

        ws.onerror = (e) => {
            console.log(`[ws] error ${e}`)
        }
    }

    effect(() => {
        console.log(`event: ${status.value} ${user.value}`)
    })

    const set_token = (new_token) => {
        console.log(`[ws] set token ${new_token}`)
        token = new_token
        _shutdown()
        if (token) {
            _connect()
        } else {
            batch(() => {
                status.value = 'logout'
                user.value = null
            })
        }
    }
    
    return {
        status,
        user,
        set_token,
    }
})
