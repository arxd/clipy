import sys, re, socket, tempfile
from datetime import datetime
from cli import ConfigVar
from .sys_tool import SysTool
from pathlib import Path


class OpenSSL(SysTool):

    sub_commands = ['req', 'x509', 'genrsa', 'rand', 'dgst']
    version_probe = (lambda s: (s.cmd.v, 'version')), r'^(Open|Libre)SSL (?P<v0>\d+)\.(?P<v1>\d+)\.(?P<v2>\d+).*$'
    cmd = ConfigVar('openssl_path The path to the openssl executable', default='openssl')
    version = ConfigVar('openssl_version The required version of openssl', default='3.3')
    ca = ConfigVar('openssl_ca The default CA to use when creating a server certificate', default='~/.ssh/ca_localhost')
    days = ConfigVar('openssl_server_days The default number of days for a server certificate', default=28)
                     
    @classmethod
    def install_help_generic(self):
        return ['Get OpenSSL 3.x and / or set the OpenSSL.cmd config variable.',
                '$ brew install openssl']

    @property
    def is_libre(self):
        return self.version_probe_result.startswith('LibreSSL')


    def inspect(self, prefix, mode='-subject', **kwargs):
        sep = '/' if self.is_libre else ', '
        v = self.x509('-in', f'{prefix}.pem', mode, '-noout', msg=None, if_0='utf8,,', if_1='null,null,', **kwargs)
        if v is None: return
        parts = dict(map(str.strip, x.split('=')) for x in v[len(mode):].split(sep) if '=' in x)
        return parts


    def expires(self, prefix):
        v = self.x509('-enddate','-noout','-in', f'{prefix}.pem', msg=None, if_0='utf8,,', if_1='null,null,')
        if v is None: return
        return datetime.strptime(v.split('=',1)[1].strip(), "%b %d %H:%M:%S %Y %Z") - datetime.now()


    def cert(self, *, prefix, cn=None, ca, san=[], client=False, force=False, askpass=False, days=314, **kwargs):
        prefix = Path(prefix)
        if not force and prefix.with_suffix('.pem').exists():
            raise ValueError(f'Certificate exists: {prefix}.pem')
        prefix.parent.mkdir(parents=True, exist_ok=True)
    # Create the config file with all the options
        req = dict(distinguished_name='req_distinguished_name', req_extensions='v3_req', x509_extensions='v3_req', prompt='no')
        req_dn = {'O':'cli.py', **({'CN':cn} if cn else {})}
        v3_req = {'basicConstraints':f'critical,CA:{str(not ca).upper()}', 'subjectKeyIdentifier':'hash'}
        if san: v3_req['subjectAltName'] = '@alt_names'
        if ca: v3_req['extendedKeyUsage'] = 'clientAuth' if client else 'serverAuth'
        if not ca: v3_req.update({'keyUsage':'critical,keyCertSign', 'authorityKeyIdentifier':'keyid,issuer'})
        cnf = {'req':req, 'req_distinguished_name':req_dn, 'v3_req':v3_req}
        sans = [[],[]]
        for name in san: sans[bool(re.match(r'^[0-9.:]+$', name))].append(name)
        if san:
            cnf['alt_names'] = {}
            for i, name in enumerate(sans[0]): cnf['alt_names'][f'DNS.{i+1}'] = name
            for i, name in enumerate(sans[1]): cnf['alt_names'][f'IP.{i+1}'] = name
    # Use temporary req.cnf and cob.csr to create the certificate
        with tempfile.TemporaryDirectory() as tmp_dir:
            cnf_file = Path(tmp_dir)/'req.cnf'
            csr_file = Path(tmp_dir)/'cob.csr'
            with open(cnf_file,'w') as f:
                for name, kw in cnf.items():
                    f.write(f'[ {name} ]\n')
                    for k,v in kw.items():
                        f.write(f'{k} = {v}\n')
                    f.write('\n')
            with open(cnf_file) as f:
                print(f.read())
            cmd = ('-newkey', 'rsa:2048', '-keyout', f'{prefix}-key.pem', '-config', cnf_file)
            if not askpass: cmd = (*cmd, '-nodes' if self.is_libre else '-noenc')
            if ca:
                # Two-step process for old LibreSSL
                self.req('-new', *cmd, '-out', csr_file)
                self.x509('-req', '-in', csr_file, '-CA', f'{ca}.pem', '-CAkey', f'{ca}-key.pem', '-days', days, '-CAcreateserial', '-extfile', cnf_file, '-extensions', 'v3_req', '-sha256', '-out', f'{prefix}.pem')
            else:
                self.req('-x509', *cmd, '-days', days, '-out', f'{prefix}.pem')
        return self.inspect(prefix)


    def rsa(self, *, path=None):
        return self.genrsa(*(['-traditional']*(not self.is_libre)), *(['-out', path]*bool(path)), msg=None, if_0="utf8,null,")


    def rand_hex(self, *, path=None, nbytes=32):
        return self.rand('-hex', *(['-out', path]*bool(path)), str(nbytes), msg=None, if_0="utf8,,").strip()


    def sha256(self, fname):
        return (self.dgst('-sha256', '-hex', '-r', fname, msg=None, if_0='utf8,,', if_1='null,null,') or '').split(' ',1)[0]


    def ensure_server_cert(self, prefix, cn='webserver'):
        hostname = socket.gethostname()
        if (exp:=self.expires(prefix)) and exp.days > 2: return
        ca = Path(OpenSSL.ca.v).expanduser().resolve()
        if not (exp:=self.expires(ca)) or exp.days < OpenSSL.days.v:
            print("Creating system-wide CA certificate")
            self.cert(prefix=ca, askpass=False, days=OpenSSL.days.v*4, ca=None, cn='localhost-ca', force=True)
            if sys.platform == "darwin":
                from .run import run
                run(['sudo','security', 'add-trusted-cert', '-d', '-r', 'trustRoot', '-k', '/Library/Keychains/System.keychain', f'{ca}.pem'], msg="Enter your password to add the newly created CA certificate to the system's trusted roots")
            else:
                print(f"Manually add this certificate to the set of trusted ca certificates: {ca}.pem") 
        self.cert(prefix=prefix, askpass=False, days=OpenSSL.days.v, cn=cn, ca=ca, san=['localhost','127.0.0.1','dev.localhost','*.dev.localhost',hostname, f'*.{hostname}'])
