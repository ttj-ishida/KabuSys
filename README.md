# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants）によるマーケットデータ収集、ニュースの NLP による銘柄センチメント評価、ファクター・リサーチ、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL パイプライン）
- RSS ニュース収集と記事の前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_scores と市場レジーム判定）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量探索ユーティリティ（IC, forward returns 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ
- 環境変数 / .env の自動読み込みと設定管理

設計上の重点:
- ルックアヘッドバイアスを防ぐ日付扱い（内部で date.today() を直接参照しない設計の箇所あり）
- API 呼び出しの堅牢性（リトライ・エクスポネンシャルバックオフ・フェイルセーフ）
- DuckDB を用いたローカル分析・保存（ETL は冪等性を重視）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数読み込み (.env / .env.local の自動ロード)、settings オブジェクト提供
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存関数、トークン自動リフレッシュ、レート制限）
  - pipeline: 日次 ETL 実装（run_daily_etl 等）と ETLResult
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - news_collector: RSS 取得と前処理
  - calendar_management: JPX カレンダー管理／営業日判定
  - audit: 監査ログ（監査テーブルDDL・初期化関数）
  - stats: zscore_normalize（研究用ユーティリティ）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 動作前提・依存関係

- Python 3.10 以上（typing の union operator などを使用）
- 必須ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib, json, logging 等を使用

pip でインストールする例（仮）:
pip install duckdb openai defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数・設定

パッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)

settings へのアクセス例:
from kabusys.config import settings
token = settings.jquants_refresh_token

---

## セットアップ手順（ローカルでの最小手順）

1. Python 3.10+ を用意
2. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
3. プロジェクトルートに .env を作成（.env.example を参考に）
   - 例（最低限）:
     JQUANTS_REFRESH_TOKEN=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
4. DuckDB データベース用ディレクトリを作成（自動作成される箇所もありますが、念のため）
   - mkdir -p data
5. 監査ログ DB を初期化する（必要に応じて）
   - from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要なユースケース）

以下はライブラリを直接呼ぶ最小の例です。実運用ではログ・例外処理・ジョブスケジューラ等を追加してください。

1) DuckDB 接続を作成して日次 ETL を実行
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順に処理します。ETLResult を返します。

2) ニュースセンチメントを計算して ai_scores に保存
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書込み銘柄数: {n_written}")

3) 市場レジームをスコアリングして market_regime に保存
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用

4) 監査ログスキーマの初期化（既存 DB に追加）
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

5) J-Quants から直接データをフェッチ（テストや単発取得）
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
data = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))

---

## 実行時の注意点 / 設計上のポイント

- 日付扱いはルックアヘッドバイアスを避けるよう設計されています（多くの関数で target_date 引数を明示する）。
- OpenAI 呼び出しはリトライとフォールバック（失敗時はスコア 0.0）を行います。API キーは関数引数で注入可能（テスト容易性）。
- J-Quants API 呼び出しはレート制限（120 req/min）を守る実装です（内部でスロットリング）。
- news_collector は SSRF 対策やレスポンス上限など安全対策を実装しています。
- DuckDB の executemany に関して空リストバグ（バージョン依存）を回避するため、空チェックを入れています。

---

## ディレクトリ構成

（主要ファイル・モジュールのツリー）

src/kabusys/
- __init__.py
- config.py                      -> 環境変数 / .env 読み込みと settings
- ai/
  - __init__.py
  - news_nlp.py                   -> ニュース NLP（score_news）
  - regime_detector.py            -> 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             -> J-Quants API クライアント（fetch/save 関数）
  - pipeline.py                   -> ETL パイプライン（run_daily_etl 等）
  - etl.py                        -> ETLResult の再エクスポート
  - calendar_management.py        -> 市場カレンダー管理（営業日判定・更新ジョブ）
  - news_collector.py             -> RSS ニュース収集・前処理
  - stats.py                      -> zscore_normalize 等
  - quality.py                    -> データ品質チェック
  - audit.py                      -> 監査ログスキーマ初期化、init_audit_db 等
- research/
  - __init__.py
  - factor_research.py            -> calc_momentum / calc_value / calc_volatility
  - feature_exploration.py        -> calc_forward_returns / calc_ic / factor_summary / rank

その他:
- data/                          -> デフォルトのデータ格納先（DuckDB ファイル等）
- .env, .env.local               -> 環境変数（プロジェクトルートに配置）

---

## 開発・テストについてのヒント

- テスト時は環境変数の自動ロードを無効化できます:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O はモック化可能（各モジュール内で _call_openai_api や _urlopen を差し替える設計）。
- DuckDB の in-memory ":memory:" を使えば副作用のないユニットテストが行えます（例: init_audit_db(":memory:")）。

---

## サポート / 貢献

バグ報告や機能提案は issue を立ててください。  
コントリビュートする場合は、コードのスタイル・テストカバレッジ・ドキュメント整備を心がけてください。

---

以上が README の骨子です。必要に応じてサンプルスクリプト、requirements.txt、.env.example、運用手順（cron / Airflow ジョブ化）などを追加できます。希望があれば追記します。