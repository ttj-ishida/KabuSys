# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（主要な設定項目）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本市場向けのデータプラットフォーム兼リサーチ／自動売買基盤の一部を切り出した Python パッケージです。  
主に以下用途を想定しています。

- J-Quants API からの株価・財務・カレンダーなどの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と記事の前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）MA 等を用いた市場レジーム判定
- ファクター計算（モメンタム/ボラティリティ/バリュー等）および基礎統計・IC 計算
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ用テーブル定義と初期化）

設計上の特徴:
- ルックアヘッドバイアスを避ける実装（内部で date.today()/datetime.today() を直接使わない等）
- DuckDB をデータ格納に使用（軽量かつ SQL ベース）
- 冪等（idempotent）設計：ETL 保存は ON CONFLICT で更新
- API 呼び出しに対するリトライ／バックオフ、レート制御を実装

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証トークン管理、レート制御）
  - news_collector（RSS 取得、前処理、SSRF 対策、記事ID生成）
  - calendar_management（営業日判定、next/prev_trading_day、calendar_update_job）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログ用テーブル定義・初期化）
  - stats（Z スコア正規化）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントの取得と ai_scores への書き込み）
  - regime_detector.score_regime（ETF MA + マクロLLM を合成した market_regime 判定）
- research/
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数・設定のロード（自動 .env ロード機能、Settings クラス）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントのユニオン等の構文を使用）
- DuckDB を利用（パッケージに含まれる duckdb モジュール）
- OpenAI SDK（openai）、defusedxml などが必要

1. リポジトリをクローン / コピー
   - 例: git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 以下は最低限の例（実プロジェクトでは requirements.txt を参照してください）:
     - pip install duckdb openai defusedxml

   実際に使う機能に応じて追加パッケージが必要になる場合があります（例: slack 通知など）。

4. 環境変数 (.env) の準備
   - プロジェクトルートに .env（または .env.local）を配置すると自動で読み込まれます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数や推奨値は次のセクション「環境変数」を参照してください。

5. DuckDB データベース初期化（監査テーブル等）
   - 監査ログ用 DB を初期化する例:
     - python -c "import duckdb; from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 環境変数（主要な設定項目）

KabuSys は .env ファイルまたは OS 環境変数を参照します。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探して行います。

主要なキー:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI の API キー。ai.score_news / regime_detector で使用（関数引数で上書き可能）。

- KABU_API_PASSWORD (必須 if kabu ステーション連携)
  - kabu ステーション API パスワード。

- KABU_API_BASE_URL (任意)
  - kabu API の base URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意)
  - Slack 通知に使用。

- DUCKDB_PATH (任意)
  - デフォルト DuckDB ファイルパス: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - モニタリング用途の SQLite パス: data/monitoring.db

- KABUSYS_ENV (任意)
  - 開発環境区分: development / paper_trading / live
  - デフォルト: development

- LOG_LEVEL (任意)
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - デフォルト: INFO

設定ファイルの自動ロードを無効にするには:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡易サンプル）

以下は代表的なユースケースの簡単なコード例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って ETL を実行する（日次 ETL）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を評価して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み件数:", n_written)

- 市場レジーム判定を実行する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算・研究ユーティリティの呼び出し:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))

- 監査ログテーブルの初期化（推奨: 起動時に一度だけ）:

  from kabusys.data.audit import init_audit_db
  init_audit_db("data/audit.duckdb")

注意:
- AI 系関数（score_news, score_regime）は OPENAI_API_KEY または引数 api_key が必要です。
- J-Quants API を呼ぶ ETL は JQUANTS_REFRESH_TOKEN を必要とします（get_id_token 経由で id_token を取得）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    -- 環境変数 / Settings クラス、.env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py                -- ニュースセンチメント（銘柄別）
  - regime_detector.py         -- ETF MA + マクロ LLM で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py          -- J-Quants API クライアント（fetch/save）
  - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
  - etl.py                     -- ETLResult 再エクスポート
  - news_collector.py          -- RSS 収集・前処理・SSRF 対策
  - calendar_management.py     -- 市場カレンダー管理、営業日判定、更新ジョブ
  - quality.py                 -- データ品質チェック
  - stats.py                   -- 統計ユーティリティ（zscore_normalize）
  - audit.py                   -- 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py         -- モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py     -- forward returns / IC / summary / rank

README.md（このファイル）

---

## 備考 / 実運用上の注意

- セキュリティ:
  - news_collector は SSRF 対策や XML 攻撃対策（defusedxml）を組み込んでいますが、運用環境ではネットワークポリシーやプロキシ設定も考慮してください。
  - API キーやパスワードは .env やシークレットマネージャで安全に管理してください。

- 冪等性:
  - ETL 保存関数は ON CONFLICT を使っているため複数回実行しても上書き（更新）されます。ただし部分失敗時の取り扱いはログや ETLResult を確認してください。

- テスト:
  - OpenAI / ネットワーク呼び出し部分はモック可能な設計（内部呼び出しを差し替え可能）になっています。運用前にユニットテストや統合テストを用意してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細な API 使用例（ETL スケジュール、Airflow / cron の組み方）、あるいは運用手順（バックアップ、監査ログの運用）などを追加で作成します。どの部分を詳しく書いてほしいか教えてください。