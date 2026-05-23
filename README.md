# yomiage-bot

Discord のテキストチャンネルに投稿されたメッセージを、VOICEVOX（ずんだもん等）でボイスチャンネルに読み上げる Bot。

- 非公開 Bot（自分のサーバー専用）
- `bot`（Python / discord.py）と `voicevox`（音声合成エンジン）の 2 コンテナ構成
- Apple Silicon Mac のローカル環境で動作確認済み

詳細な設計方針は [SPEC.md](./SPEC.md) を参照。

---

## クイックスタート

```bash
git clone <this-repo>
cd yomiage-bot
cp .env.example .env       # .env を作成しトークンを記入
docker compose up --build -d
docker compose logs -f bot # "Logged in as yomiage-bot#XXXX" が出れば成功
```

Discord 側で `/join` → そのテキストチャンネルが読み上げ対象になる。`/leave` で終了。

---

## 1. Discord Developer Portal での設定

<https://discord.com/developers/applications/>

### 1-1. アプリケーション作成
「New Application」から作成。

### 1-2. Installation タブ
- **インストールリンク → 「なし」** に変更して保存
  - これをしないと、Bot タブの保存時に「プライベートアプリケーションはデフォルトの認証リンクを持つことはできません」エラーになる

### 1-3. Bot タブ
- **TOKEN**: 「Reset Token」で発行してコピー（一度しか表示されない）
- **PUBLIC BOT**: OFF
- **Privileged Gateway Intents**
  - MESSAGE CONTENT INTENT: **ON** ← 必須（OFF だと `PrivilegedIntentsRequired` で起動不可）
  - SERVER MEMBERS INTENT: ON 推奨
  - PRESENCE INTENT: OFF

### 1-4. OAuth2 → URL Generator
**SCOPES**
- `bot`
- `applications.commands`

**BOT PERMISSIONS**
- Send Messages
- Read Message History
- Connect
- Speak

生成された招待 URL をブラウザで開き、自分のサーバーで認証する。

---

## 2. プロジェクト構成

```
yomiage-bot/
├── .env              # 自分で作成（コミットしない）
├── .env.example
├── Dockerfile
├── SPEC.md
├── bot.py
├── docker-compose.yml
└── requirements.txt
```

---

## 3. `.env` の作成

```env
DISCORD_TOKEN=（Bot タブで発行したトークン）
SPEAKER_ID=3
```

### SPEAKER_ID 代表値

| ID | 声質 |
|----|------|
| 3  | ずんだもん ノーマル |
| 1  | あまあま |
| 7  | ツンツン |
| 5  | セクシー |
| 22 | ささやき |
| 38 | ヒソヒソ |

---

## 4. Docker 操作

```bash
docker compose up --build -d     # 起動
docker compose logs -f bot       # ログ確認
docker compose down              # 停止
```

x86_64 環境で動かす場合は `docker-compose.yml` の voicevox イメージを `voicevox/voicevox_engine:cpu-ubuntu20.04-latest` に差し替える。

---

## 5. Discord での使い方

| コマンド | 動作 |
|---------|------|
| `/join`  | 実行者がいる VC に Bot を呼び、コマンドを打った**テキストチャンネル**を読み上げ対象に登録 |
| `/leave` | VC から退出し、読み上げ対象を解除 |

1. 自分が VC に入る
2. テキストチャンネルで `/join`
3. そのチャンネルへのメッセージが読み上げられる

`/join` を別チャンネルで打ち直すと、Bot は新しい VC に移動し読み上げ対象も切り替わる。

---

## 6. 読み上げ仕様

- Bot 自身のメッセージと DM は読み上げない
- URL → 「URL」に置換
- カスタム絵文字・メンション → 削除
- 100 文字超 → 切り詰めて末尾に「以下略」
- 添付ファイル・スタンプ・埋め込みは対象外（テキスト本文のみ）

---

## 7. 制約

- Bot は自動追従しない（`/join` で呼ぶ方式）
- 読み上げ対象チャンネルはメモリ上のみで、再起動で解除される
- ローカル運用では Mac がスリープすると停止する
- CPU 合成のため多少のラグがある
- 24 時間稼働させたい場合は Oracle Cloud 等のサーバーへの移行を検討

---

## 8. トラブルシューティング

| 症状 | 対処 |
|------|------|
| `PrivilegedIntentsRequired` | Bot タブの MESSAGE CONTENT INTENT を ON |
| 「プライベートアプリケーションはデフォルトの認証リンクを持つことはできません」 | Installation タブのインストールリンクを「なし」に |
| `env file ... .env not found` | `cp .env.example .env` で `.env` を作成 |
| Bot がオフライン | `docker compose up -d` でコンテナ起動 |
| `/join` が候補に出ない | OAuth2 SCOPES に `applications.commands` が含まれているか確認 |
