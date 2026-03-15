# KabuSys

日本株の自動売買システム向けライブラリ（軽量ベース）。  
このリポジトリは、設定管理やデータ/戦略/実行/監視用のパッケージ構成を提供します。コアの取引ロジックや各モジュールの実装はこの上に構築していきます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムの基礎となる Python パッケージです。  
- 環境変数や .env ファイルからの設定読み込み（自動ロード機能）  
- J-Quants / kabuステーション / Slack / データベースなどの標準的な設定項目を提供  
- data / strategy / execution / monitoring といったサブパッケージ構成により、実装を分離して拡張しやすく設計

このリポジトリはフレームワーク／スケルトンとして利用し、独自の戦略や実行ロジックを追加して運用します。

---

## 主な機能

- 環境変数および .env ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
- .env パーサ（export 形式、シングル/ダブルクォート、エスケープ、コメント処理に対応）
- 設定アクセスのための Settings クラス（プロパティ経由で安全に取得）
  - J-Quants リフレッシュトークン
  - kabuステーション API (パスワード・ベースURL)
  - Slack トークン / チャネル
  - データベースファイルパス（DuckDB / SQLite）
  - 環境（development / paper_trading / live）とログレベル検証
- 簡単に拡張できるパッケージ構成 (data, strategy, execution, monitoring)

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションで `X | Y` を使用しているため）
- 必要に応じて DuckDB／SQLite 等の外部ライブラリを導入

開発環境へのインストール（リポジトリルートで実行）:
```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

.env の準備:
- プロジェクトルートに `.env` または `.env.local` を作成してください。
- `.env.local` は `.env` を上書きする優先度で読み込まれます。

自動ロードの制御:
- デフォルトでは、OS環境変数 > .env.local > .env の順で設定が反映されます。
- 自動ロードを無効化するには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに利用）。

---

## 必要な環境変数

以下は Settings クラスから参照される主な環境変数です。必須のものは未設定時に例外が発生します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack bot token
- SLACK_CHANNEL_ID — Slack の投稿先チャネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabuステーションのベースURL（デフォルト: "http://localhost:18080/kabusapi"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（有効値: development, paper_trading, live。デフォルト: development）
- LOG_LEVEL — ログレベル（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）

.env の例（テンプレート）:
```
# .env (例)
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

SLACK_BOT_TOKEN="xoxb-xxxxxxxxxx"
SLACK_CHANNEL_ID="C01234567"

# データベースパス（任意）
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 環境（development|paper_trading|live）
KABUSYS_ENV=development

# ログレベル
LOG_LEVEL=INFO
```

.env パーサの挙動（主なポイント）:
- 行頭の `export ` を許可（例: export KEY=val）
- シングル/ダブルクォート内のエスケープ（バックスラッシュ）に対応
- クォートがない値では、`#` の直前が空白/タブならコメントとみなす（通常の inline comment 処理）
- 読み込み順と上書きルール: OS 環境変数（保護） > .env > .env.local（.env.local は override=True）

---

## 使い方

基本的な設定の取得例:
```python
from kabusys.config import settings

# 必須項目を取得（未設定なら ValueError）
jquants_token = settings.jquants_refresh_token
kabu_password = settings.kabu_api_password

# オプション（デフォルトを持つ）
kabu_base = settings.kabu_api_base_url
duckdb_path = settings.duckdb_path

# 環境判定
if settings.is_live:
    print("LIVE 環境です")
elif settings.is_paper:
    print("ペーパートレード環境です")
else:
    print("開発環境です")

# ログレベル
print("LOG_LEVEL =", settings.log_level)
```

パッケージ情報:
```python
import kabusys
print(kabusys.__version__)
```

開発時のワークフロー例:
- strategy モジュールに 独自の戦略クラスを実装
- execution モジュールに売買 API 呼び出しの実装を追加
- monitoring モジュールで監視・アラート（例: Slack 送信）を実装
- data モジュールで市場データ取得や DB 保存処理を実装

---

## ディレクトリ構成

リポジトリの主要ファイル構成（src 配下）:
```
src/
└─ kabusys/
   ├─ __init__.py         # パッケージのエントリ（__version__ 等）
   ├─ config.py           # 環境変数 / 設定読み込みロジック（Settings）
   ├─ data/               # (将来的に) データ取得・格納関連
   │  └─ __init__.py
   ├─ strategy/           # (将来的に) 売買戦略
   │  └─ __init__.py
   ├─ execution/          # (将来的に) 注文実行ロジック
   │  └─ __init__.py
   └─ monitoring/         # (将来的に) 監視/アラート処理
      └─ __init__.py
```

---

## 開発・テストのヒント

- 自動環境読み込みを無効化してテストする場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OS 環境変数は .env の内容より優先されます。テスト用に一時的な値を上書きしたい場合は、OS 側で環境変数を設定してください。
- .env ファイルの読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml が見つかる親ディレクトリ）。パッケージ配布後に CWD が変わっても安定して動作するよう設計されています。

---

## 拡張について（ガイド）

- data: マーケットデータ取得、キャッシュ、DB 永続化（DuckDB 想定）
- strategy: エントリ/イグジットの判定ロジック、リスク管理
- execution: kabuAPI 等を用いた注文処理、注文管理（リトライ・エラーハンドリング）
- monitoring: Slack 通知、ロギング、取引結果の集計

これらのモジュールを分離することで、テストやCI/CD、実運用（ペーパートレード→本番切り替え）を容易にします。

---

必要に応じて README をプロジェクトの実装状況に合わせて更新してください（.env.example の追加、サンプル戦略・実行スクリプト、テスト手順など）。