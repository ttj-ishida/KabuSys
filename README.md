# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データパイプライン、ニュースNLP、市場レジーム判定、リサーチ向けファクター計算、監査ログなどを含むモジュール群）です。本リポジトリは、ETL・品質チェック・AIベースのニュースセンチメント評価・監査トレースなど、実運用を想定したコンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS ベースのニュース収集と OpenAI による銘柄別・マクロセンチメント評価
- ETF（1321）を用いた市場レジーム判定（MA + マクロセンチメントの合成）
- DuckDB を用いたデータ永続化、品質チェック、監査ログテーブル
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注・約定の監査トレーサビリティ（監査テーブル・初期化ユーティリティ）

設計方針としては、ルックアヘッドバイアス回避、堅牢な例外ハンドリング、冪等性（idempotency）、および外部 API 呼び出し周りのリトライ・レート制御を重視しています。

---

## 主な機能一覧

- ETL（data.pipeline）
  - run_daily_etl: 市場カレンダー・株価・財務データの差分取得・保存・品質チェックを実行
  - 個別 ETL：run_prices_etl、run_financials_etl、run_calendar_etl
- J-Quants API クライアント（data.jquants_client）
  - fetch / save の一連処理、レート制限とリトライ、トークンリフレッシュ対応
- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news への保存ロジック（設計）
- ニュース NLP（ai.news_nlp）
  - 銘柄ごとの記事をまとめて OpenAI に問い合わせ、ai_scores テーブルに書き込み
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロ記事の LLM センチメントを合成して daily regime を算出
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検査と QualityIssue レポート
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- リサーチ（research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary など
- 共通ユーティリティ
  - config.Settings による環境変数読み込み（.env 自動ロード機能あり）
  - data.stats.zscore_normalize 等の統計ユーティリティ

---

## 必要条件（主な依存）

- Python 3.10+
- duckdb
- openai
- defusedxml

（その他、標準ライブラリの urllib 等を使用）

requirements.txt があればそれを使用してください。なければ以下のようにインストールできます:

例:
pip install duckdb openai defusedxml

プロジェクトは src レイアウトのため、開発時は -e インストールが便利です:
pip install -e .

---

## 環境変数 / .env

プロジェクトルートの .env / .env.local が自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可能）。

必須の環境変数（アプリ実行に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時、引数で渡すことも可）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読込を無効化

.example .env（README 用）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存をインストール
   pip install -r requirements.txt
   または
   pip install duckdb openai defusedxml

4. 開発用インストール（src レイアウト）
   pip install -e .

5. .env をプロジェクトルートに作成し、必要な環境変数を設定

---

## 使い方（主な例）

以下は Python REPL やスクリプトから呼び出す簡単な使用例です。各関数は duckdb 接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

基本的な DB 接続例:
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

ETL を日次で実行:
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニューススコアリング（銘柄ごとの AI スコア）:
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("written:", n_written)

市場レジーム判定:
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

監査ログ DB の初期化（監査専用 DB を作る例）:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

カレンダー更新ジョブ（夜間バッチ）:
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)

データ品質チェックを実行して結果を取得:
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

リサーチ向けファクター計算例:
from kabusys.research.factor_research import calc_momentum
factors = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

注意点:
- OpenAI を呼ぶ関数（score_news / score_regime）は OPENAI_API_KEY が必要です。api_key を引数で注入することも可能。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を必要とします（settings.jquants_refresh_token）。
- すべての ETL / 保存関数は冪等性（重複 INSERT → ON CONFLICT DO UPDATE）を考慮しています。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリは src/kabusys 以下に機能別モジュールが配置されています。主要な構成:

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）

- src/kabusys/config.py
  - .env / 環境変数読み込み、Settings クラス（各種 API トークン・パス等の設定取得）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: 銘柄別ニュースセンチメントスコアリング（OpenAI 使用）
  - regime_detector.py: ETF MA とマクロセンチメントを合成する市場レジーム判定

- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch/save 含む）
  - pipeline.py: ETL の実装（run_daily_etl 等）
  - etl.py: ETLResult の公開
  - news_collector.py: RSS 収集ロジック（前処理・SSRF 対策等）
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - quality.py: データ品質チェック
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログテーブルの DDL と初期化ユーティリティ

- src/kabusys/research/
  - __init__.py
  - factor_research.py: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC / ランク・統計サマリー等

- src/kabusys/ai/__init__.py、src/kabusys/research/__init__.py などで API を再エクスポートしています。

---

## 運用・注意点

- ルックアヘッドバイアス対策: 多くのモジュールで datetime.today()/date.today() を内部で参照せず、明示的な target_date を受け取る設計です。バックテストや再現性のあるバッチ実行時は target_date の注入を推奨します。
- 冪等性: J-Quants データ保存や監査テーブルの初期化は冪等に実装されています。ただし DDL の transactional オプションなど使用時の注意点あり（DuckDB のトランザクション挙動に依存）。
- API キー: OpenAI・J-Quants のキーは安全に管理してください。.env ファイルは機密情報を含むためバージョン管理にコミットしないでください。
- テスト: 各モジュールは外部 API 呼び出し部分をモックできるよう設計されています（内部の _call_openai_api などを patch してテスト可能）。

---

## 付録: よく使う関数一覧（抜粋）

- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_management.calendar_update_job(conn)
- kabusys.data.audit.init_audit_db(path)
- kabusys.research.factor_research.calc_momentum(conn, target_date)

---

ご不明点や README に追記したい具体的な使い方（例: docker-compose、CI セットアップ、より詳しい ETL 実行例や SQL スキーマ一覧など）があれば教えてください。必要に応じてサンプルスクリプトや起動手順を追加します。