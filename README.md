# KabuSys — 日本株自動売買プラットフォーム（README）

日本語ドキュメントです。KabuSys は日本株向けのデータパイプライン、リサーチ、ニュースNLP、レジーム判定、監査ログなどを備えた自動売買システムのコアライブラリ群です。本リポジトリのコードは DuckDB をデータストアに用い、J-Quants / OpenAI / kabuステーション 等の外部サービスと連携して動作します。

## プロジェクト概要
- 名称: KabuSys
- 目的: 日本株のデータ収集（J-Quants）、品質チェック、特徴量（ファクター）計算、ニュースNLP による銘柄センチメント評価、ETF ベースの市場レジーム判定、監査ログ（発注〜約定トレーサビリティ）の提供。
- コア技術: Python, DuckDB, OpenAI API, J-Quants API, RSS 収集、堅牢な ETL・品質チェックロジック

## 主な機能（抜粋）
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション・レート制限・自動リフレッシュ対応）
  - ETL の日次パイプライン（run_daily_etl）と個別 ETL ジョブ（prices / financials / calendar）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合の検出（QualityIssue オブジェクト）
- ニュース収集・NLP
  - RSS 収集（SSRF対策、トラッキング除去、前処理）
  - ニュースを銘柄ごとに集約し OpenAI でセンチメントを取得して ai_scores に書き込み（score_news）
- レジーム判定
  - ETF 1321（日経225 連動）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義、初期化ユーティリティ（init_audit_db / init_audit_schema）によるトレーサビリティ

## 依存関係（代表例）
本 README 作成時点のコードを動かす際に想定される主要パッケージ。
- Python 3.9+
- duckdb
- openai（OpenAI の新 SDK を想定）
- defusedxml

setup.py / requirements.txt がある前提であれば `pip install -r requirements.txt` または `pip install -e .` を推奨します。個別に入れる場合:
- pip install duckdb openai defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を確認してください）

## 環境変数（必要なもの）
自動で .env/.env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須・主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL で使用）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabuステーション API のパスワード

OpenAI:
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime のデフォルト）

オプション / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 をセット）

.env 例:
（プロダクション機密情報は別途安全に管理してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従う）
4. .env をプロジェクトルートに配置し、必要な環境変数を設定
5. DuckDB ファイル保存先の親ディレクトリ（例 data/）を作成
   - mkdir -p data

## 使い方（主要なユースケース）
下記は Python スクリプトからライブラリを直接呼ぶ例です。DuckDB 接続は duckdb.connect(path) を使用します。

1) ETL（日次パイプライン）
- run_daily_etl を使って市場カレンダー、株価、財務データを差分取得し品質チェックまで実行します。

簡易例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメントスコア取得（score_news）
- raw_news / news_symbols テーブルを参照して OpenAI で銘柄ごとのセンチメントを計算し ai_scores に書き込みます。

例:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)

3) 市場レジーム判定（score_regime）
- ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込みます。

例:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

4) 監査ログ DB 初期化
- 発注 / 約定の監査用テーブルを DuckDB に初期化する helper。

例:
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.kabusys")
# conn を使って order_requests 等への書き込みが可能

5) カレンダー周りのユーティリティ
- is_trading_day, next_trading_day, prev_trading_day, get_trading_days などを利用して営業日判定や期間取得が可能。

例:
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

## ディレクトリ構成（主要ファイル）
リポジトリ内の主要モジュールを抜粋して示します（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + save_* 関数
    - pipeline.py        — ETL パイプライン run_daily_etl 等
    - etl.py             — ETLResult の再エクスポート
    - calendar_management.py — 営業日ロジック / calendar_update_job
    - news_collector.py  — RSS 収集 / 前処理 / 保存
    - stats.py           — zscore_normalize 等統計ユーティリティ
    - quality.py         — データ品質チェック（missing/spike/duplicates/...）
    - audit.py           — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — forward returns, IC, factor_summary

上記以外に strategy, execution, monitoring 等のパッケージが __all__ に用意されています（将来的な戦略・約定・監視モジュールの公開インターフェース）。

## 開発者向けメモ
- Look-ahead bias 対策: 内部の関数群は datetime.today()/date.today() を直接参照せず、target_date を引数で受け取る設計です（バックテストと運用で同じ振る舞いになるよう配慮）。
- DuckDB の executemany はバージョン依存で空のパラメータを受け付けないケースがあるため、コード内で空チェックを行っています。
- OpenAI 呼び出しはリトライと戻り値のバリデーションを行い、API 失敗時はフェイルセーフ（0 やスキップ）する設計です。
- news_collector は SSRF・XML Bomb・大容量レスポンス等の脅威に対する対策を実装しています。

## トラブルシューティング（よくある問題）
- ValueError: 環境変数が未設定
  - settings.* プロパティは必須キー未設定時に ValueError を投げます。必須環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を確認してください。
- OpenAI API エラー / レート制限
  - SDK の RateLimitError や 5xx はリトライされますが、長時間失敗する場合は API キーの権限・クォータを確認してください。
- J-Quants 認証失敗（401）
  - get_id_token はリフレッシュトークンから id_token を取得します。リフレッシュトークンが無効だと認証失敗します。
- DuckDB に書き込めない / パーミッション
  - DUCKDB_PATH の親ディレクトリが存在するか・書き込み権限を確認してください。
- ニュース収集で RSS が取得できない
  - fetch_rss はリダイレクト先やコンテンツサイズを検査します。RSS が gzip で巨大な場合や最終リダイレクト先がプライベートIP の場合は取得を拒否します。

## ライセンス / コントリビューション
この README はコードベースの概要ドキュメントです。ライセンスやコントリビュート手順はプロジェクトの LICENSE / CONTRIBUTING ファイルに従ってください。

---

ご要望があれば、README に以下を追加できます:
- 具体的な実行スクリプト（CLI 例）
- 完全な .env.example ファイル
- CI / テストの実行方法（ユニットテスト・モック例）
- データベーススキーマ（CREATE TABLE の一覧）