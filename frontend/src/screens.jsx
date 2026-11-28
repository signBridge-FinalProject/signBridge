import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bookmark, Camera, Hand, Info, Mic, MessagesSquare, UserRound } from 'lucide-react'
import { Link } from 'react-router'

// SB-55: static screen shells for the entry flow (MF1) and the conversation layouts (MF10).
// Nothing here opens the camera or microphone, recognises signs, speaks, or calls a server.
// All words and signs shown are placeholders, labelled as such on screen.

export const MODES = [
  { to: '/isaretten-sese', title: 'İşaretten sese', description: 'İşaret dilini Türkçe cümleye çevirin.', Icon: Hand },
  { to: '/sesten-isarete', title: 'Sesten işarete', description: 'Konuşmayı işaret dizisine çevirin.', Icon: Mic },
  { to: '/iki-yonlu', title: 'İki yönlü konuşma', description: 'İşaret ve konuşma arasında sırayla iletişim kurun.', Icon: MessagesSquare },
  { to: '/hizli-ifadeler', title: 'Hızlı ifadeler', description: 'Kayıtlı cümlelere tek dokunuşla ulaşın.', Icon: Bookmark },
]

function Screen({ title, lead, children }) {
  return (
    <article className="screen">
      <h1 tabIndex={-1}>{title}</h1>
      <p className="lead">{lead}</p>
      <p className="notice" role="note">
        <Info aria-hidden="true" />
        <span><strong>Yerleşim örneği.</strong> Bu sürümde kamera, mikrofon, işaret tanıma, seslendirme veya sunucu bağlantısı yoktur. Gösterilen tüm içerik yer tutucudur.</span>
      </p>
      {children}
      <Link className="back-link" to="/"><ArrowLeft aria-hidden="true" />Mod seçimine dön</Link>
    </article>
  )
}

// Moves focus to the step heading when the step changes, so keyboard and screen reader users land on the new content.
function useStepFocus(step) {
  const heading = useRef(null)
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    heading.current?.focus()
  }, [step])
  return heading
}

function CameraPanel() {
  return (
    <div className="panel camera">
      <Camera aria-hidden="true" />
      <p><strong>Kamera alanı (yer tutucu)</strong></p>
      <p className="status">Kamera açılmaz. El takibi: kapalı.</p>
    </div>
  )
}

function MicPanel() {
  return (
    <div className="panel mic">
      <Mic aria-hidden="true" />
      <p><strong>Mikrofon alanı (yer tutucu)</strong></p>
      <p className="status">Mikrofon açılmaz. Ses dinlenmez.</p>
    </div>
  )
}

function AvatarPanel() {
  return (
    <div className="panel avatar">
      <UserRound aria-hidden="true" />
      <p><strong>Avatar alanı (yer tutucu)</strong></p>
      <p className="status">İşaret animasyonu oynatılmaz.</p>
    </div>
  )
}

function Strip({ label, children }) {
  return <p className="strip"><span className="strip-label">{label}</span>{children}</p>
}

const SIGN_PLACEHOLDER = '[İŞARET 1] [İŞARET 2] [İŞARET 3]'

export function SignToVoice() {
  const [step, setStep] = useState(0)
  const heading = useStepFocus(step)
  return (
    <Screen title="İşaretten sese" lead="İşaret verin, oluşan cümleyi kontrol edin, sonra sese çevirin. Aşağıdaki üç adım yalnızca ekran düzenini gösterir.">
      {step === 0 && (
        <section aria-labelledby="adim">
          <h2 id="adim" ref={heading} tabIndex={-1} className="step-heading">1. Adım: İşaret verme</h2>
          <CameraPanel />
          <Strip label="Tanınan işaretler (yer tutucu)">{SIGN_PLACEHOLDER}</Strip>
          <div className="actions">
            <button type="button" className="button primary" onClick={() => setStep(1)}>Bitti</button>
          </div>
        </section>
      )}
      {step === 1 && (
        <section aria-labelledby="adim">
          <h2 id="adim" ref={heading} tabIndex={-1} className="step-heading">2. Adım: Cümleyi kontrol edin</h2>
          <p className="sentence">Örnek cümle burada görünür.</p>
          <div className="actions">
            <button type="button" className="button primary" onClick={() => setStep(2)}>Konuş</button>
            <button type="button" className="button" onClick={() => setStep(0)}>Düzenle</button>
          </div>
        </section>
      )}
      {step === 2 && (
        <section aria-labelledby="adim">
          <h2 id="adim" ref={heading} tabIndex={-1} className="step-heading">3. Adım: Seslendirme ekranı</h2>
          <p className="sentence">Örnek cümle burada görünür.</p>
          <p className="status-line">Seslendirme yapılmaz. Bu yalnızca ekran düzenidir.</p>
          <div className="actions">
            <button type="button" className="button" onClick={() => setStep(1)}>Tekrarla</button>
            <button type="button" className="button" onClick={() => setStep(0)}>Yeni işaret ver</button>
          </div>
        </section>
      )}
    </Screen>
  )
}

