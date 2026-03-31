README.md

KabuSys — 日本株自動売買プラットフォーム（開発向け概要）
=================================

概要
----
KabuSys は日本株のデータ取得・前処理・ファクター計算・ニュース解析・監査ログ・ETL パイプライン等を備えた自動売買/リサーチ基盤向けのライブラリ群です。  
主要コンポーネントは DuckDB を利用したオンプレミスデータレイク（raw_prices / raw_financials / raw_news 等）と、J-Quants / RSS / OpenAI（LLM）を組み合わせた処理フローを想定しています。

主な特徴
--------
- データ ETL（J-Quants 経由で株価・財務・マーケットカレンダーを差分取得・保存）
- データ品質チェック（欠損／スパイク／重複／日付不整合検出）
- ニュース NLP（OpenAI を用いた銘柄別センチメント集約・ai_scores への保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- 監査ログ（信号→発注→約定のトレーサビリティ用テーブル群）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- セキュアな RSS 収集（SSRF 対策・トラッキング除去・サイズ制限・XML デフューズ処理）
- 設定管理（.env の自動読み込み、環境変数による設定）

セットアップ手順
----------------

前提
- Python 3.10+（型アノテーションの union 演算子 `|` を使用）
- Git（.git をプロジェクトルートとして自動 .env ロードを行うため推奨）

インストール（開発環境）
1. リポジトリをクローン:
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール:
   python -m pip install -e .[dev]  または最低限:
   python -m pip install -e . duckdb openai defusedxml

依存パッケージ（主要）
- duckdb
- openai (OpenAI Python SDK。OpenAI.Chat Completions を使用)
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

環境変数 / .env
プロジェクトはプロジェクトルートの .env と .env.local を自動で読み込みます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API パスワード（注文時）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- OPENAI_API_KEY        : OpenAI 呼び出しに使用（score_news / score_regime の引数でも指定可）

任意 / デフォルト
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視関連

使い方（主要 API と簡単な実行例）
---------------------------------

基本的なパターンは DuckDB 接続を作成し、各モジュールの関数に接続と日付を渡す形です。以下は最小限の実行例です。

準備: 設定読み込みと DuckDB 接続
- settings は kabusys.config.settings 経由で参照できます（.env 自動読み込みあり）。

例:
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 30))
print(result.to_dict())

2) ニュース NLP（銘柄別スコアリング）
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が設定されている前提
count = score_news(conn, target_date=date(2026, 3, 30))
print(f"書き込み銘柄数: {count}")

3) 市場レジーム判定（MA200 + マクロニュース）
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 30))

4) 監査ログ DB 初期化
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # :memory: も可能

5) J-Quants から生データを直接取得（ETL を使わずデバッグ）
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,30))

注意点
- OpenAI 呼び出しは API キーを環境変数 OPENAI_API_KEY または関数引数で渡します。
- score_news / score_regime は外部 API 呼び出しに失敗した場合にフェイルセーフで継続する設計です（スコアを0にする等）。
- DuckDB に対する書き込みは基本的に冪等を意識して実装（ON CONFLICT 等）されています。

ディレクトリ構成（要約）
----------------------

src/kabusys/
- __init__.py
  - パッケージ公開情報（version, __all__）

- config.py
  - 環境変数/.env 自動ロードと Settings（各種設定プロパティ）

- ai/
  - __init__.py
  - news_nlp.py        : ニュースの集約・OpenAI による銘柄別センチメント算出
  - regime_detector.py : マーケットレジーム判定（1321 MA200 + マクロニュース）

- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - etl.py                : ETLResult の再エクスポート
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - stats.py              : 共通統計ユーティリティ（zscore_normalize）
  - quality.py            : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py              : 監査ログテーブル定義・初期化
  - news_collector.py     : RSS 収集（SSRF 対策、正規化、DB 挿入）

- research/
  - __init__.py
  - factor_research.py    : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリ / ランク関数

補足：主要テーブル（DuckDB 上想定）
- raw_prices        : 日次株価（date, code, open, high, low, close, volume, turnover, fetched_at）
- raw_financials    : 財務データ（code, report_date, eps, roe, fetched_at, ...）
- market_calendar   : 市場カレンダー（date, is_trading_day, is_half_day, is_sq_day）
- raw_news, news_symbols, ai_scores : ニュース・銘柄紐付け・AI スコア
- market_regime     : 日次の市場レジーム（date, regime_score, regime_label, ma200_ratio, macro_sentiment）
- signal_events / order_requests / executions : 監査ログ関連

設計上の注意・理念
-------------------
- ルックアヘッドバイアス防止: 各モジュールは target_date 引数を明示的に受け取り、内部で date.today() 等に依存しない実装を心掛けています（バックテストに安全）。
- フェイルセーフ: 外部 API（OpenAI / J-Quants / ネットワーク）障害時は可能な限り局所的にフォールバック／スキップして処理継続するよう設計されています。
- 冪等性: DB 書き込みは ON CONFLICT 等で上書きすることで再実行時の安全性を確保しています。
- セキュリティ: RSS の SSRF 対策、defusedxml による XML パース、トラッキングパラメータ除去等を実装しています。

開発・テスト
------------
- 自動 .env ロードは .git または pyproject.toml をプロジェクトルートの指標としています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し自動読み込みを無効化できます。
- OpenAI 呼び出し箇所は内部 _call_openai_api をモックしてテスト可能な設計です。

最後に
------
この README はコードベースの主要機能と使用法の概要をまとめたものです。各モジュールの詳細な利用例やスキーマ定義、ETL の実運用設定（ジョブスケジューリング、監視アラート設定等）はプロジェクトの運用ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。質問や追加のドキュメント化が必要であれば教えてください。