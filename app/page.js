'use client'

import Image from 'next/image'
import styles from './page.module.css'
import {useState} from 'react'
import Description from '../components/Description'

export default function Home() {
  const [formData, setFormData] = useState(
    {
      book: "",
      character: ""         
    }
  )

  const [llmOutput, setLlmOutput] = useState("")

  function handleSubmit(event) {
    event.preventDefault()
    const url = `https://sandcat100--stable-diffusion-cli-llm-entrypoint-dev.modal.run?book=${encodeURIComponent(formData.book)}&character=${encodeURIComponent(formData.character)}`
      fetch(url)
      .then(response => {
        if (response.ok) {
          return response.json()
        }
        throw new Error("Bad response from Modal endpoint")
      })
      .then(data => setLlmOutput(data))
      .catch(error => console.log(error))
    // setLlmOutput("slender, middle-aged man with a refined and dignified appearance, thinning silver hair, piercing blue eyes, sharp nose, elegant dress shirt, tailored suit, polished shoes")
  }

  function handleFormChange(event) {
    const {name, value} = event.target
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }))
  }

  return (
    <main className={styles.main}>
      <h1>hi babbit!!!!</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Book:
          <input 
            type="text"
            name="book"
            onChange={handleFormChange}
            value={formData.book}
          />
        </label>        
        <label>
          Character:
          <input
            type="text"
            name="character"
            onChange={handleFormChange}
            value={formData.character}
          />
        </label>
        <button>Generate</button>
      </form>
      <Description
        llmOutput={llmOutput}
      />
    </main>
  )
}
