# KabuSys — 日本株自動売買システム（README）

この README はリポジトリ内のコードベース（src/kabusys）に基づいて作成した概要ドキュメントです。プロジェクトの目的、主要機能、セットアップ手順、使い方の例、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、研究（リサーチ）機能、AI を使ったニュースセンチメント評価、監査ログ（トレーサビリティ）、および市場カレンダー管理を備えた自動売買／研究プラットフォームの基盤ライブラリです。主に以下用途を想定しています。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の差分取得（ETL）と DuckDB への格納
- ニュース収集（RSS）と LLM（OpenAI）による銘柄レベルのニューススコアリング
- ETF とニュースを組み合わせた「市場レジーム判定」
- ファクター計算・特徴量探索（研究用）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までを追跡する監査ログスキーマの初期化と管理

設計上、バックテストや研究においてルックアヘッドバイアスが生じないよう日付処理やデータ参照に細心の注意が払われています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェックと設定オプション（ログレベル、環境区分など）
- データパイプライン（kabusys.data）
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ（audit）テーブル定義・初期化ユーティリティ
  - 共通統計ユーティリティ（zscore 正規化）
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（銘柄ごとの news score -> ai_scores テーブルへ）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
  - OpenAI 呼び出しは JSON Mode を利用し、リトライとフェイルセーフを実装
- 研究機能（kabusys.research）
  - Momentum / Volatility / Value のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - 例（venv）:
     - python -m venv .venv
     - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

2. 必要な依存パッケージをインストール
   - 本 README では requirements.txt を提供していませんが、主要依存は次のとおりです：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   - 開発中はパッケージを editable インストールすると便利です:
     - pip install -e .

3. 環境変数設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限必要な環境変数（本番利用時）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...（AI 機能を使う場合）
   - 任意（デフォルト値が使われるもの）:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid

   - 例 `.env`（テンプレート）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABU_API_PASSWORD=your_password
     - DUCKDB_PATH=data/kabusys.duckdb

4. データベースディレクトリ作成
   - settings.duckdb_path 等で指定したパスの親ディレクトリを事前に作成しておくと安心です（多くの初期化関数は自動作成するものもあります）。

---

## 使い方（主要な呼び出し例）

以下はライブラリを直接インポートして使う場合の Python スニペット例です。

- 共通設定（settings）
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで値を取得

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング（OpenAI を使用）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
  - print(f"scored {written} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ（audit）テーブル初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - これにより監査関連テーブルが初期化されます

- 市場カレンダーユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading_day(conn, date(2026,3,20))
  - next_trading_day(conn, date(2026,3,20))

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - 各 issue は QualityIssue dataclass（check_name, table, severity, detail, rows）を持ちます

注意点:
- OpenAI API 呼び出し時は rate limit やネットワークエラーを考慮してリトライが組み込まれています。api_key を関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しは settings.jquants_refresh_token を用いて id_token を取得し、内部キャッシュ・自動リフレッシュが行われます。

---

## 主要モジュール / API（抜粋）

- kabusys.config
  - settings: アプリ設定オブジェクト（必須 env の取得、デフォルト値）
- kabusys.data
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client.fetch_* / save_*（J-Quants との通信と DuckDB 保存）
  - news_collector.fetch_rss / preprocess_text（RSS 収集・前処理）
  - calendar_management.is_trading_day / next_trading_day / get_trading_days / calendar_update_job
  - quality.run_all_checks（データ品質チェック）
  - audit.init_audit_schema / init_audit_db（監査テーブル初期化）
  - stats.zscore_normalize（正規化ユーティリティ）
- kabusys.ai
  - news_nlp.score_news（銘柄ニューススコア）
  - regime_detector.score_regime（市場レジーム判定）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・評価）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル群（本 README 作成時点の内容）です。

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター・探索ユーティリティ）

各ファイルはモジュールごとに責務が明確に分かれており、ETL / Data / AI / Research / Audit といった階層で構成されています。

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

config.py によって .env / .env.local がプロジェクトルートから自動的にロードされます（.git または pyproject.toml を起点にルートを検出）。

---

## 備考 / 運用上の注意

- DuckDB を使うため大規模な分析や並列処理の際はメモリとディスク配置に留意してください。
- OpenAI や J-Quants の API キーは安全に管理してください。ログやリポジトリに含めないでください。
- news_collector は SSRF や XML 攻撃対策（defusedxml, ホスト検査, レスポンスサイズ制限など）を組み込んでいますが、公開環境で運用する場合は追加監視・制限を検討してください。
- audit.init_audit_schema は transactional オプションがあり、DuckDB のトランザクション特性に注意が必要です（ネストトランザクション非対応）。

---

この README はコードベースの概要説明です。詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）や運用手順が別途あることを想定しています。必要であれば、特定モジュールの利用例や API リファレンス（関数シグネチャ、戻り値、想定テーブルスキーマ）をさらに作成しますので、どの部分を重点的にドキュメント化するか指示してください。