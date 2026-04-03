KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤向けの Python ライブラリです。  
主な目的は J-Quants 等からのデータ ETL、ニュースの NLP スコアリング、ファクター計算、マーケットレジーム判定、監査ログ（発注・約定トレーサビリティ）など、自動売買システムに必要な基盤処理を提供することです。

主な特徴
--------
- J-Quants API 経由の差分 ETL（株価・財務・市場カレンダー）
- ニュース（RSS）収集と OpenAI を用いた銘柄別センチメント評価（news_nlp）
- マクロニュース + ETF MA 乖離を合成する市場レジーム判定（regime_detector）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ（research）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）用のスキーマ作成ユーティリティ
- DuckDB ベースの永続化・冪等保存（ON CONFLICT を利用）

セットアップ手順
----------------

前提
- Python 3.10 以上（| 型注釈を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. ローカルで開発する場合（パッケージとして editable インストール）
   - pip install -e .

4. 環境変数 / .env
   プロジェクトルートに .env を置くと自動で読み込まれます（CWD ではなくパッケージ位置から .git / pyproject.toml を探索してプロジェクトルートを特定します）。
   自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   - OPENAI_API_KEY=sk-...
   - KABU_API_PASSWORD=...
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag

   注意: Settings クラス（kabusys.config.settings）は必須値をチェックします。J-Quants のリフレッシュトークンなどは必須になっています。

使い方（簡単な例）
-----------------

以下はライブラリの主な使い方サンプルです。実行する前に .env または環境変数で必要なキーを設定してください。

1) DuckDB 接続と日次 ETL を実行する
- ETL は市場カレンダー → 株価日足 → 財務データ → 品質チェック の順で処理します。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュースセンチメントをスコア化（OpenAI 必須）
- score_news(conn, target_date, api_key=None) を使います。api_key を与えない場合は環境変数 OPENAI_API_KEY を参照します。

例:
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 19))
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- score_regime(conn, target_date, api_key=None)

例:
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026,3,19))

4) 監査ログデータベース初期化
- 監査用の DuckDB ファイルを作成し、必要なテーブル・インデックスを作成します。

例:
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")

5) J-Quants クライアント関数
- jquants_client モジュールは ID トークン取得・各種フェッチ・保存関数を提供します。
  例: fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

設計上の注意点と安全策
---------------------
- Look-ahead バイアス対策: 日付計算やデータ取得は target_date ベースで厳格に行い、datetime.today(), date.today() を不用意に使わない設計になっています（AI スコアリングやファクター計算）。
- OpenAI 呼び出しはリトライ・バックオフやパース失敗時のフェイルセーフ（0.0 でフォールバック）を実装しています。
- RSS 収集は SSRF 対策（スキームチェック、プライベートホスト拒否、リダイレクト検査、レスポンスサイズ制限）を行っています。
- J-Quants API 呼び出しではレート制御（120 req/min）と 401 自動リフレッシュ、リトライロジックを備えています。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    -- ニュース NLP（銘柄別スコア）
  - regime_detector.py             -- マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント / 保存関数
  - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
  - etl.py                         -- ETLResult 再エクスポート
  - news_collector.py              -- RSS 収集（SSRF 対策等）
  - quality.py                     -- データ品質チェック
  - stats.py                       -- 統計ユーティリティ（zscore_normalize）
  - calendar_management.py         -- マーケットカレンダー（営業日判定等）
  - audit.py                       -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py         -- 将来リターン計算、IC、統計サマリー 等
- research/* other modules re-exported
- その他: strategy/ execution/ monitoring 等のパッケージは __all__ に含まれます（各機能層）

設定とオプション
-----------------
- KABUSYS_ENV (development | paper_trading | live) : 実行モード
- LOG_LEVEL : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化 (任意)
- DB パス（DUCKDB_PATH / SQLITE_PATH）や監視用の PID/KILL フラグパスなどは settings 経由で取得できます。

運用上のヒント
---------------
- 本コードは本番口座へ直接接続する発注ロジックを含まない部分（データ・研究・監査）に重点を置いています。実際の発注・約定ロジックを組み込む場合はリスク管理・冪等性確認を十分に行ってください。
- OpenAI 呼び出しはコストがかかるため、バッチ単位やレート制限を考慮して運用してください。
- ETL は差分取得・バックフィル設計になっているため、cron やジョブスケジューラで定期実行する運用に向いています。
- DuckDB ファイルは定期バックアップを推奨します（監査ログは削除しない前提）。

ライセンス / 貢献
-----------------
（必要に応じてここにライセンスや貢献方法を記載してください）

補足
----
README にない詳細な API 使用例はコード内の docstring を参照してください。各関数は引数説明・返り値・例外仕様が記載されています。問題や改善提案があれば issue / PR を作成してください。