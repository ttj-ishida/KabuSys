# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants / JPX データの ETL、ニュース収集・NLP、ファクター算出・リサーチ、監査ログ（トレーサビリティ）、市場レジーム判定、監視設定などを含むモジュール群を提供します。

概要
- 名前: KabuSys
- 目的: 日本株のデータパイプラインとクオンツリサーチ、AI を用いたニュースセンチメント、監査／発注関連の基盤機能を提供する。
- 設計方針:
  - Look-ahead bias を避ける日付扱い（内部で date.today() を不用意に参照しない）。
  - DuckDB をローカル DB として使用し、ETL は冪等性（ON CONFLICT）を重視。
  - 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・レート制御を備える。
  - ニュース収集では SSRF 対策や XML の安全パースを実施。

主な機能一覧
- データ取得・ETL
  - J-Quants から日次株価（OHLCV）・財務データ・上場銘柄情報・市場カレンダーを取得（jquants_client）。
  - 差分 ETL / 日次 ETL を実行するパイプライン（data.pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）。
  - 品質チェック（欠損・スパイク・重複・日付不整合）（data.quality）。
- ニュース収集・NLP
  - RSS からニュース収集と前処理（data.news_collector）。
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント集計（ai.news_nlp.score_news）。
  - マクロニュースと ETF（1321）MA 乖離を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）。
- 研究（research）
  - モメンタム、ボラティリティ、バリューなどのファクター計算（research.factor_research）。
  - 将来リターン計算、IC 計算、統計サマリなど（research.feature_exploration）。
  - 共通統計ユーティリティ（data.stats.zscore_normalize）。
- 監査（audit）
  - signal → order_request → execution のトレース用テーブルと初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）。
- ユーティリティ・設定
  - 環境変数管理（config.Settings）。`.env` / `.env.local` の自動読み込み（プロジェクトルート検出）機能あり。

セットアップ手順（開発環境向け）
1. 前提
   - Python 3.10 以上（型ヒントで `|` を使用しているため）。
   - システムにネットワークアクセスが可能であること（J-Quants / OpenAI へアクセスする場合）。

2. リポジトリの取得
   - リポジトリをクローンし、作業ディレクトリをプロジェクトルート（.git や pyproject.toml がある場所）にしてください。

3. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

4. 依存パッケージのインストール
   - 必要な主要パッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 開発用に requirements.txt / pyproject.toml がある場合はそれに従ってください。手動例:
     - pip install duckdb openai defusedxml

5. パッケージのインストール（任意）
   - setup が用意されていれば editable インストール:
     - pip install -e .

環境変数 / .env
- 自動読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml のある親）を探索し、`.env`（優先度低）および`.env.local`（優先度高）を読み込みます。
  - OS 環境変数は保護され、`.env` により上書きされません（`.env.local` は override=True で上書きするが OS 変数は protected）。
  - 自動読み込みを無効化する場合:
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。

- 主要な環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須: ETL 実行時）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（実行/発注系で使用）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
  - KABUSYS_ENV: 環境 ('development' / 'paper_trading' / 'live')
  - LOG_LEVEL: 'DEBUG' / 'INFO' / 'WARNING' / 'ERROR' / 'CRITICAL'

例: `.env`（抜粋）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的な使い方（Python API 例）
- 共通: 設定や duckdb の接続は config.Settings から取得できます。

1) DuckDB 接続を作る
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))

2) 日次 ETL を実行する
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

3) ニューススコアリング（銘柄別ニュースセンチメント）
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))

5) ファクター計算（研究用）
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))

6) 監査 DB 初期化（別 DB ファイルで運用する場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は 初期化済みの duckdb 接続

注意点 / 運用上のヒント
- OpenAI API 呼び出しはレート、ネットワーク障害に対しリトライとフォールバック（失敗時はゼロスコア等）を行います。API キーは必ず保護してください。
- J-Quants 呼び出しはレート制御 (_RateLimiter) と 401 リフレッシュハンドリングを実装しています。refresh token は `.env` に安全に保管してください。
- ニュース収集は SSRF 対策や XML の安全パースを行いますが、RSS ソースは信頼できるものを追加してください。
- DuckDB への executemany に空リストを渡すとエラーとなるバージョンがあるため、実装は空チェックを行っています（互換性に注意）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄別）
    - regime_detector.py      — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS 取得・前処理・保存
    - calendar_management.py  — 市場カレンダーと営業日ユーティリティ
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - quality.py              — 品質チェック
    - audit.py                — 監査ログ用 DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - research/*, ai/* の他モジュール...

ライセンス / 責任
- この README はコードベースから自動生成した要約です。実運用前にコード全体をレビューし、API キー・トークンの管理、外部サービスの利用制限、法的/規制上の準拠事項を確認してください。

追加情報 / よくある質問
- 自動で .env を読み込みたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト時は OpenAI 呼び出し等をモックすると安全です（コード内でもテスト差し替えを想定した設計あり）。
- DuckDB ファイルやログの配置は settings.duckdb_path / settings.sqlite_path 等を変更して調整してください。

必要があれば、README にサンプル .env.example、ユースケース別の具体的なコード例（ETL cron、監査 DB 運用、ニュースソース追加手順など）を追記します。どの内容を優先して追加しますか?