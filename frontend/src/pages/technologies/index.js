import { Title, Container, Main } from '../../components'
import styles from './styles.module.css'
import MetaTags from 'react-meta-tags'

const Technologies = () => {
  return (
    <Main>
      <MetaTags>
        <title>Технологии</title>
        <meta name="description" content="Фудграм — Технологии проекта" />
        <meta property="og:title" content="Технологии" />
      </MetaTags>

      <Container>
        <h1 className={styles.title}>Технологии</h1>

        <div className={styles.content}>
          <div>
            <h2 className={styles.subtitle}>Что используется в проекте:</h2>
            <ul className={styles.text}>
              <li className={styles.textItem}>⚙️ <strong>Python 3.10</strong> — основной язык бэкенда</li>
              <li className={styles.textItem}>🌐 <strong>Django 5.1</strong> — фреймворк для создания веб-приложений</li>
              <li className={styles.textItem}>🔗 <strong>Django REST Framework</strong> — создание REST API</li>
              <li className={styles.textItem}>🔐 <strong>Djoser</strong> — аутентификация через токены</li>
              <li className={styles.textItem}>🐘 <strong>PostgreSQL</strong> — реляционная СУБД</li>
              <li className={styles.textItem}>🐳 <strong>Docker / Docker Compose</strong> — контейнеризация проекта</li>
              <li className={styles.textItem}>⚙️ <strong>Gunicorn + Nginx</strong> — продакшен-сервер</li>
              <li className={styles.textItem}>🛠️ <strong>GitHub Actions</strong> — CI/CD, автодеплой</li>
              <li className={styles.textItem}>⚛️ <strong>React</strong> — фронтенд SPA</li>
            </ul>
          </div>
        </div>
      </Container>
    </Main>
  )
}

export default Technologies