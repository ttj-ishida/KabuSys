# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

本プロジェクトはデータ取得（J-Quants）、ニュース収集・NLP、ファクター計算、ETLパイプライン、監査ログ（約定トレーサビリティ）などを含む日本株向けのバックエンドコンポーネント群です。バックテスト / リサーチ / 実運用（paper/live）を想定した設計とフェイルセーフ、ルックアヘッドバイアス回避を重視しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python モジュール群です。

- J-Quants API を使った株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータ格納・冪等保存（ON CONFLICT）
- ニュース収集（RSS）と前処理（SSRF 対策・コンテンツ正規化）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジーム判定（JSON Mode を前提）
- ETLパイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算・IC、Zスコア正規化 等）

設計上のポイント:
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない等）
- フェイルセーフ（外部API失敗時に局所的に0やNoneでフォールバック）
- 冪等性（DB書き込みは ON CONFLICT / idempotent を意識）

---

## 機能一覧（主要 API）

- 環境・設定:
  - kabusys.config.settings（.env の自動ロード、環境変数アクセス）
- データ取得 / ETL:
  - kabusys.data.jquants_client
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - get_id_token（J-Quants トークン取得）
  - kabusys.data.pipeline
    - run_daily_etl（市場カレンダー、株価、財務の差分ETL + 品質チェック）
- ニュース関連:
  - kabusys.data.news_collector.fetch_rss（RSS 取得・正規化）
  - kabusys.ai.news_nlp.score_news（銘柄ごとのニュースセンチメントを ai_scores テーブルへ）
  - kabusys.ai.regime_detector.score_regime（ETF 1321 の MA とマクロニュースを合成して market_regime に保存）
- 研究用:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
  - data.stats.zscore_normalize
- 品質・カレンダー・監査:
  - kabusys.data.quality.run_all_checks（欠損・スパイク・重複・日付不整合検出）
  - kabusys.data.calendar_management.{is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job}
  - kabusys.data.audit.init_audit_db / init_audit_schema（監査テーブル初期化）

---

## セットアップ手順

前提:
- Python 3.10+（typing の | 記法や型ヒントを使用）
- DuckDB を使います（duckdb パッケージ）
- OpenAI API を使う機能は openai ライブラリを使用
- defusedxml をニュース XML パースで利用

1. リポジトリをチェックアウト
   - git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .\.venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - または開発時:
     - pip install duckdb openai defusedxml

   （プロジェクトに packaging がある場合は pip install -e .）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込み順: OS > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース初期化（例: 監査DB）
   - Python REPL / スクリプトで:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")
     ```
   - Schema を既存の接続へ追加する場合:
     ```python
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     audit.init_audit_schema(conn, transactional=True)
     ```

---

## 簡単な使い方（コード例）

環境変数（OpenAI / J-Quants 等）を設定した上で、DuckDB 接続を使って ETL や NLP を実行します。

- ETL（日次パイプライン）を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（特定日）を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("wrote", n_written)
  ```

- 市場レジーム判定（例: 1321 を用いる）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB初期化（インメモリ例）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db(":memory:")
  ```

注意:
- OpenAI 呼び出しはモデル gpt-4o-mini を想定しており、JSON mode のレスポンスを期待します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API は JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token で参照）。

---

## 環境変数（主要）

以下はプロジェクトが参照する主な環境変数です。`.env` またはシステム環境変数で設定してください。

- JQUANTS_REFRESH_TOKEN — 必須。J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABU_API_BASE_URL — 任意。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN — 必須（Slack 通知を使う場合）
- SLACK_CHANNEL_ID — 必須（Slack 通知を使う場合）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — {"development","paper_trading","live"} のいずれか（デフォルト: development）
- LOG_LEVEL — {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env ロードを無効化

サンプル .env 内容（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意点 / 運用メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しや J-Quants API 呼び出しはリトライ・バックオフやフェイルセーフが備わっていますが、API料金やレート制限の考慮は運用側で行ってください。
- ETL は差分取得・バックフィルを行うので、初回は長い時間が掛かる場合があります。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、内部で空チェックが行われています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み・settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants HTTP クライアント / DuckDB 保存
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集・正規化
  - calendar_management.py — 市場カレンダー管理
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize 等
  - audit.py — 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility 等
  - feature_exploration.py — forward returns, IC, summary, rank

その他:
- README.md（本ファイル）
- .env.example（プロジェクトルートに用意することを推奨）

---

もし README に追加したい内容（例: dev 環境の Docker 化手順、CI 設定、より詳細な API 仕様やスキーマ定義のドキュメント）があれば教えてください。必要に応じてサンプル .env.example や初期 SQL スキーマ、問い合わせ用のユーティリティスクリプト例も作成します。