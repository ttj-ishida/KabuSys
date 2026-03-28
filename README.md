# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムおよびリサーチ基盤向けのモジュール群を含みます。主に以下の役割を担います。

- J-Quants API からの株価・財務・カレンダー等の ETL
- RSS ニュース収集と前処理（SSRF / XML 攻撃対策を含む）
- OpenAI（GPT 系）を使ったニュースセンチメントスコアリング（銘柄別）とマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用 DuckDB スキーマ

設計上の共通方針として、Look-ahead バイアスの回避、冪等（idempotent）な DB 保存、外部 API のリトライ・レート制御、そして失敗時にシステム全体を止めないフェイルセーフな挙動を重視しています。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート検出）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - 差分取得・ページネーション対応・ID トークン自動リフレッシュ・レート制御
  - DuckDB への冪等保存（ON CONFLICT）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev/trading days、calendar 更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 防御、gzip 対応
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を使った銘柄別センチメントスコアリング（JSON mode、バッチ処理、リトライ）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントの合成判定
- ファクター計算・解析（kabusys.research）
  - モメンタム / バリュー / ボラティリティ / 将来リターン / IC / 統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ初期化・管理（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションで `|` を使用）
- Git リポジトリをクローン済み（.git をプロジェクトルート検出に使用）

1. 仮想環境作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install -e .  （プロジェクトをパッケージとして編集可能インストール）
   - 直接インストールする場合の主要依存例:
     - duckdb
     - openai
     - defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数の設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置すると、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - OPENAI_API_KEY=<your_openai_api_key>  （AI モジュールで使用）
   - KABU_API_PASSWORD=<kabu_station_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>

   その他（任意デフォルトあり）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env ロードを無効化）
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト data/monitoring.db)
   - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）

   .env のサンプル（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB（監査ログ等）初期化（任意）
   - Python から初期化する例:
     ```py
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存接続に対してスキーマのみ適用:
     ```py
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（簡単な例）

以下は主要ユースケースのサンプルコード例です。実行は仮想環境内で行ってください。

- 日次 ETL を実行する（J-Quants からデータ取得→保存→品質チェック）
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを計算して ai_scores に書き込む
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行する
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（モメンタム等）
  ```py
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 環境設定の取得
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 主要 API（一覧）

- kabusys.config.Settings
  - settings.jquants_refresh_token, settings.env, settings.log_level など

- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult（結果オブジェクト）

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token

- kabusys.data.news_collector
  - fetch_rss, preprocess_text（RSS 取得と前処理ユーティリティ）

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False), init_audit_db(db_path)

---

## ディレクトリ構成

主要ファイル・モジュールを抜粋した構成例:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - etl.py (再エクスポートなど)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/         (READMEでの説明用に存在を想定、監視系コード)
    - strategy/           (戦略・シグナル生成のためのモジュールを想定)
    - execution/          (注文送信・約定処理のためのモジュールを想定)

実際のリポジトリではさらにユーティリティやテスト、CLI スクリプト等が含まれる場合があります。

---

## 注意点 / 運用メモ

- OpenAI 呼び出し（news_nlp, regime_detector）は API レート・コストが発生します。テストではモック化を推奨します。
- ETL / API クライアントはリトライと指数バックオフ、レート制御を実装していますが、実運用では API 制限に注意してください。
- DuckDB スキーマは一部で ON CONFLICT を使うため、使用する DuckDB のバージョンに依存する振る舞いがあるかもしれません。テスト環境での検証を推奨します。
- 環境変数自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込みます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベースの簡易ガイドです。詳細な設計文書や運用手順（DataPlatform.md, StrategyModel.md 等）が別途あればそちらも参照してください。必要であれば README の拡張（CLI 実行例、デプロイ手順、CI 設定例など）を作成します。