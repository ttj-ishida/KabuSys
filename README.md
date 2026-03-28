# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームで必要となる以下の処理を提供します。

- J-Quants API を用いた市場データ（株価、財務、上場銘柄、マーケットカレンダー）の差分取得・保存（DuckDB）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集（RSS）と前処理、LLM（OpenAI）を使ったニュースセンチメントの銘柄別スコア化
- マクロセンチメント＋ETF MA乖離を合成した市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- 発注〜約定までをトレースする監査（audit）スキーマ初期化ユーティリティ
- 環境設定読み込みユーティリティ（.env / 環境変数）

設計上、ルックアヘッドバイアス回避・冪等性・フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得 & DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）の実装（run_daily_etl 等）
  - news_collector: RSS 収集・前処理・raw_news 保存
  - quality: データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログスキーマ生成・監査用 DB 初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルに書込
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数/.env 読み込みロジックと Settings オブジェクト（settings）を提供

---

## 必要条件（依存）

最低限の主要依存例（プロジェクトに requirements.txt を用意してください）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- typing_extensions （環境によって不要）
- （標準ライブラリで賄える部分が多めです）

例（pip インストール）:
pip install duckdb openai defusedxml

※ プロダクション用途ではバージョン固定（requirements.txt / poetry 等）を推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存インストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の主要依存を個別にインストール）

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動的に読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

   最低限必要な環境変数（プロジェクトで参照されるもの）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - KABU_API_PASSWORD=...  # kabuステーション API 用（利用する場合）
   - DUCKDB_PATH=data/kabusys.duckdb  # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db   # 任意（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   サンプル（.env.example）:
   JQUANTS_REFRESH_TOKEN=REPLACE_ME
   OPENAI_API_KEY=REPLACE_ME
   SLACK_BOT_TOKEN=REPLACE_ME
   SLACK_CHANNEL_ID=REPLACE_ME
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト内での利用例です。

共通準備:
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコア（ai_scores へ書き込み）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（market_regime へ書き込み）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  res = score_regime(conn, target_date=date(2026, 3, 20))
  # 戻り値は 1（成功）を返す設計

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は監査用テーブル群を作成し接続を返す

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

注意点:
- 多くの関数は DuckDB 接続と target_date を受け取り、ルックアヘッドバイアスを防ぐため内部で現在時刻を参照しない設計です。
- OpenAI を呼ぶ関数（news_nlp, regime_detector）は API キーを環境変数 OPENAI_API_KEY または引数 api_key で受け取ります。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を意識して実装されています。

---

## 自動環境読み込みの挙動

- プロジェクトルートはこのファイルの位置から上方に向かって `.git` または `pyproject.toml` を探索して決定します。
- ルートが見つかれば `.env`（上書き不可） → `.env.local`（上書き可）の順で自動ロードします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに便利）。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースセンチメント（score_news）
    - regime_detector.py       # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py              # ETL（run_daily_etl, run_prices_etl 等）
    - etl.py                   # ETL インターフェース再エクスポート
    - calendar_management.py   # マーケットカレンダー管理
    - news_collector.py        # RSS ニュース取得・前処理
    - quality.py               # データ品質チェック
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - audit.py                 # 監査ログスキーマ初期化/DB作成
  - research/
    - __init__.py
    - factor_research.py       # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   # 将来リターン / IC / サマリー等
  - (その他) strategy/, execution/, monitoring/ は __init__ の __all__ に含まれますが、
    この配布に含まれていない場合があります（将来的なモジュール）。

---

## 注意事項 / ベストプラクティス

- OpenAI／J-Quants の API キーは必ずプロジェクト外で安全に管理（シークレット管理）してください。
- ETL や LLM 呼び出し部分は API コストがかかるため、ローカル開発ではモックや制限を行ってください（関数内部でテスト用差替え箇所あり）。
- DuckDB ファイルはバックアップ・運用監視を行ってください（特に監査ログ DB は消さない前提）。
- production モード（KABUSYS_ENV=live）の場合は十分なログ・モニタリングとサンドボックス運用を推奨します。

---

## 貢献 / ライセンス

- 本プロジェクトの貢献は歓迎します。Pull Request 前に issue で計画を共有してください。
- ライセンス情報はリポジトリの LICENSE を参照してください（本 README では明示していません）。

---

この README はコードベースの現状に基づいて作成しています。実行方法や API キー、テーブルスキーマなど運用に必要な追加設定がある場合は、プロジェクト内のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。