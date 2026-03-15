# KabuSys

KabuSys は日本株向けの自動売買システムの骨組みとなる Python パッケージです。  
本リポジトリは設定読み込み、環境変数管理、各種モジュール（データ取得、ストラテジ、注文実行、監視）の基盤を提供します。

バージョン: 0.1.0

---

## 概要

- 日本株自動売買の基盤ライブラリ。
- 環境変数／.env ファイルの柔軟な読み込みと検証を行う `kabusys.config.Settings` を提供。
- J-Quants API、kabuステーション API、Slack、ローカル DB（DuckDB / SQLite）などを想定した設定項目を定義。
- モジュール構成（data / strategy / execution / monitoring）の雛形を含む。

---

## 主な機能

- .env ファイル自動読み込み（プロジェクトルートを自動検出）
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env で上書きされない
  - `.env.local` は `.env` の上書きとして読み込まれる
  - 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 高度な .env パーサ
  - 空行／コメント行を無視
  - export プレフィックスに対応（`export KEY=val`）
  - シングル・ダブルクォート内のエスケープ処理対応
  - クォート無し値の行末コメント処理（直前が空白/タブの場合のみ）
- 設定プロパティ（`kabusys.config.Settings`）
  - J-Quants: `jquants_refresh_token`（必須）
  - kabuステーション: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルトあり）
  - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
  - DB: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
  - 実行環境: `env`（`development` / `paper_trading` / `live` のいずれか）、`log_level`（`DEBUG`等）
  - 利便性プロパティ: `is_live`, `is_paper`, `is_dev`
- 設定値の未設定・不正値は早期に例外で通知（ValueError）

---

## 必要条件

- Python 3.10 以上（型ヒントの union 演算子 `X | Y` を使用しているため）
- 推奨: 仮想環境（venv / conda 等）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール（編集可能インストール）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを抑止する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix/macOS
     set KABUSYS_DISABLE_AUTO_ENV_LOAD=1      # Windows (cmd)
     ```

5. 必須環境変数の例（.env）
   以下は最低限必要なキーの例です（実際の値は各自で設定してください）:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUS_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて変更
   ```

   注意: 必須キーが未設定の場合、`kabusys.config.Settings` の該当プロパティ呼び出し時に ValueError が発生します。

---

## 使い方

- 設定の取得例:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  is_live = settings.is_live
  duckdb_file = settings.duckdb_path
  ```

- パッケージ基本情報:
  ```python
  import kabusys
  print(kabusys.__version__)
  ```

- 自動環境読み込みの動作確認:
  - プロジェクトルートに `.env` を置くと、プロセス起動時に自動で読み込まれます。
  - テストなどで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- .env の書き方（補足）
  - 値にスペースや `#` を含めたい場合はクォートで囲んでください。例: `KEY="value with # hash"`
  - クォート内ではバックスラッシュでエスケープ可能（例: `KEY="a\"b"` → a"b）
  - `export KEY=val` 形式も許容します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py            — パッケージ初期化（バージョン指定）
    - config.py              — 環境変数・設定管理（自動 .env ロード、Settings クラス）
    - data/
      - __init__.py          — データ取得関連の雛形モジュール
    - strategy/
      - __init__.py          — ストラテジ関連の雛形モジュール
    - execution/
      - __init__.py          — 注文実行関連の雛形モジュール
    - monitoring/
      - __init__.py          — 監視・ロギング関連の雛形モジュール

README や .env.example 等の補助ファイルはプロジェクトルートに配置してください（本コードベースでは .env.example は参照されていますが、実ファイルは含まれていません）。

---

## 開発上の注意点 / 補足

- 設定値の妥当性チェックは `Settings` 側で行われるため、呼び出し側では未設定や不正値による例外に備えてください（例えば起動時にキャッチしてログ出力し停止する等）。
- DB パス（DuckDB / SQLite）はデフォルトで `data/` 以下を指すため、実行前にディレクトリ作成が必要な場合があります。
- 現状はモジュールの雛形が中心です。具体的なデータ取得・ストラテジ・実行ロジックは各自実装してください。

---

必要であれば、.env.example のテンプレート、実行スクリプト例（モジュール呼び出し例）、CI 用設定、あるいは各モジュールの実装例（kabu API 呼び出し、Slack 通知等）も作成します。どれを優先してほしいか教えてください。