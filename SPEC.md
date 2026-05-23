# yomiage-bot 仕様・方針

Discord のテキストチャンネルに投稿されたメッセージを、ボイスチャンネルで VOICEVOX（ずんだもん等）に読み上げさせる、個人／小規模サーバー向けの読み上げ Bot。

## 1. 目的とスコープ

- 非公開 Bot として運用する（Public Bot を OFF にし、自分が招待したサーバーでのみ動作）。
- 1 サーバーにつき 1 つのテキストチャンネルを読み上げ対象とする。
- 合成は外部の VOICEVOX エンジン（コンテナ）に委譲し、Bot 本体は I/O とキュー制御に専念する。

## 2. 構成

```
[Discord] ── Gateway ──> [bot コンテナ (Python / discord.py)]
                              │
                              └── HTTP ──> [voicevox コンテナ :50021]
```

`docker compose` で `bot` と `voicevox` の 2 サービスを同居させる。`bot` から `voicevox` へは `VOICEVOX_URL` 経由でアクセスする（compose 内で `http://voicevox:50021` を注入）。

## 3. コマンド（Slash Commands）

| コマンド | 動作 |
|---|---|
| `/join` | 実行者が参加しているボイスチャンネルに Bot が参加し、コマンドを叩いた**テキストチャンネル**を読み上げ対象として登録する。 |
| `/leave` | ボイスチャンネルから退出し、読み上げ対象を解除する。 |

`/join` を別のチャンネルで叩き直すと、Bot は新しい VC に移動し、読み上げ対象も切り替わる。

## 4. 読み上げ仕様

- 対象は `/join` を実行したテキストチャンネルのみ。ギルド単位で 1 チャンネル。
- Bot 自身のメッセージと DM は読み上げない。
- ギルドごとに `asyncio.Queue` で逐次再生する。割り込みは行わず FIFO。
- 1 メッセージごとに VOICEVOX の `/audio_query` → `/synthesis` を呼び、`FFmpegPCMAudio` で再生する。

## 5. テキスト前処理

`bot.py` の `sanitize()` で以下を行う。

- URL（`https?://...`）→ 文字列「URL」に置換。
- カスタム絵文字（`<a?:name:id>`）→ 削除。
- メンション（`<@id>` / `<#id>` / `<@&id>`）→ 削除。
- 前後の空白を除去。
- **100 文字を超える場合は切り詰め、末尾に「以下略」を付与**。
- 前処理後に空文字となったメッセージはキューに入れない。

## 6. 話者

- 既定: `SPEAKER_ID=3`（ずんだもん ノーマル）。
- `.env` の `SPEAKER_ID` で変更可。代表値:
  - 3: ノーマル / 1: あまあま / 7: ツンツン / 5: セクシー / 22: ささやき / 38: ヒソヒソ

## 7. 環境変数

| 変数 | 必須 | 既定 | 用途 |
|---|---|---|---|
| `DISCORD_TOKEN` | ✅ | — | Discord Developer Portal の **Bot** タブで発行したトークン。 |
| `SPEAKER_ID` | ❌ | `3` | VOICEVOX の話者 ID。 |
| `VOICEVOX_URL` | ❌ | `http://voicevox:50021` | VOICEVOX エンジンのエンドポイント。compose で自動注入される。 |

## 8. Discord 側の設定

### Intents（Bot タブ）
- `MESSAGE CONTENT INTENT`: **ON**
- `SERVER MEMBERS INTENT`: ON 推奨
- `PRESENCE INTENT`: OFF

### Bot 公開設定
- `PUBLIC BOT`: **OFF**（非公開 Bot のため）
- `REQUIRES OAUTH2 CODE GRANT`: OFF

### 招待時に要求する権限（OAuth2 → URL Generator）
- SCOPES: `bot`, `applications.commands`
- BOT PERMISSIONS: `Send Messages`, `Read Message History`, `Connect`, `Speak`

## 9. 運用方針

- コンテナは `restart: unless-stopped` で異常終了時に自動復旧する。
- VOICEVOX イメージは既定で `cpu-arm64-ubuntu20.04-latest`（Apple Silicon / ARM64 向け）。x86_64 環境では `cpu-ubuntu20.04-latest` に差し替える。
- ログは標準出力に Python `logging` で出力する（`logger=yomiage`）。
- 合成失敗時はそのメッセージをスキップしてログに記録し、キューの次のメッセージへ進む（Bot は落ちない）。

## 10. 既知の制約 / 非対応

- 読み上げ対象チャンネルの設定はメモリ上のみで、Bot 再起動で失われる。
- 添付ファイル・スタンプ・埋め込みは読み上げ対象外（テキスト本文のみ）。
- 1 ギルドあたりの並列再生・割り込み・スキップ機能は持たない。
- ユーザーごとの話者切替は持たない（ギルド共通）。

## 11. 将来検討する拡張

- 読み上げ対象チャンネルの永続化（ファイル or SQLite）。
- `/skip`, `/clear` 等のキュー操作コマンド。
- ユーザーごとの話者割り当て。
- 辞書機能（読み替え登録）。
