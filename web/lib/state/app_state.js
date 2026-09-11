import { createContext } from 'preact'
import { create_cxn } from './cxn.js' 

export const AppState = createContext()

export function create_app_state({token=null}={}) {
    const cxn = create_cxn()
    cxn.set_token(token)
    
    return { cxn }
}
