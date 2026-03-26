# KabuSys

バージョン: 0.1.0

日本株向けのデータ基盤・リサーチ・AI を組み合わせた自動売買補助ライブラリ。J-Quants / JQ API からのデータ ETL、ニュースの NLP スコアリング（OpenAI 利用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ管理など、アルゴリズムトレーディングのコア機能群を提供します。

---

## 概要

KabuSys は以下の目的に設計されています。

- J-Quants API を使った株価・財務・カレンダー等の差分 ETL パイプライン
- RSS ニュース収集と OpenAI を使った銘柄別センチメント（ai_score）算出
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- ファクター（モメンタム / バリュー / ボラティリティ等）計算と特徴量探索（IC・forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス回避（target_date を明示し、datetime.today() を内部処理で参照しない）
- DuckDB ベースのデータ操作（SQL + Python）
- OpenAI（gpt-4o-mini 等）の JSON mode を利用した堅牢な API 呼び出しとリトライ処理
- 冪等（idempotent）保存を前提とする ETL / 保存ロジック

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・raw_news 保存）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news: 銘柄ごとに ai_scores を生成）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースセンチメント合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数 / .env ロードと検証（Settings オブジェクト経由で設定取得）
- audit
  - 監査ログ用 DDL とインデックス定義／初期化

---

## 前提条件（Prerequisites）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai（OpenAI の Python SDK。v1 系の API を想定）
  - defusedxml
  - （標準ライブラリ以外に追加が必要な場合は pyproject.toml / requirements.txt を参照）

環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH — デフォルトの DuckDB 保存先（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)

自動 .env ロード:
- パッケージはプロジェクトルート（.git か pyproject.toml）を探索し、.env / .env.local を自動読み込みします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements / pyproject.toml があればそれを使ってインストール:
     - pip install -e .  （ローカル編集を反映したい場合）

4. 環境変数の準備
   - プロジェクトルートに .env を作成（.env.example を参考にしてください）
   - 例（最低限）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
   - 注意: .env.local は .env を上書きするため、ローカル専用設定は .env.local に置くと便利です。

---

## 使い方（基本例）

以下はライブラリの主なユースケースの簡単な使用例です。Python スクリプトや REPL から利用できます。

1) DuckDB 接続と ETL 実行（日次 ETL）
- 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュース NLP スコアリング（OpenAI を利用）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

3) 市場レジーム判定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB 初期化
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って order_requests / executions 等を記録可能

5) データ品質チェックの実行
- 例:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

6) 市場カレンダーの判定
- 例:
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,20))

注意点:
- score_news / score_regime は OpenAI API キーを要します（引数 api_key を渡すか、環境変数 OPENAI_API_KEY を設定）。
- run_daily_etl は J-Quants の認証（JQUANTS_REFRESH_TOKEN）を前提とします。

---

## よく使う関数一覧（抜粋）

- ETL / data
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)
  - kabusys.data.jquants_client.get_id_token(...)

- AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Research
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_forward_returns(conn, target_date)

- Data quality / calendar / audit
  - kabusys.data.quality.run_all_checks(conn, target_date)
  - kabusys.data.calendar_management.calendar_update_job(conn)
  - kabusys.data.audit.init_audit_db(path)

- 設定
  - kabusys.config.settings — 環境変数から安全に設定値を取得

---

## ディレクトリ構成

主要なファイル／モジュール構成（src/kabusys）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            -- ニュース NLP（score_news, calc_news_window など）
  - regime_detector.py     -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py -- カレンダー/営業日ロジック
  - etl.py                 -- ETL インターフェース再公開
  - pipeline.py            -- ETL パイプライン実装（run_daily_etl 等）
  - stats.py               -- 統計ユーティリティ（zscore_normalize）
  - quality.py             -- データ品質チェック
  - audit.py               -- 監査ログスキーマ定義 / 初期化
  - jquants_client.py      -- J-Quants API クライアント（fetch/save）
  - news_collector.py      -- RSS ニュース収集ユーティリティ
- research/
  - __init__.py
  - factor_research.py     -- ファクター計算（momentum / value / volatility）
  - feature_exploration.py -- 将来リターン / IC / 統計サマリー 等

---

## 開発上の注意・設計方針（抜粋）

- ルックアヘッドバイアスを避けるため、日付に関する関数は常に target_date 引数を取るか、外部から渡す設計です。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE / INSERT ... DO UPDATE）を採用。
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ処理を持ち、フェイルセーフ（API 失敗時はゼロ補正やスキップして継続）を基本方針としています。
- DuckDB のバージョン差異（executemany の空リスト等）にも注意した実装になっています。

---

## サポート／拡張

- OpenAI モデルやマクロキーワード、ウィンドウ長などのパラメータは ai/*.py の定数で管理されています。必要に応じて調整してください。
- ニュースソースの追加は data/news_collector.DEFAULT_RSS_SOURCES を編集してください。
- ETL の ID トークン注入（id_token 引数）はテスト容易性のために残されています。ユニットテスト作成時はトークンや API 呼び出しをモックしてください。

---

もし README に加えたいサンプルスクリプトや、CI / デプロイ手順、あるいは .env.example の具体的なテンプレートが必要であれば教えてください。必要に応じて追記例を作成します。