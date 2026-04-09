README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を支援する Python ライブラリ群です。  
主に以下を提供します。

- ファクター計算・特徴量探索（DuckDB 上の履歴データに対して純粋関数で計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リスク調整（セクター上限、マーケットレジームによる資金乗数）
- ニュース NLP（OpenAI を用いたニュースのセンチメント集約）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースの LLM スコア）
- 発注エンジン周辺（OrderManager / ExecutionEngine / Reconciler 等）
- 監視（system / trade / risk の監視、SQLite 永続化、LINE 通知、Streamlit ダッシュボード）

設計方針として、ビジネスロジックは可能な限り純粋関数（副作用を持たない）に分離し、
DB 操作・API 呼び出しは専用モジュールに限定することでテスト容易性を高めています。

機能一覧
--------
主な機能（モジュール別）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily/raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・IC 計算・統計サマリ
  - zscore_normalize（kabusys.data.stats 経由）

- kabusys.portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定・重み計算
  - calc_position_sizes：株数決定（等配分・スコア加重・リスクベース）
  - apply_sector_cap / calc_regime_multiplier：セクター集中制限・レジーム乗数

- kabusys.ai
  - score_news：raw_news を OpenAI で評価して ai_scores に書き込む
  - score_regime：ETF とマクロニュースを用いて日次レジーム判定し market_regime に書き込む

- kabusys.execution
  - Broker API 抽象（Protocol）、OrderManager、ExecutionEngine、Reconciler：発注フローと自動復旧
  - 発注状態管理と DB 永続化のロジックを提供

- kabusys.monitoring
  - MonitoringDB：SQLite を使った永続層
  - SystemMonitor / TradeMonitor / RiskMonitor：各種監視ロジック
  - AlertManager：LINE Push 通知（クールダウン管理）
  - KillSwitch：kill.flag による実行停止
  - MonitoringEngine：定期ポーリング
  - streamlit_dashboard：監視用の Streamlit UI（起動方法は下記参照）

セットアップ手順
--------------
前提
- Python 3.10+（typing の union 短縮表記などを使用）
- DuckDB、psutil、requests、streamlit、openai 等の依存ライブラリ

推奨手順（一般的な例）
1. リポジトリをクローン
   - git clone <repo_url>
2. venv を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限: pip install duckdb psutil requests streamlit openai）
4. パッケージを editable インストール（開発）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（.git もしくは pyproject.toml がある場所）に .env / .env.local を置くと自動的に読み込まれます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（必須/任意）

  必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン
  - KABU_API_PASSWORD     : kabu ステーション API のパスワード

  AI 関連（OpenAI を利用する機能を使う場合必須）:
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で利用）

  通知（任意、LINE 通知を有効にする場合）:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

  データベースパス（デフォルト値あり）:
  - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
  - SQLITE_PATH           : デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH : Paper trading 用 SQLite パス（デフォルト data/paper_trading.db）

  その他:
  - KABUSYS_ENV           : development | paper_trading | live （デフォルト development）
  - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL

使い方（代表的な例）
------------------

DuckDB を用いたファクター計算（研究用途）
- Python 内で DuckDB 接続を渡して呼び出すだけです。

例:
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

ニュース NLP（OpenAI でスコアリング）
- score_news は DuckDB 接続と target_date を受け取って ai_scores テーブルへ書き込みます。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定します。

例:
from datetime import date
from kabusys.ai import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026, 3, 20), api_key="sk-...")

市場レジーム判定
- score_regime を呼ぶと market_regime テーブルに書き込みます（同様に OpenAI キーを利用）。

監視周り
- MonitoringDB を初期化:
import sqlite3
from kabusys.monitoring import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)

- Streamlit ダッシュボード起動:
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ExecutionEngine（運用用）
- ExecutionEngine は Broker 実装（BrokerAPIProtocol）、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを渡して使用します。実運用での組み立ては各環境依存（ブローカークライアント実装・DB スキーマ）なので README ではサンプルの骨組みのみ記載します。

簡易イメージ:
from kabusys.execution import ExecutionEngine, EngineConfig
# broker: BrokerAPIProtocol 実装
# repo: OrderRepository インスタンス
# risk_manager: RiskManager インスタンス
# order_manager: OrderManager インスタンス
engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=...))
engine.run_session()

注意点 / 動作仕様の抜粋
- .env のパーサは export 形式・クォート・インラインコメントなどに対応しています。
- 自動ロード順序: OS 環境変数 > .env.local > .env 。既存 OS 環境変数は保護されます。
- OpenAI 呼び出しは失敗に対してリトライやフェイルセーフのロジックがありますが、API キー未設定の場合は例外を送出します。
- kill.flag（デフォルト data/kill.flag）で ExecutionEngine の起動抑止や実行停止を行います。設定により起動時に自動クリア可能です（KILL_FLAG_CLEAR_ON_START=1）。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報／エクスポート

- config.py
  - 環境変数管理（.env 自動ロード、Settings クラス）

- portfolio/
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py        — 株数決定・集約上限の調整
  - risk_adjustment.py        — セクター上限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py        — Momentum / Volatility / Value の計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリ
  - __init__.py

- ai/
  - news_nlp.py               — raw_news を OpenAI で評価して ai_scores に書き込む
  - regime_detector.py        — ETF + マクロニュースで market_regime を判定
  - __init__.py

- monitoring/
  - monitoring_db.py          — SQLite 永続層（init + MonitoringDB）
  - system_monitor.py         — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py          — 滞留注文 / 約定異常監視
  - risk_monitor.py           — ドローダウン / ポジション上限監視
  - alert_manager.py          — LINE 通知
  - kill_switch.py            — kill.flag 管理
  - monitoring_engine.py      — 各 Monitor のポーリング合成
  - streamlit_dashboard.py    — Streamlit ダッシュボード

- execution/
  - broker_api.py             — Broker API のデータモデル / Protocol / 例外
  - order_manager.py         — Order state machine の外向き API
  - reconciler.py            — 起動時リコンシリエーション
  - execution_engine.py      — Signal Queue Pull 型の発注エンジン
  - （その他発注関連モジュール: order_repository, order_record, risk_manager 等は同ツリーに存在する想定）

- research, portfolio, ai, monitoring, execution の他に data モジュール等が存在し得ます（DuckDB パイプラインや統計ユーティリティ等）。

補足
----
- この README はコードベースの主要機能と利用方法の概要を示します。実運用ではブローカークライアント実装、OrderRepository の初期化、RiskManager の設定、DuckDB のデータ投入（prices_daily / raw_financials / raw_news 等の準備）など、環境ごとの初期作業が必要です。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑止できます。

ライセンスや貢献方法についてはリポジトリのトップレベルにある記載を参照してください。