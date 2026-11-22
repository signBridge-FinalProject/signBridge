import { ArrowLeft, ArrowUpRight, AudioLines, Hand, Keyboard, MonitorDown } from 'lucide-react'
import { Link } from 'react-router'

function GuideLink({ to, title, description, Icon }) {
  return (
    <Link to={to} className="guide-link">
      <span className="guide-icon"><Icon aria-hidden="true" /></span>
      <span><strong>{title}</strong><span className="detail">{description}</span></span>
      <ArrowUpRight className="arrow" aria-hidden="true" />
    </Link>
  )
}

export function Home() {
  return (
    <>
      <div className="hero">
        <div className="hero-copy">
          <h1 tabIndex={-1}>İşaret Köprüsü</h1>
          <p>Türk İşaret Dili ile Türkçe arasında günlük iletişimi desteklemek için geliştirilen bir araştırma projesi.</p>
        </div>
        <div className="illustration" aria-hidden="true">
          <div className="bubble sign"><Hand /></div>
          <div className="bubble voice"><AudioLines /></div>
        </div>
      </div>
      <section className="guide-section" aria-labelledby="rehber">
        <h2 id="rehber">Kullanım rehberi</h2>
        <div className="guide-list">
          <GuideLink to="/klavye" title="Klavye ile gezinme" description="Bağlantılara ulaşın ve ana içeriğe geçin." Icon={Keyboard} />
          <GuideLink to="/kurulum" title="Cihaza kurulum" description="Ana ekrandan açın ve çevrimdışı kullanın." Icon={MonitorDown} />
        </div>
      </section>
    </>
  )
}

function Article({ title, children }) {
  return (
    <article className="article">
      <h1 tabIndex={-1}>{title}</h1>
      {children}
      <Link className="back-link" to="/"><ArrowLeft aria-hidden="true" />Başlangıca dön</Link>
    </article>
  )
}

export function KeyboardGuide() {
  return (
    <Article title="Klavye ile gezinme">
      <h2>Bağlantılar arasında ilerleme</h2>
      <p><kbd>Tab</kbd> ile sonraki bağlantıya, <kbd>Shift</kbd> + <kbd>Tab</kbd> ile önceki bağlantıya geçin. Çerçeve, odağın yerini gösterir.</p>
      <p><kbd>Enter</kbd> ile bağlantıyı açın. Açılan sayfanın başlığı odaklanır.</p>
      <h2>Menüyü atlama</h2>
      <p>Sayfayı ilk açtığınızda <kbd>Tab</kbd> tuşuna basın. “Ana içeriğe geç” bağlantısını seçip <kbd>Enter</kbd> tuşuna basarak doğrudan içeriğe ulaşabilirsiniz.</p>
    </Article>
  )
}

export function InstallGuide() {
  return (
    <Article title="Cihaza kurulum">
      <h2>Ana ekrana ekleme</h2>
      <p>Kurulumu destekleyen bir tarayıcıda adres çubuğundaki yükleme simgesini veya menüdeki uygulama yükleme seçeneğini kullanın. iPhone’da Safari’nin paylaşım menüsünden “Ana Ekrana Ekle”yi seçin.</p>
      <p>Kurulumdan sonra İşaret Köprüsü’nü cihazınızdaki SignBridge simgesinden açabilirsiniz.</p>
      <h2>Çevrimdışı açma</h2>
      <p>İlk açılışta çevrimiçi kalın. Uygulama dosyaları cihaza kaydedildikten sonra başlangıç sayfasını ve bu rehberleri internet bağlantısı olmadan da açabilirsiniz.</p>
    </Article>
  )
}

export function NotFound() {
  return <Article title="Sayfa bulunamadı"><p>Adresi kontrol edin veya başlangıç sayfasına dönün.</p></Article>
}
