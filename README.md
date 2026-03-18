# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API や RSS フィードから市場データやニュースを収集し、DuckDB を用いて冪等に保存・品質チェック・ETL を行うことを目的としています。戦略や発注実装のための土台（データ層、監査ログ、実行レイヤ）を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レートリミット（120 req/min）対応、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を回避
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を取得して前処理（URL除去、空白正規化）し DuckDB に保存
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を使用して冪等性を保証
  - SSRF / XML Bomb 等の安全対策（スキーム検査、プライベートIPチェック、defusedxml、最大受信バイト数制限）

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution（監査）レイヤを含むスキーマ
  - インデックス定義、監査ログテーブル（注文/約定のトレーサビリティ）を提供

- ETL パイプライン
  - 差分更新（最終取得日時から未取得分のみ）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行

- カレンダー管理
  - JPX カレンダー取得 / 営業日判定 / next/prev_trading_day 等のユーティリティ

---

## 必要な環境変数

KabuSys は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を読み込みます。必須の環境変数は以下の通りです。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack の通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API の基底 URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

制御用:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動で .env を読み込む処理を無効化（テストなどで使用）

自動ロード仕様:
- プロジェクトルートは __file__ の親階層から `.git` または `pyproject.toml` を探索して決定し、そのルートの `.env` → `.env.local` の順に読み込みます（OS 環境変数が優先されます）。

---

## セットアップ手順（開発環境向け）

1. Python 仮想環境を作成・有効化（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は主要依存をインストールしてください:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

3. リポジトリを開発モードでインストール（オプション）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` ファイルを作成するか、必要な環境変数を OS 環境に設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（コード例）

以下は DuckDB スキーマ初期化と日次 ETL 実行の簡単な例です。

- データベースの初期化（DuckDB スキーマ作成）:

```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリが無ければ自動生成）
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行（市場カレンダー・株価・財務を取得し品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡して特定日で実行可能
print(result.to_dict())
```

- ニュース収集ジョブの実行例:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes はスクレイピング・銘柄抽出に使う有効銘柄コードの set
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 監査スキーマ（注文/約定）を追加したいとき:

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意:
- J-Quants 呼び出しはトークン取得 / リフレッシュが必要です。settings.jquants_refresh_token に値を設定してください（環境変数）。
- ネットワーク呼び出しはレート制限とリトライ制御が組み込まれていますが、運用時にはログ監視を推奨します。

---

## 主なモジュールと機能一覧

- kabusys.config
  - 環境変数の読み込みと管理（.env/.env.local 自動ロード）
  - Settings オブジェクト経由で設定にアクセス

- kabusys.data.jquants_client
  - J-Quants API クライアント（fetch_* / save_* 関数）
  - レートリミット管理、リトライ、トークン自動リフレッシュ

- kabusys.data.news_collector
  - RSS 取得、前処理、DuckDB への保存、銘柄抽出・紐付け
  - SSRF・XML 攻撃対策、受信サイズ制限

- kabusys.data.schema
  - DuckDB スキーマの DDL と初期化関数（init_schema / get_connection）

- kabusys.data.pipeline
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分更新、バックフィル、品質チェック呼び出し

- kabusys.data.calendar_management
  - market_calendar 更新ロジックと営業日判定ユーティリティ（is_trading_day, next_trading_day 等）

- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）スキーマの初期化

- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略・発注・監視関連のプレースホルダ（各種実装箇所）

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      - (戦略実装を配置)
    - execution/
      - __init__.py
      - (発注・ブローカー連携を配置)
    - monitoring/
      - __init__.py
      - (監視・アラート関連を配置)

この README に記載のサンプル API や関数は上記モジュールに実装されています。

---

## 運用上の注意点

- 環境変数・シークレットの管理は安全に行ってください（.env をリポジトリにコミットしない）。
- DuckDB はファイルベース DB のため、運用時はバックアップ・排他アクセス設計に注意してください。
- J-Quants のレート制限（120 req/min）を尊重すること。ライブラリは基本的な制御を行いますが、大量バッチ実行時は注意が必要です。
- ニュース収集や外部 URL 取得では SSRF・圧縮爆弾・XML 攻撃等に対策をしていますが、運用環境での追加監査・制限（プロキシ、ネットワーク ACL 等）を推奨します。

---

## 付録: よく使う関数（要約）

- data.schema.init_schema(db_path)
  - DuckDB スキーマ初期化、接続を返す

- data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL を実行して ETLResult を返す

- data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から日足を取得

- data.jquants_client.save_daily_quotes(conn, records)
  - raw_prices テーブルへ冪等保存

- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - RSS 全取得 → raw_news 保存 → news_symbols 紐付け

- data.audit.init_audit_schema(conn, transactional=False)
  - 監査ログ用テーブルを初期化

---

README 以外のドキュメント（DataPlatform.md, DataSchema.md 等）が参照される設計コメントがコード内にあります。実運用や拡張の際はそれら設計ドキュメントに従って実装を追加してください。質問や追加したい項目があれば教えてください。