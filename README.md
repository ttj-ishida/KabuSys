# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ／発注履歴管理、市場カレンダー管理、及び市場レジーム判定などを提供します。

---

## 主要コンセプト / 特長

- DuckDB を中心としたオンプレ／ローカルデータレイヤ（raw_prices / raw_financials / raw_news / market_calendar / ai_scores / audit テーブル等）。
- J-Quants API からの差分 ETL（ページネーション・レート制御・トークン自動更新・冪等保存）。
- ニュース RSS の安全な収集（SSRF 対策、XML 攻撃対策、トラッキングパラメータ除去）。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（銘柄別 ai_score）とマクロセンチメント合成による市場レジーム判定。
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー）・特徴量探索ユーティリティ。
- データ品質チェック（欠損・重複・スパイク・日付不整合）。
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化ユーティリティ。
- 環境変数 / .env 自動読み込みと集中設定（kabusys.config.settings）。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ
  - news_collector: RSS 収集 → raw_news 保存（SSRF/サイズ対策）
  - quality: 品質チェック群（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ（is_trading_day, next_trading_day 等）
  - audit: 監査テーブル定義と初期化（init_audit_schema, init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- ai/
  - news_nlp: 銘柄単位ニュースセンチメント集約（score_news）
  - regime_detector: ETF MA とマクロ LLM を合成した市場レジーム判定（score_regime）
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境設定・.env 自動読み込み（settings オブジェクト）

---

## 要求事項（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai (OpenAI の新 SDK を想定)
- defusedxml
- （標準ライブラリの urllib, json, logging など多数を使用）

※ pyproject.toml / requirements.txt が別途ある想定です。テストや追加のランタイム依存はプロジェクト設定に従ってください。

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <repository-url>
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用: pip install -e . や requirements.txt を使用）
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置できます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 典型的な環境変数（.env に記載する例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL 上での利用例です。日時は date オブジェクトで渡します（内部で date.today() に依存する処理は最小限に留める設計）。

- DuckDB 接続の準備
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行（J-Quants からの差分取得 + 品質チェック）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントスコア生成（銘柄別 ai_scores へ保存）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - # APIキーは OPENAI_API_KEY 環境変数、または api_key 引数で渡す
  - n = score_news(conn, target_date=date(2026,3,20))
  - print(f"書き込み銘柄数: {n}")

- 市場レジーム判定（ETF 1321 とマクロニュースの合成）
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - res = score_regime(conn, target_date=date(2026,3,20))
  - print("OK" if res == 1 else "NG")

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # conn_audit は監査テーブルが初期化された DuckDB 接続

- ファクター計算 / 研究ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - volatility = calc_volatility(conn, target_date=date(2026,3,20))

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading_day(conn, date(2026,3,20))
  - next_trading_day(conn, date(2026,3,20))
  - get_trading_days(conn, date(2026,3,1), date(2026,3,31))

注意:
- OpenAI API 呼び出し系（score_news, score_regime）は API 料金が発生します。api_key を環境変数または引数で安全に渡してください。
- ETL や保存処理は DuckDB のトランザクションを使用します。エラー時はロールバック処理が実装されています。

---

## 設定（kabusys.config.Settings）

settings = kabusys.config.settings でアクセス可能。主なプロパティ:

- jquants_refresh_token: J-Quants のリフレッシュトークン（必須）
- kabu_api_password, kabu_api_base_url: kabuステーション API 関連
- slack_bot_token, slack_channel_id: Slack 通知
- duckdb_path, sqlite_path: データベースファイルパス
- pid_file_path, cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct: 監視設定
- env (KABUSYS_ENV): development / paper_trading / live（検証あり）
- log_level (LOG_LEVEL): DEBUG/INFO/WARNING/ERROR/CRITICAL

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に .env と .env.local を読み込みます。
- OS 環境変数が優先されます。.env.local は .env を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - quality.py
  - stats.py
  - calendar_management.py
  - audit.py
  - (その他モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, execution/, strategy/ など（パッケージ外から参照される想定モジュール名が __all__ に含まれます）

（上記は本リポジトリに含まれる主要なソースファイルを抜粋したものです。実際のツリーはリポジトリルートで確認してください。）

---

## 実運用上の注意 / ベストプラクティス

- APIキーの管理は `.env` や秘密管理ツールを利用し、ソース管理に含めないでください。
- OpenAI 呼び出しは費用とレイテンシを伴うため、バッチ化やキャッシュを検討してください（既にバッチ処理・リトライ・フォールバックが実装されています）。
- DuckDB ファイルは適切にバックアップやファイルローテーションを検討してください（大容量になることがあります）。
- run_daily_etl は部分的に失敗しても他処理を継続する設計です。ETLResult の has_errors / has_quality_errors を監視して運用アラートを出してください。
- テストでは環境自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、テスト専用の一時 DB を使うと再現性が高まります。

---

以上が KabuSys の概要、セットアップ、代表的な使い方、ディレクトリ構成です。  
追加で「インストール用の pyproject.toml / requirements.txt の例」や「具体的な .env.example」を作成したい場合はお知らせください。