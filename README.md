KabuSys — README (日本語)
========================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／自動売買支援ライブラリです。  
主に以下の機能を提供します。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- ニュース収集・前処理・NLP（OpenAI）による銘柄ごとのニュースセンチメントスコアリング
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースの LLM センチメント合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索（forward returns / IC 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を表現するスキーマ定義と初期化ユーティリティ

主な想定用途:
- データパイプライン（夜間 ETL）と品質管理
- 研究用途のファクター計算・評価
- ニュースを活用したアルファ発見
- バックテスト準備や自動売買監査ログ基盤の構築

主な機能一覧
-------------
- data/*
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動更新、レートリミット、リトライ）
  - ニュース収集（RSS フィード取得、正規化、SSRF/サイズ対策）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/*
  - ニュース NLP（gpt-4o-mini を用いた銘柄スコアリング: score_news）
  - 市場レジーム判定（ETF MA200 乖離とマクロセンチメント合成: score_regime）
  - 安定した API 呼び出し・リトライ設計（429, 5xx, タイムアウト対策）
- research/*
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数・.env 自動読み込み（プロジェクトルート検出）と設定取得用 Settings オブジェクト

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（PEP 604 の union 型記法、型注釈を使用）
   - ネットワークアクセス（J-Quants / OpenAI / RSS）

2. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

3. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

4. 必要パッケージをインストール
   - 主要依存（例）
     - pip install --upgrade pip
     - pip install duckdb openai defusedxml
   - プロジェクト固有の追加依存がある場合は適宜インストールしてください（例: slack SDK 等）。

   ※ 本コードベースは独自の .env ローダを持つため python-dotenv は必須ではありません。

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（config モジュールが .git または pyproject.toml を基準にルートを探索します）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime が参照）
     - KABU_API_PASSWORD — kabu API のパスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用（必要な場合）
   - 任意設定（デフォルトあり）:
     - KABUSYS_ENV (development|paper_trading|live) — 動作モード
     - LOG_LEVEL (DEBUG|INFO|...) — ログレベル
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — 監視 DB 等に使用（data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

基本的な DuckDB 接続を作り、ETL を実行する例:

from kabusys.config import settings
import duckdb
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# DuckDB 接続（settings.duckdb_path のデフォルト: data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn)
print(result.to_dict())

ニューススコアリング（OpenAI API キーが必要）:

from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")

市場レジーム判定（score_regime）:

from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB を初期化する例:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能

設定（config.Settings）の使い方:

from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError

注意点・設計上のポリシー
-----------------------
- Look-ahead bias（先見バイアス）対策:
  - ETL・スコアリング関数は内部で datetime.today() を用いないか、あるいは target_date を引数で受けます。バックテスト時は必ず明示的に target_date を指定してください。
  - API 取得時の fetched_at を UTC で保存し「いつそのデータを知り得たか」をトレースします。
- 冪等性:
  - J-Quants から取得したデータ保存は ON CONFLICT を用いて冪等に行います（save_* 関数）。
  - 監査ログは order_request_id を冪等キーとして利用可能。
- エラー耐性:
  - 外部 API 呼び出しにはリトライ（指数バックオフ）とフェイルセーフが実装されています。LLM/API 失敗時はスコアを 0 にフォールバックするなどの設計が多くの箇所で適用されています。
- セキュリティ:
  - RSS 取得では SSRF 対策（ホストのプライベート判定、リダイレクト検査）やレスポンスサイズ制限を実装しています。
  - OpenAI / J-Quants の API キーは環境変数で管理してください。コードベースは .env 自動読み込み機能を持ちますが、機密情報はリポジトリに含めないでください。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py               — 環境変数 / .env 管理と Settings
- ai/
  - __init__.py
  - news_nlp.py           — ニュース NLP スコアリング（score_news）
  - regime_detector.py    — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py     — J-Quants API クライアント（fetch/save）
  - news_collector.py     — RSS 収集・前処理
  - calendar_management.py— マーケットカレンダー管理（is_trading_day 等）
  - quality.py            — データ品質チェック
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログスキーマの定義・初期化
  - etl.py                — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py    — ファクター計算（momentum, value, volatility）
  - feature_exploration.py— 将来リターン、IC、統計サマリー等

補足
----
- OpenAI の呼び出しは gpt-4o-mini など JSON Mode を用いる設計になっています。API レスポンスの取り扱いは堅牢化していますが、API の挙動変更には注意してください。
- J-Quants API 利用時はレート制限（120 req/min）やトークン更新ロジックが組み込まれています。ID トークンは自動でリフレッシュされますが、quota や利用規約に留意してください。
- 本 README はコード（src/kabusys 以下）の公開されている設計とインターフェースに基づいて作成しています。より詳細な運用手順や CI/CD、デプロイ手順は別途ドキュメントにまとめることを推奨します。

ライセンス
---------
（ここに適用されるライセンス情報を挿入してください）

問題や質問
----------
使い方や拡張について不明点があれば、ソースコード内の docstring や logger のメッセージを参照してください。必要なら README を拡張します。