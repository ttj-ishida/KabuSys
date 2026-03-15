# KabuSys

日本株向け自動売買基盤（KabuSys）  
バージョン: 0.1.0

簡単な説明: このパッケージは日本株のデータ収集・加工・特徴量生成・発注管理・モニタリングを想定した骨組みを提供します。DuckDB を用いたデータスキーマ定義と、環境変数管理（.env 自動読み込み）を中心に実装されています。戦略（strategy）や実行（execution）、モニタリング（monitoring）用のモジュールが配置される想定です。

---

## 主な機能

- 環境変数 / 設定の集中管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（OS 環境変数が優先）
  - 必須設定を取得するヘルパー（未設定時は例外）
  - 自動読み込みの無効化オプションあり（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）
- DuckDB によるスキーマ定義と初期化
  - Raw / Processed / Feature / Execution の4層構造に基づくテーブル定義
  - インデックス作成、外部キーを考慮したテーブル作成順
  - `init_schema()` で冪等にスキーマを初期化
- パッケージ構成（strategy、execution、monitoring、data モジュールのひな形）

---

## 必要な環境変数／設定

最低限必要（必須）な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意/デフォルト値あり:

- KABUSYS_ENV — 実行環境（`development` / `paper_trading` / `live`）。デフォルト: `development`
- LOG_LEVEL — ログレベル（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）。デフォルト: `INFO`
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — SQLite（モニタリング用 DB）パス。デフォルト: `data/monitoring.db`

.env の自動読み込みについて:

- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパースはシェル風の `KEY=VALUE` 形式に対応（シングル/ダブルクォート、export プレフィックス、行末コメント等を考慮）。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（例）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   このコードベースでは少なくとも `duckdb` を使用しています。プロジェクトの requirements ファイルがあればそれを使ってください。

   ```
   pip install duckdb
   # または requirements.txt があれば:
   # pip install -r requirements.txt
   ```

4. 環境変数を用意する  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記の必須キーを設定してください。例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   注: OS 環境変数が優先されます。

---

## 使い方（簡単な例）

- 設定の読み取り:

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.is_dev)  # development 判定
  ```

- DuckDB スキーマの初期化:

  ```python
  from pathlib import Path
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = init_schema(db_path)     # テーブル作成（存在すればスキップ）
  # 以降 conn を使ってクエリを実行
  df = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchdf()
  ```

  - `init_schema(":memory:")` を渡すとインメモリ DB を使用します。
  - 既存の DB に接続するだけなら `get_connection(db_path)` を使用してください（スキーマ初期化は行いません）。

- シグナル → 発注 → トレード の流れは、`signal_queue` / `orders` / `trades` 等のテーブル定義が用意されています。実際の戦略実装や発注ロジックは `strategy` / `execution` モジュールに実装してください（現在はモジュールのひな形のみ）。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py           # パッケージ初期化（__version__ = "0.1.0"）
    - config.py             # 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - schema.py           # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - strategy/
      - __init__.py         # 戦略モジュール（実装箇所）
    - execution/
      - __init__.py         # 発注実行モジュール（実装箇所）
    - monitoring/
      - __init__.py         # モニタリング用モジュール（実装箇所）
- .env.example              #（ある場合）設定例を置く想定
- pyproject.toml / setup / その他パッケージ設定ファイル（存在する場合）

---

## 補足 / 開発メモ

- スキーマは Raw / Processed / Feature / Execution の層で整理されています。外部キーやインデックスは実運用での参照パターン（銘柄×日付スキャン、ステータス検索など）を想定して定義しています。
- .env パーサーはシェル風の引用・エスケープ・コメントをかなり忠実に扱いますが、複雑なケースは `.env` の書式に注意してください。
- 自動ロードの対象となるプロジェクトルートは、`config.py` の実装により `.git` または `pyproject.toml` を親ディレクトリに持つ場所を探します。パッケージ配布後もカレントワーキングディレクトリに依存しないよう設計しています。
- 実際の売買ロジック（API 経由の注文送信、約定処理、リスク管理、Slack 通知等）は strategy / execution / monitoring モジュールに実装してください。

---

ご不明点や README に追加したい具体的な使用例（戦略のテンプレート、マイグレーション手順、CI 設定など）があれば教えてください。README を拡張して例やコマンドを追加します。