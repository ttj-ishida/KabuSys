README — KabuSys (日本株自動売買基盤)
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／研究・運用基盤の骨組みを提供するライブラリです。  
主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- ETL パイプラインによる差分更新と品質チェック
- ニュース収集と LLM を用いたニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

主な機能一覧
--------------
- データ取得・保存
  - J-Quants API クライアント（fetch / save 用関数）
  - DuckDB への冪等保存（ON CONFLICT ベース）
- ETL
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務の差分取得 + 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出
- ニュース処理 & AI
  - RSS 収集（news_collector.fetch_rss、前処理、安全対策付き）
  - 銘柄毎ニュースセンチメント（score_news: OpenAI を使用）
  - 市場レジーム判定（score_regime: ETF MA200 とマクロセンチメント合成）
- 研究（research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン（calc_forward_returns）、IC 計算（calc_ic）、統計サマリ
- 監査ログ
  - 監査用スキーマ初期化（init_audit_schema / init_audit_db）

前提条件 / 必要ライブラリ
-------------------------
- Python 3.10+
  - 型アノテーション（X | Y 形式）や from __future__ import annotations を想定
- 外部ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

例:
pip install duckdb openai defusedxml

設定（環境変数・.env）
---------------------
kabusys は .env / .env.local または OS 環境変数から設定を読み込みます（自動ロード）。  
自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（主に Settings で参照されるもの）:
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必須）
  - KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注連携等）
- OpenAI
  - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector のデフォルト）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / ファイルパス
  - DUCKDB_PATH           : DuckDB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（既定: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- ロギング / 環境
  - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
  - KABUSYS_ENV           : development / paper_trading / live（既定: development）
- システム監視しきい値（任意）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env の自動読み込みは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。

インストール
------------
（プロジェクトをソースとして利用する場合の例）

1. レポジトリをクローン
   git clone <repo-url>
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

（プロジェクトに requirements.txt ある場合はそれを使用してください）

簡単な使い方（コード例）
-----------------------

- DuckDB 接続を作って日次 ETL を実行する例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（銘柄別）を実行する例:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None だと環境変数 OPENAI_API_KEY を参照
print(f"scored {count} codes")

- 市場レジーム判定を実行する例:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ用 DB を初期化する例:

from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)  # テーブルとインデックスを作成する

注意点 / 運用上のポイント
------------------------
- Look-ahead バイアス対策が各所に組み込まれています：
  - score_news / score_regime / ETL 等は内部で date 引数を取る設計で、datetime.today() を直接参照しません。
- J-Quants API 呼び出しはレート制限やリトライ、401 の自動リフレッシュ等を実装しています。JQUANTS_REFRESH_TOKEN を正しく設定してください。
- OpenAI 呼び出しはリトライとフェイルセーフ（失敗時ゼロフォールバック）を行いますが、API 使用はコストが発生します。テスト時はモック化することを推奨します。
- news_collector は SSRF 防止・XML の安全パース・応答サイズ制限など安全対策を備えています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、空の場合はパスする実装がなされています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュースの LLM ベースセンチメント評価
  - regime_detector.py      — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py             — ETL パイプライン（run_daily_etl など）
  - etl.py                  — ETL インターフェース（ETLResult エクスポート）
  - calendar_management.py  — マーケットカレンダー管理 / 営業日判定
  - news_collector.py       — RSS ニュース収集（安全対策あり）
  - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py              — データ品質チェック
  - audit.py                — 監査ログ（テーブル定義 / 初期化）
- research/
  - __init__.py
  - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ
- research/...              — 研究用ユーティリティ
- その他モジュール（strategy, execution, monitoring 等）は __init__ に列挙されています

（ソース内コメントや docstring を参照すると各関数の挙動が詳細に記載されています）

テストとモック
---------------
- OpenAI 呼び出しや外部 HTTP 呼び出しはテスト時にモックする設計になっています（例: news_nlp._call_openai_api を patch）。  
- news_collector._urlopen なども差し替え可能です。

補足
----
- README はコードベースから抽出した情報に基づく概要です。実際の運用では設定や権限、API 利用制限、コスト、安全運用（秘密情報管理）を十分に検討してください。  
- 追加のスクリプトや CLI、パッケージ化（pyproject.toml/requirements）等はプロジェクトルートに応じて整備してください。

以上。必要であれば「.env.example のサンプル」や「よく使うコマンド例（systemd / cron / GitHub Actions 用）」などの追記も作成します。どの項目を追加しますか？