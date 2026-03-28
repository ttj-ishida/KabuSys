# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（部分実装）。  
本リポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL・品質チェック、監査ログなどを提供するモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するためのライブラリ群です。主に以下の機能領域をカバーします。

- データ ETL（J-Quants からの株価・財務・カレンダー取得、DuckDB 保存）
- ニュース収集（RSS）と NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF 指標 × マクロニュース）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計上の重要ポイント:
- ルックアヘッドバイアスを避けるため、関数は date を明示的に受け取り内部で現在時刻を参照しない設計が多く採用されています。
- DuckDB を主要なローカル DB として使用。
- OpenAI（gpt-4o-mini）を JSON mode で呼び出して NLP を行う設計。
- .env ファイルの自動読み込み機能を持つ（プロジェクトルート検出ベース）。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_* 系関数
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss, 前処理、SSRF 対策、トラッキングパラメータ除去
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP: score_news（銘柄ごとの AI スコア算出）
  - レジーム判定: score_regime（ETF MA200 乖離とマクロセンチメント合成）
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提条件・依存パッケージ（代表例）

- Python 3.10+ 推奨（型ヒントに union 型などを使用）
- 必要な Python パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで賄える部分が多いですが、上記は必須想定です。

（実際の requirements.txt はプロジェクトに合わせて追加してください）

---

## 環境変数（主なもの）

config.py によって .env/.env.local を自動読み込みします（プロジェクトルート上の .git または pyproject.toml を検出してルートを決定）。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（data.jquants_client.get_id_token で使用）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector が使用。関数に api_key を直接渡すことも可能）
- （監視・通知などに）KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が設定されるコードパスあり

任意/デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

自動読み込みを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の読み方のポイント:
- .env がまず読み込まれ、.env.local は上書き（override=True）されます。
- OS 環境変数は保護され .env が上書きしません（ただし .env.local は override=True で OS 環境変数で保護されたキーを上書きしません）。

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   - git clone <repo> && cd <repo>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . 等を利用してください。

4. .env を準備
   - リポジトリルートに .env を作成（.env.example を参照）
   - 必要な環境変数（上記参照）を設定

5. DuckDB の準備（例）
   - デフォルト path は data/kabusys.duckdb
   - 監査ログ用 DB を初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主なサンプル）

以下は対話的に Python から呼び出す例です。日付はテスト・バックテスト目的で明示的に渡します（内部で date.today() を盲目的に使わない設計の関数が多いです）。

1) DuckDB 接続の作成:
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL の実行:
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

3) ニュース NLP スコア生成:
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数 OPENAI_API_KEY を使用

4) 市場レジーム評価:
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) ファクター計算（研究用）:
- from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
- mom = calc_momentum(conn, target_date=date(2026, 3, 20))
- vol = calc_volatility(conn, target_date=date(2026, 3, 20))
- val = calc_value(conn, target_date=date(2026, 3, 20))
- normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

6) J-Quants 直接操作（テストや ETL の一部で利用）:
- from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
- token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
- quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

7) RSS フィード取得（ニュース収集の一部）:
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点:
- OpenAI 呼び出しは API レートや課金に影響するため、テストではモック化することを推奨します（コード内でも unittest.mock.patch で差し替え可能になっています）。
- ETL 実行時は J-Quants の API レート制限・認証に注意してください。jquants_client は内部で rate limiter / トークン自動更新を実装しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。代表的なファイルを示します。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は抜粋です。細かいユーティリティや追加モジュールが含まれます）

---

## 実運用上の注意・ベストプラクティス

- 環境変数の取り扱いは慎重に。APIキーは CI/CD やジョブランナーの Secret 機能で安全に管理してください。
- OpenAI 呼び出しは失敗時の挙動（フォールバックスコア等）をコード側で考慮していますが、API のレートやコストを監視してください。
- ETL / API 呼び出し部分はネットワーク障害や API 変更に備えてログを十分に残すこと。
- テストでは外部 API 呼び出しをモック化して deterministic なテストを行ってください（コード内にモック用フックが用意されています）。
- DuckDB のバージョン差異に依存する箇所（一部 executemany の挙動など）があるため、本番環境では使用バージョンを固定してください。

---

README はここまでです。より詳しい API ドキュメントや実運用手順（CI/CD、ジョブスケジューラ、監視設定、スキーマ定義など）が必要であれば、目的に応じて追加で作成します。どういった追加情報が欲しいか教えてください。