KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視基盤のコンポーネント群です。  
主に以下を提供します。

- ファクター計算・リサーチ（DuckDB 上の市場データを使った純粋関数群）
- ポートフォリオ構築（候補選定・重み付け・リスク補正・株数計算）
- 実行層（注文管理・ブローカー API 抽象・リコンシリエーション・ExecutionEngine）
- 監視層（システム/注文/リスク監視、Alert 通知、Streamlit ダッシュボード）
- AI ユーティリティ（ニュースのセンチメント集計、マーケットレジーム判定）  
- 環境変数/設定管理（.env 自動読み込み / Settings クラス）

設計方針の要点
- 多くのロジックは純粋関数（副作用なし）で実装され、テストしやすい構造
- DuckDB / SQLite を利用して履歴データ・メタデータを保持
- OpenAI（gpt-4o-mini）を利用した NLP 部分は API 失敗時にフェイルセーフで継続
- 起動時の自動復旧（Reconciler）や kill.flag による安全停止など運用重視の設計

主な機能一覧
----------------
- 環境設定
  - settings（kabusys.config.Settings）経由で環境変数を取得
  - .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml で探索）
- ポートフォリオ構築（kabusys.portfolio）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（リスクベース・等分配・スコア配分）
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value（DuckDB の prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）
- AI（kabusys.ai）
  - score_news: raw_news を集約して OpenAI に投げ、ai_scores テーブルへ保存
  - score_regime: ETF 1321 の MA 乖離とマクロニュースの LLM 結果でレジーム判定
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）によるログ保存・スキーマ初期化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringEngine（ループ実行）と Streamlit ダッシュボード
- 実行（kabusys.execution）
  - BrokerAPI Protocol 型・データモデル（OrderRequest / OrderStatus / Position 等）
  - OrderManager（DB とブローカー呼び出しの安全な連携）
  - ExecutionEngine（シグナル処理 / WebSocket push ドレイン / kill_switch）
  - Reconciler（再起動時の注文・ポジション同期）

セットアップ手順
----------------
前提
- Python 3.10+（| 型ヒントや一部構文を使用）
- システムに DuckDB / SQLite 利用可能

1. リポジトリをクローン
   git clone <this-repo>

2. 仮想環境作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール（最小）
   pip install duckdb openai requests psutil streamlit

   ※ 実環境では requirements.txt を作成して pip install -r するのを推奨。

4. 環境変数（.env）を用意
   プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
   自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（主な例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API を使う場合に必要（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE Push）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — Monitoring DB（デフォルト data/monitoring.db）
- PAPER_FILL_MODE — paper trading のフィルモード（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視設定
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL

使い方（簡易例）
----------------

1) Settings を使う（コードから）
from kabusys.config import settings
print(settings.duckdb_path)

2) DuckDB を使ったファクター計算例
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect(str(settings.duckdb_path))
res = calc_momentum(conn, date(2026, 3, 20))
print(res[:5])

3) AI ニューススコア（OpenAI API キーが必要）
from datetime import date
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20), api_key="sk-...")

5) 監視 DB 初期化（SQLite）
import sqlite3
from kabusys.monitoring import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)

6) Streamlit ダッシュボード起動
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

7) ExecutionEngine を使った運用（構成要素の提供は実装者側）
- BrokerAPI の具象実装（kabuステーションクライアント等）を作成して Protocol を満たす
- OrderRepository（SQLite）や RiskManager、OrderManager、Reconciler を組み合わせて Engine をインスタンス化
- Engine.run_session() をコントロールして実行

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/.env 管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py                — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py         — レジーム判定（MA + マクロニュース）
- portfolio/
  - __init__.py
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py        — 株数計算・スケールダウン
  - risk_adjustment.py        — セクター制限・レジーム乗数
- research/
  - __init__.py
  - factor_research.py        — momentum/value/volatility 計算
  - feature_exploration.py    — forward returns / IC / summary
- monitoring/
  - __init__.py
  - monitoring_db.py          — MonitoringDB スキーマ / 永続化
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py             — ブローカー API の Protocol / データモデル / 例外
  - order_manager.py          — 注文作成・送出・同期・キャンセル
  - reconciler.py             — 起動時リコンシリエーション
  - execution_engine.py       — Signal-driven 発注エンジン
  - (その他: order_repository, order_record, risk_manager 等 想定)
- monitoring/ (上記)
- research/ (上記)
- portfolio/ (上記)
（注）プロジェクトに参照される kabusys.data や一部のモジュールは別ファイルで提供される想定です。

運用上の注意
- OpenAI を使う処理は API キーが必須。API 呼び出しはレート制限や一時的な障害が発生するため
  内部で指数バックオフやフォールバック（スコア=0.0）を行いますが、キーや課金管理は注意してください。
- .env 自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。テストでの自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine は PID ファイル（デフォルト data/execution.pid）と kill.flag（data/kill.flag）を用いて起動制御・安全停止を行います。起動前に既存の kill.flag を確認してください（設定により起動時に自動クリア可）。

テスト / 開発時のヒント
- 多くの関数は副作用がなく単体テストしやすい（DuckDB コネクションを渡して結果を検証）。
- OpenAI 呼び出しはモック化しやすく、モジュール内で _call_openai_api を patch してテスト可能。
- MonitoringDB.init_monitoring_db() は冪等（既存スキーマを壊さない）なのでテストデータセットの作成に便利。

ライセンス / 貢献
----------------
- 本 README はコードベースから抜粋した設計・使用方法を要約したものです。実運用前に各設定・DB スキーマ・外部依存の挙動を十分テストしてください。
- 貢献や修正は Pull Request を歓迎します。開発ルールやコーディング規約があれば別途 CONTRIBUTING.md を参照してください。

---  
質問や README に追加してほしい具体的な項目（例: サンプル .env.example、requirements.txt、実行時のコマンド一覧など）があれば教えてください。必要に応じて追記します。