# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量算出、ニュースの NLP 評価、マーケットレジーム判定、監査ログ（トレーサビリティ）などの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されたライブラリです。

- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- 収集データの品質チェック（欠損 / 重複 / スパイク / 日付整合性）
- ニュースの収集と前処理（RSS）および OpenAI を用いた銘柄別センチメント評価
- 市場レジーム（bull / neutral / bear）判定（ETF + マクロニュースの LLM 評価統合）
- 研究用途のファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化ユーティリティ
- アプリ設定の環境変数管理（.env 自動ロード機能を含む）

設計上の特徴：
- DuckDB を主要なオンディスク DB として使用（ファイル or :memory:）
- Look-ahead bias に配慮した日付扱い（内部で date.today() を乱用しない）
- API 呼び出しに対する堅牢な再試行・バックオフロジック
- 冪等性を重視した DB 書き込み（ON CONFLICT 系）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数のチェック
- データ（kabusys.data）
  - J-Quants クライアント（fetch / save の実装、認証・リトライ・レート制限）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 市場カレンダー管理（営業日判定・次営業日/前営業日検索）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - 監査ログスキーマ初期化（監査テーブル / インデックス作成）
  - 共通統計ユーティリティ（Zスコア正規化）
- AI（kabusys.ai）
  - ニュース NLP（銘柄別センチメント算出）
  - レジーム判定（ETF 1321 の MA とマクロニュース LLM スコアを合成）
  - OpenAI 呼び出しに対するリトライやレスポンス検証
- 研究（kabusys.research）
  - ファクター計算：モメンタム / ボラティリティ / バリュー 等
  - 将来リターン計算、IC（スピアマン）、統計サマリー、ランク化ユーティリティ

---

## 必要な環境変数

主に以下を使用します（すべて必須ではありませんが、多くの機能で必要）:

- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須 for ETL）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行/発注周り）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用など、デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境 ('development' / 'paper_trading' / 'live')
- LOG_LEVEL — ログレベル ('DEBUG','INFO',...)

注意:
- パッケージ読み込み時にプロジェクトルートが検出されると .env / .env.local を自動で読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部機能に依存）
- duckdb が利用可能（pip install duckdb）
- OpenAI SDK（openai）を使う場合は該当バージョンに合わせてインストール

基本的な手順:

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は最低限 pip install duckdb openai defusedxml を追加）
4. .env を用意して必要な環境変数を設定
5. DuckDB ファイルの作成・スキーマ初期化（必要に応じて）
   - Python から init_audit_db などを呼ぶことで監査 DB を初期化できます（後述）

---

## 使い方（主要なサンプル）

以下は Python インタラクティブ／スクリプトで利用する場合の例です。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーが必要）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)

- 市場レジームを評価して market_regime に保存:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクターを計算:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
print(mom[:5])

- 監査ログ DB の初期化（独立 DB を使う場合）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます

- 設定アクセス例:

from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)

注意点:
- OpenAI を利用する関数は API キーを引数で渡すことも可能（api_key=...）。テスト時は関数内部の _call_openai_api をモックして外部呼び出しを回避できます。
- ETL / 保存関数は冪等性を考慮していますが、初回は表スキーマが必要です（raw_prices, raw_financials, market_calendar, ai_scores など）。スキーマ作成用の初期化ユーティリティが別途存在する前提です（プロジェクトに応じて用意してください）。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）

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
  - etl.py (軽量再エクスポート)
  - stats.py
  - quality.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - (その他モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの役割（再掲）:
- config.py: 環境変数管理・自動 .env ロード・設定プロパティ
- data/jquants_client.py: J-Quants API 呼び出し・DuckDB への保存ロジック
- data/pipeline.py: 日次 ETL の Orchestrator（run_daily_etl 等）
- data/quality.py: データ品質チェック一式
- data/news_collector.py: RSS 取得・前処理、raw_news 保存（SSRF 対策・サイズ制限等）
- data/audit.py: 監査ログテーブルと初期化ユーティリティ
- ai/news_nlp.py: ニュース → 銘柄別センチメント算出（OpenAI）
- ai/regime_detector.py: マーケットレジーム判定ロジック
- research/*: ファクター計算・統計解析ユーティリティ

---

## 開発 / テスト時の注意

- OpenAI 周りは外部依存なのでユニットテストでは _call_openai_api をパッチしてモックすることを想定しています（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）。
- .env 自動ロードはプロジェクトルートの検出に依存します。CI / テスト環境で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョン差異があるため、空リストチェックを行った上で呼び出す実装になっています。
- Look-ahead bias 回避のため、内部ロジックは target_date パラメータを明示的に受け取り、現在時刻を直接参照しない設計が多く採用されています。

---

この README はコードベースの主要設計・使い方をまとめたものです。実運用／組み込み時は環境変数の管理、DB スキーマの初期化、API キーの取り扱い（安全な保管）に十分ご注意ください。質問や追加の利用例が必要であれば教えてください。