# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
データ収集（J-Quants）、品質チェック、特徴量計算、ニュース NLP、LLM を用いた市場レジーム判定、監査ログ管理などを含む一連のコンポーネントを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（関数内で datetime.today()/date.today() を不用意に使わない）
- DuckDB を中心としたローカルデータレイクでの idempotent 保存
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- テストしやすい（依存注入／モックしやすい設計）


目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成
- 環境変数一覧 / .env 例
- 注意事項 / 設計上のポイント


## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含みます：
- データ収集（J-Quants API から株価・財務・市場カレンダー・上場情報を取得）
- ETL（差分取得、保存、品質チェック）
- ニュース収集（RSS → raw_news）と NLP による銘柄別センチメントスコア算出（OpenAI）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ（signal / order_request / execution）用スキーマの初期化ユーティリティ


## 機能一覧

- data/jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
  - レートリミッタ、リトライ、401 時のトークン自動リフレッシュ実装

- data/pipeline（ETL）
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult による実行結果収集・品質チェック統合

- data/quality
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
  - QualityIssue オブジェクトで問題を返却

- data/news_collector
  - RSS 取得・前処理・記事ID 作成（URL 正規化 + SHA256）
  - SSRF 対策、gzip サイズチェック、XML パースに対する安全対策

- data/calendar_management
  - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job

- data/audit
  - 監査テーブル DDL（signal_events / order_requests / executions）と初期化関数 init_audit_schema / init_audit_db

- data/stats
  - zscore_normalize（クロスセクション Z スコア）

- ai/news_nlp
  - calc_news_window, score_news: ニュースを銘柄別に集約して LLM に投げ、ai_scores に保存

- ai/regime_detector
  - ETF (1321) の 200 日 MA 乖離とマクロニュース LLM センチメントを合成して市場レジーム判定（bull/neutral/bear）を market_regime に保存

- research
  - calc_momentum, calc_volatility, calc_value（ファクター群）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量評価 / 研究用）


## セットアップ手順

以下はローカル開発環境向けの手順例です。

1. Python 仮想環境の作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   必要な主なパッケージ（バージョンは適宜調整してください）:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （本プロジェクト配下に pyproject.toml / requirements.txt があればそちらからインストールしてください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env, .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 必要な環境変数は次節「環境変数一覧」を参照してください。

5. DuckDB・監査 DB 初期化（例）
   - Python REPL やスクリプト内で data.audit.init_audit_db("/path/to/kabusys_audit.duckdb") を呼び出して監査 DB を初期化します。


## 使い方（主要 API の例）

以下は基本的な呼び出し例です。全て DuckDB 接続には `duckdb.connect(path)` で得た接続を渡します。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- ETL（日次パイプライン）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア算出（ai/news_nlp）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（ai/regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  ```

- 監査テーブル初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

注意：
- OpenAI API 呼び出しは api_key を引数で渡すか環境変数 OPENAI_API_KEY を利用してください。
- ETL/LLM 呼び出しはネットワークや API エラー時にフェイルセーフ（多くはスキップして継続する）処理が入っていますが、実運用ではログ監視・再実行戦略を設計してください。


## ディレクトリ構成

この README は src/kabusys 以下の構成に基づいています。主要ファイル／モジュールは以下の通りです：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news 等）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理、営業日判定
    - stats.py               — zscore_normalize 等汎用統計
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（上記は主要ファイルの抜粋です。実際のパッケージにはさらに細分化されたコードやユーティリティが含まれます。）


## 環境変数一覧（主要）

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN — Slack 通知等で使用する場合
- SLACK_CHANNEL_ID — Slack チャネル ID

kabu ステーション関連：
- KABU_API_PASSWORD — kabu API のパスワード
- KABU_API_BASE_URL  — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

データベースパス：
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite を使うモジュールがあればその DB パス（デフォルト: data/monitoring.db）

システム：
- KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

自動 .env 読み込み：
- プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します）。

簡易 .env 例（.env.example）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 注意事項 / 設計上のポイント

- Look-ahead bias：多くの関数（score_news, score_regime, ETL 等）は target_date で明示的に日付を受け取り、内部で現在時刻を参照しないよう設計されています。バックテスト用途においては「いつそのデータを知り得たか」を明確に扱ってください。
- 冪等性：J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE によって保存されるため再実行が安全です。ETL は backfill を用いて API 側の後出し修正を取り込みます。
- LLM（OpenAI）呼び出し：429/タイムアウト/ネットワークエラー/5xx に対するリトライや JSON バリデーションを実装しています。API のコスト・遅延に留意してください。
- セキュリティ：news_collector は SSRF 対策（リダイレクト先の検査、プライベート IP 拒否等）や defusedxml を利用した安全な XML パースを行います。
- DuckDB バージョン差異：コード中に DuckDB バージョン互換性を考慮した実装（executemany の空リスト制約回避など）があります。DuckDB のバージョンに依存する挙動には注意してください。

---

不明点や README に追加したい操作（例：デプロイ手順、CI 設定、より詳細な .env.example）の要望があれば教えてください。必要に応じて README を拡張します。