export function VoiceToSign() {
  const [step, setStep] = useState(0)
  const heading = useStepFocus(step)
  return (
    <Screen title="Sesten işarete" lead="Konuşmanın metni görünür, ardından işaret dizisi avatar alanında gösterilir. Aşağıdaki iki adım yalnızca ekran düzenini gösterir.">
      {step === 0 && (
        <section aria-labelledby="adim">
          <h2 id="adim" ref={heading} tabIndex={-1} className="step-heading">1. Adım: Dinleme</h2>
          <MicPanel />
          <p className="transcript"><span className="strip-label">Konuşma metni (yer tutucu)</span>Konuşma metni burada görünür.</p>
          <div className="actions">
            <button type="button" className="button primary" onClick={() => setStep(1)}>Konuşmayı bitir</button>
          </div>
        </section>
      )}
      {step === 1 && (
        <section aria-labelledby="adim">
          <h2 id="adim" ref={heading} tabIndex={-1} className="step-heading">2. Adım: Avatar</h2>
          <AvatarPanel />
          <Strip label="İşaret dizisi (yer tutucu)">{SIGN_PLACEHOLDER}</Strip>
          <p className="status-line">Hız 1,0×. Tekrar oynatma bu sürümde yoktur.</p>
          <div className="actions">
            <button type="button" className="button primary" onClick={() => setStep(0)}>Yeniden dinle</button>
          </div>
        </section>
      )}
    </Screen>
  )
}

export function TwoWay() {
  const [turn, setTurn] = useState('hearing')
  const hearing = turn === 'hearing'
  return (
    <Screen title="İki yönlü konuşma" lead="Duyan kişi konuşur, işaret eden kişi işaret verir. Sıra değişir. Bu ekran iki tarafın yan yana yerleşimini gösterir.">
      <p className="turn" role="status">Sıra: <strong>{hearing ? 'Duyan kişi' : 'İşaret eden kişi'}</strong></p>
      <div className="two-way">
        <section className="side" data-active={hearing} aria-labelledby="duyan">
          <h2 id="duyan" className="side-heading">Duyan kişi</h2>
          <MicPanel />
          <p className="transcript"><span className="strip-label">Konuşma metni (yer tutucu)</span>Konuşma metni burada görünür.</p>
        </section>
        <section className="side" data-active={!hearing} aria-labelledby="isaret">
          <h2 id="isaret" className="side-heading">İşaret eden kişi</h2>
          <CameraPanel />
          <Strip label="Tanınan işaretler (yer tutucu)">{SIGN_PLACEHOLDER}</Strip>
        </section>
      </div>
      <div className="actions">
        <button type="button" className="button primary" onClick={() => setTurn(hearing ? 'signing' : 'hearing')}>Sırayı değiştir</button>
      </div>
      <section aria-labelledby="kayit" className="log-section">
        <h2 id="kayit" className="step-heading">Konuşma kaydı (örnek)</h2>
        <ol className="log">
          <li><strong>Duyan kişi:</strong> Örnek cümle 1.</li>
          <li><strong>İşaret eden kişi:</strong> {SIGN_PLACEHOLDER}</li>
          <li><strong>Duyan kişi:</strong> Örnek cümle 2.</li>
        </ol>
      </section>
    </Screen>
  )
}

export function QuickPhrases() {
  return (
    <Screen title="Hızlı ifadeler" lead="Kayıtlı cümleler bu ekranda listelenecek.">
      <p className="status-line">Bu ekran SB-55 kapsamında değildir (MF11). Mod seçiminde yalnızca yönlendirme olarak yer alır; kayıt, liste ve seslendirme yoktur.</p>
    </Screen>
  )
}
