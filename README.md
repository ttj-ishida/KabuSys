# KabuSys

日本株向け自動売買基盤（ライブラリ）です。  
本リポジトリはデータ層（DuckDB スキーマ）、設定管理、戦略・発注・モニタリングの骨組みを含むパッケージ構成になっています。現状はスケルトン／基盤実装が中心で、個別の戦略や実行ロジックは各自実装して利用します。

## 主な特徴
- 環境変数と .env ファイルの自動読み込み（プロジェクトルート検出）
- DuckDB を用いた層別データスキーマ（Raw / Processed / Feature / Execution）
- アプリケーション設定のラッパー（必須値のチェック、環境判定）
- 発注・監視・戦略用のパッケージ構成（strategy, execution, monitoring のプレースホルダ）

---

## 機能一覧
- 設定（kabusys.config.Settings）
  - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development, paper_trading, live）などを環境変数から読み取り
  - 必須値が未設定の場合は例外を投げる
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込む
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
  - export 形式や引用符、コメント（#）等の一般的な .env 記法に対応
- DuckDB スキーマ初期化（kabusys.data.schema.init_schema）
  - 多数のテーブル（raw_prices, prices_daily, features, signals, orders, trades, positions など）を定義
  - インデックスの作成
  - 冪等（既存テーブルがあればスキップ）
  - ファイル DB の親ディレクトリがなければ自動作成
- DuckDB 接続取得（kabusys.data.schema.get_connection）

---

## 要求環境 / 依存
- Python 3.10+
  - 型定義で `X | Y` を使っているため Python 3.10 以上が必要です
- 必要なパッケージ（最小）
  - duckdb
- その他、実際に API と連携する場合は各種クライアント（Slack SDK / J-Quants クライアント / kabu API クライアント等）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - git clone ... を行ってください。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - まずは最低限 DuckDB を入れる:
     - pip install duckdb
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。
   - 開発時は editable install:
     - pip install -e .

4. 環境変数の設定
   - 必須環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - データベースパス（任意、デフォルトを使用可）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - 実行環境:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - ログレベル:
     - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

5. .env ファイル（任意）
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動でロードされます（自動ロードを無効にしない限り）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - `.env.local` は `.env` を上書きする用途で使われます（OS 環境変数は保護される）。

---

## 使い方（簡易ガイド）

- 設定値の参照:
  ```python
  from kabusys.config import settings

  print(settings.env)  # development / paper_trading / live
  print(settings.kabu_api_base_url)  # デフォルト: http://localhost:18080/kabusapi
  ```

- DuckDB スキーマの初期化:
  ```python
  from kabusys.data.schema import init_schema
  from pathlib import Path

  db_path = Path("data/kabusys.duckdb")
  conn = init_schema(db_path)  # テーブルとインデックスを作成し、接続を返す

  # :memory: を使ってインメモリ DB で初期化することも可能
  conn_mem = init_schema(":memory:")
  ```

- 既存 DB への接続取得:
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 自動 .env ロードを無効化したい場合（テスト等）:
  - 環境変数を設定して起動:
    - Unix/macOS: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - Windows (PowerShell): $env:KABUSYS_DISABLE_AUTO_ENV_LOAD="1"

---

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理（自動 .env ロード含む）
    - data/
      - __init__.py
      - schema.py              — DuckDB スキーマ定義・初期化ロジック（init_schema, get_connection）
    - strategy/
      - __init__.py            — 戦略モジュール（実装場所）
    - execution/
      - __init__.py            — 発注・注文管理（実装場所）
    - monitoring/
      - __init__.py            — 監視・ログ・メトリクス（実装場所）

---

## 実装上の注意点 / 補足
- Settings は必須変数が未設定だと ValueError を投げます。初回実行前に必須環境変数を用意してください。
- .env のパースは一般的なケース（export 形式、シングル/ダブルクォート、コメント）に対応していますが、極端な形式は想定外の動作をする可能性があります。
- DuckDB のスキーマは多くのテーブルと制約を定義します。既存の DB への移行・マイグレーションは慎重に行ってください（本モジュールの init_schema は既存テーブルがあれば作成をスキップしますが、列の変更などは行いません）。
- 実運用（ライブトレード）では必ず十分なテストと安全策（ペーパートレード、オフラインのシミュレーション、リスク制御）を行ってください。

---

必要に応じて README に追記（例: CI / テストの実行方法、パッケージ公開方法、具体的な戦略テンプレート）します。追加で載せたい情報があれば教えてください。