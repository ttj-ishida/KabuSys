README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視用ライブラリ群と起動スクリプトの集合です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ファクター計算・リサーチ、ポートフォリオ構築、AI ベースのニュースセンチメント評価などを含みます。  
設計方針としては「本番とペーパートレードの分離」「ルックアヘッドバイアスの回避」「フェイルセーフ（API 失敗時はスキップ）」を重視しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV により paper_trading（MockBroker を使用）/ live（本番） を切替可能
  - Paper Trading は専用 SQLite（デフォルト: data/paper_trading.db）に記録
  - プロセス優先度の設定・PID ファイル管理・停止フラグ対応

- Monitoring（run_monitoring / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）監視、データ鮮度チェック
  - 注文ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（条件達成で data/kill.flag を書き込み Execution を停止）
  - アラート送信フック（AlertManager 経由）

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定、重み付け（等配分・スコア加重）、ポジションサイズ算出、セクター上限・レジーム調整

- リサーチ / ファクター計算（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を想定）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores へ書込）
  - regime_detector: MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
  - OpenAI API 呼び出しは安全にリトライ/バリデーションを行う

- ユーティリティ
  - .env ウィザード（config_setup）、設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（console+日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ
-----------
前提
- Python 3.10+ を推奨（typing 表現等に依存）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で推奨）
これらはプロジェクトに requirements.txt があればそれを使ってください。無ければ手動でインストールします:
  pip install duckdb psutil openai PyYAML

環境変数 / .env
- プロジェクトルートの .env/.env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - LOG_LEVEL（DEBUG/INFO/...）
  - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START など

.env を対話的に作る（推奨）
  python -m kabusys.config_setup
このウィザードは .env の作成・更新を支援します。

設定検証
  python -m kabusys.validate_config
--strict を付けると警告も失敗扱いになります:
  python -m kabusys.validate_config --strict

データディレクトリとログ
- デフォルトで data/ と logs/ を使用します。権限やディスク容量に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。

使い方（起動・ツール）
--------------------

1) 監視ループを起動（Monitoring）
- 簡単起動:
  python -m kabusys.run_monitoring
- ポーリング間隔を env で上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は Settings から取得する SQLite パス（monitoring は常に本番 sqlite_path を使用）を開きます。
- 停止: プロジェクトルートの data/stop_requested.flag を作成するとループは終了します。

2) 実行エンジンを起動（Execution）
- 起動:
  python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、Paper Trading 用 DB（data/paper_trading.db）に書き込みます。
- 起動時に data/stop_requested.flag が存在すると起動しません。
- 実行中に監視側で kill.flag が書かれるとエンジンが停止されます（Kill Switch）。

3) Paper Trading 検証レポート生成
- コマンド:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。別 DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite

4) AI 関連（ニューススコア・レジーム）
- OpenAI API キーが必要:
  export OPENAI_API_KEY="sk-..."
- news_nlp の利用例（プログラムから）:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key=None)  # api_key None → 環境変数参照
- 同様に regime_detector.score_regime を使います。

重要な環境変数・設定のメモ
- KABUSYS_ENV: development | paper_trading | live（不正値は例外）
- PAPER_FILL_MODE（paper_trading 用 MockBroker の fill 動作）:
  instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に kill.flag を自動でクリアします（本番では 0 を推奨）
- LOG_DIR / LOG_LEVEL によりログの出力先・レベルを制御

停止・Kill 機構
- run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を監視しています。停止を要求するにはそのファイルを作成してください。
- Kill Switch は設定された閾値（ドローダウンやポジション上限）に達した際に data/kill.flag を作成します。ExecutionEngine は kill.flag を見て停止します。

監視 DB（SQLite）スキーマの概略
- system_status: CPU/MEM/DISK/プロセス正常フラグ 等
- trade_logs: 発注・約定イベントログ（latency_ms カラムあり）
- positions: 現在ポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベントログ
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py        — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py        — （trade 関連監視ロジック）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/                — 発注エンジン関連（Engine, BrokerFactory, OrderManager...）
- portfolio/                — portfolio_builder, position_sizing, risk_adjustment
- research/                 — factor_research, feature_exploration, __init__.py
- ai/
  - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores へ書込
  - regime_detector.py
- data/                     — データファイル（実行時に生成される例: monitoring.db, paper_trading.db）
- tools/
  - paper_verification_report.py

注意点 / トラブルシュート
------------------------
- 権限: data/ と logs/ の作成・書込み権限を確認してください。ログディレクトリが作れない場合はコンソールのみ出力されます。
- psutil を使った優先度設定は権限が必要な場合があります。AccessDenied の場合は警告ログが出て処理は継続します。
- DuckDB / SQLite 接続に関連する互換性問題（executemany の空リスト等）に注意。コード内に回避処理がありますが古いバージョンだと挙動が異なる場合があります。
- OpenAI を使う機能は API キーとネットワークが必要。API の応答に依存するため失敗時はログを確認してください（リトライ／フォールバック戦略あり）。
- 本番運用前に必ず python -m kabusys.validate_config を実行して設定を確認してください。

ライセンス・バージョン
---------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（初期リリース）です。  
ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

補足
----
- ここに記載したコマンドはプロジェクトルート（src を含むプロジェクトルート）で実行してください。  
- さらに詳細な API 使用方法や内部アルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）がドキュメントとしてリポジトリに含まれていることを想定しています。必要に応じてそれらのドキュメントを参照してください。

もし README に追加したい具体的な実行例や .env のサンプル、または各モジュールのより詳細な API ドキュメント（関数一覧・引数説明など）が必要であればお知らせください。