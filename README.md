# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP スコアリング、LLM を用いた市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレース可能な発注／約定ログ）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場情報、JPX マーケットカレンダー取得（pagination 対応、レートリミット遵守、トークン自動リフレッシュ）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）
- ニュース収集・前処理
  - RSS 収集（SSRF 対策、トラッキングパラメータ削除、前処理）と raw_news への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に渡しセンチメントを ai_scores に書き込む（score_news）
  - マクロニュースを使った市場レジーム判定（score_regime）
  - JSON Mode / 再試行・フォールバックロジックを備えた安全な実装
- リサーチ（ファクター計算）
  - Momentum / Value / Volatility / Liquidity などのファクター計算、将来リターン・IC 計算、Z スコア正規化など
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ初期化・監査トレース用ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、環境変数ラッパー（kabusys.config.settings）

---

## 前提条件

- Python 3.10+
- 必要なライブラリ（例、代表的なもの）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリを使用

（プロジェクトに requirements.txt がある場合はそれに従ってください。なければ最低限上記パッケージをインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトのセットアップに setuptools / poetry 等を使っている場合は該当の方法でインストールしてください。）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

5. （オプション）自動ロードの挙動
   - .env が自動的に読み込まれる順序は: OS 環境 > .env.local > .env
   - テスト等で自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単な例）

以下は代表的なユースケースの最小例です。読み替えてご利用ください。

- DuckDB 接続例（デフォルトの DUCKDB_PATH を使用）:
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行（J-Quants からデータを取得して保存）:
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=None)  # target_date None => 今日

  ETLResult オブジェクト（result）から取得数や品質チェック結果を確認できます。

- ニュース NLP（銘柄ごとのスコアを ai_scores テーブルへ書込む）:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.config import settings
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - count = score_news(conn, target_date=datetime.date(2026, 3, 20))  # 例

- 市場レジーム判定（ma200 + マクロニュース LLM を使う）:
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=datetime.date(2026, 3, 20))

- 監査 DB 初期化（監査ログ専用 DB を作る）:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # conn_audit は監査テーブルが初期化された接続

- J-Quants の ID トークン取得（内部で自動利用されますが、手動で取得する場合）:
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使う

注意事項:
- score_news / score_regime 等の OpenAI 呼び出しは OPENAI_API_KEY 環境変数または api_key 引数を必要とします。
- 各処理は「ルックアヘッドバイアス」を避ける設計（target_date を明示、datetime.today() を内部で参照しない等）になっています。

---

## 主要 API（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize (kabusys.data.stats)

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (必要な処理で必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

kabusys.config.Settings クラス経由で型安全に参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - (その他 jquants_client で使用される補助関数群)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research から参照される data.stats などのユーティリティ

（READMEに載せた以外にも細かいモジュールが含まれます。上記は主要コンポーネントの一覧です。）

---

## 開発メモ / 注意点

- DuckDB を用いた設計のため大量データの高速処理が可能です。INSERT は冪等（ON CONFLICT DO UPDATE）で実装されています。
- 外部 API 呼び出し（J-Quants / OpenAI）にはリトライ・バックオフ・フェイルセーフが実装されています。API エラー時はゼロスコアやスキップで継続する設計箇所があるため、ログを確認してください。
- ニュース収集では SSRF 対策や XML の安全パーサ（defusedxml）を使用しています。
- テスト時は設定や外部コールをモックすることを想定した実装（内部 _call_openai_api の差し替えや KABUSYS_DISABLE_AUTO_ENV_LOAD）になっています。

---

もし README に別項目（例: CI / テスト実行手順、開発ルール、サンプル設定ファイル .env.example など）を追加したい場合は、その内容を教えてください。README をさらに詳しく調整します。