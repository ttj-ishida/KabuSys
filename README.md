# KabuSys

日本株向け自動売買 / データ基盤ライブラリ

---

目次
- プロジェクト概要
- 主な機能
- セットアップ
- 環境変数（.env）と設定
- 使い方（簡易コード例）
- ディレクトリ構成
- 注意事項 / 設計方針（概要）

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ収集・ETL・品質チェック・監査ログ・発注管理の基盤モジュール群です。J-Quants API からの株価・財務・マーケットカレンダー取得、RSS ベースのニュース収集、DuckDB を用いたスキーマ管理および日次 ETL パイプライン、品質チェック、監査テーブルの初期化などを提供します。

設計上の特徴：
- J-Quants API のレート制限遵守（120 req/min）およびリトライ/トークン自動更新に対応
- DuckDB を中心とした三層（Raw / Processed / Feature）スキーマ設計
- ニュース収集における SSRF / XML 攻撃 / Gzip bomb 対策
- ETL の冪等性（ON CONFLICT を利用）と差分更新ロジック
- 品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までトレース可能な監査ログ

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット管理、リトライ、id_token 自動更新
  - DuckDB への安全な保存（冪等性）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）
  - バックフィル設定（後出し修正吸収）
  - 日次 ETL 実行エントリ（run_daily_etl）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト取得
  - 夜間バッチ（calendar_update_job）

- ニュース収集（RSS）
  - RSS 取得・パース・テキスト前処理
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF、XML／Gzip 攻撃対策
  - raw_news / news_symbols への冪等保存

- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合検出
  - QualityIssue データ構造で結果返却

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル群
  - UTC タイムスタンプ、冪等キー (order_request_id)、インデックス

---

## セットアップ

前提
- Python 3.10+（typing の | 型や一部記法を使用）
- git 等の開発環境（.env 自動ロードはプロジェクトルートを .git または pyproject.toml で検出します）

基本インストール例：

1. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がない場合は主要依存を個別インストールしてください:
   ```
   pip install duckdb defusedxml
   ```
   - パッケージ化されていればソースからセットアップ（開発モード）:
   ```
   pip install -e .
   ```

3. データベース初期化（DuckDB）
   - デフォルトの保存先は `data/kabusys.duckdb`（Settings により変更可能）
   - Python REPL やスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

4. 監査ログテーブルの初期化（必要に応じて）
   ```python
   from kabusys.data import audit
   # 既存の DuckDB 接続を渡す
   audit.init_audit_schema(conn)
   # または専用 DB を作る場合
   # audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 環境変数（.env）と設定

Settings は環境変数から読み込まれます。パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で自動読み込みを行います（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env のパースはシェル風のフォーマットに柔軟に対応しています（export プレフィックス、クォート、インラインコメントなど）。

---

## 使い方（簡易コード例）

基本的なワークフローの例をいくつか示します。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

# conn は上の init_schema で取得した接続または schema.get_connection()
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（抽出に使う）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

4) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) 監査ログ初期化（追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

6) Settings の利用例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## ディレクトリ構成（主要ファイル）

リポジトリのコード例に基づく主要構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py      -- RSS ニュース収集・保存
    - schema.py              -- DuckDB スキーマ定義 / init
    - pipeline.py            -- ETL パイプライン（差分取得、run_daily_etl）
    - calendar_management.py -- カレンダー管理 / 営業日ロジック
    - audit.py               -- 監査ログ定義 / 初期化
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略層（拡張用）
  - execution/
    - __init__.py            -- 発注実行層（拡張用）
  - monitoring/
    - __init__.py            -- 監視用モジュール（拡張用）

---

## 注意事項 / 設計方針（要点）

- API 利用制限（J-Quants）を守るため、モジュールは内部的に固定間隔のレートリミッターを持っています。
- トークンの有効期限切れ時には自動リフレッシュを試みます（401 を受けた場合、1 回のみ再取得して再試行）。
- DB 保存は可能な限り冪等性を担保（ON CONFLICT DO UPDATE／DO NOTHING）して二重挿入を防止します。
- ニュース収集では SSRF / XML Bomb / Gzip Bomb 対策が組み込まれています。外部 URL のスキームやホスト判定を厳格に行います。
- カレンダーが存在しない場合は土日ベースでフォールバックする等、堅牢なフォールバックロジックを持ちます。
- 品質チェックは Fail-Fast ではなく、検出された問題をすべて集めて呼び出し元に返却します（呼び出し側で決定）。

---

もし README に追記したい具体的な実行例（cron / systemd / Dockerfile / GitHub Actions のサンプル）や、想定する戦略実装のテンプレート、依存パッケージの厳密なバージョン情報があれば教えてください。README をそれに合わせて拡張します。