KabuSys — 日本株自動売買システム (README)
==================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。市場データの解析（ファクター計算・特徴量探索）、ポートフォリオ構築、発注実行、実行監視、Paper Trading 検証、さらにニュースを利用した AI ベースのセンチメント評価までを含むモジュール群で構成されています。本リポジトリはライブラリとして利用可能なほか、実行エントリポイント（監視ループ／実行エンジン／ダッシュボード／レポート生成）を提供します。

主な機能
--------
- データ調査・研究
  - ファクター（Momentum / Volatility / Value 等）計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析
- ポートフォリオ構築
  - シグナルの候補選定、等配分/スコア加重の重み計算（kabusys.portfolio）
  - リスク調整（セクター上限適用、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- 実行（Execution）
  - ブローカーファクトリ、注文マネジメント、リコンシリエーション（起動時の復旧）
  - Paper Trading モード（本番 DB と分離された専用 SQLite を利用）
- 監視（Monitoring）
  - システム状態・データ鮮度監視、注文の滞留・約定異常検出、ドローダウン監視
  - LINE によるアラート（AlertManager）
  - Kill Switch（閾値超過時に停止フラグを書き込む）
  - Streamlit による監視ダッシュボード
- AI 統合
  - ニュース記事を OpenAI（gpt-4o-mini）で評価し銘柄別スコアを生成（kabusys.ai）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（CSV/DB からメトリクスを集計）

事前準備（依存関係）
-------------------
推奨 Python バージョン: 3.10+（型注釈や一部挙動に依存）

必須パッケージ例（pip）:
- duckdb
- openai
- psutil
- requests
- streamlit

インストール例:
- pip install duckdb openai psutil requests streamlit

SQLite は標準ライブラリ（sqlite3）を使用します。

設定（環境変数）
----------------
このプロジェクトは .env /.env.local または環境変数から設定を読み込みます（自動ロードが有効な場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表例とデフォルト）:
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（任意）
- LINE_USER_ID: LINE Push 送信先ユーザー ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

セットアップ手順
---------------
1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb openai psutil requests streamlit
   （必要に応じて requirements.txt を作成して pip install -r で管理）
4. data ディレクトリを作成（実行時に自動作成されることもあります）
   - mkdir -p data
5. .env を作成し必要な環境変数を設定（.env.example があれば参照）
   - 例:
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
6. DuckDB と SQLite の初期 DB は起動スクリプトで必要に応じて初期化されます。

使い方（コマンド例）
------------------

監視ループを起動
- MONITOR_POLL_INTERVAL を指定（デフォルト 60 秒）
- python -m kabusys.run_monitoring
  - 補足: run_monitoring は常に本番用 sqlite_path を使用します（監視は本番 DB を参照）。

実行エンジンを起動（発注処理）
- KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
- python -m kabusys.run_execution

Streamlit ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - --db オプションで読み取り専用で監視 DB を指定可能

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

AI / レジーム判定・ニューススコアリング（ライブラリ呼び出し）
- OpenAI APIキーが必要（引数または OPENAI_API_KEY 環境変数）
- 例（Python REPL / スクリプト内）:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - score_news(conn, target_date, api_key="...")
  - score_regime(conn, target_date, api_key="...")

停止方法（フラグ）
- プロセス停止要求: data/stop_requested.flag を作成すると run_monitoring/run_execution のループが安全に終了します（起動スクリプトが該当ファイルの存在をチェックします）。
- ExecutionEngine の強制停止トリガ（Kill Switch）: kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を作成すると ExecutionEngine に停止シグナルが送られます。KillSwitch は自動でファイル書き込みするユーティリティもあるため通常は手動で書く必要はありません。

設定の注意点・補足
------------------
- Settings クラス（kabusys.config.Settings）で多数の設定をラップしています。不足する必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は起動時に ValueError を出します。
- Paper Trading モードは本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH）。
- MONITOR_POLL_INTERVAL 環境変数は整数（秒）で指定。1 秒未満や非数値は無視されデフォルトにフォールバックします。
- set_process_priority は psutil を使って優先度をセットします。権限不足や未対応 OS の場合は警告が出てスキップされます。
- OpenAI 呼び出しはリトライロジック（指数バックオフ）やレスポンス検証を含む実装になっており、API 失敗時はフェイルセーフ（ゼロスコアなど）にフォールバックする箇所があります。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                            — 環境変数/設定管理
- run_monitoring.py                    — 監視ポーリングループ起動スクリプト
- run_execution.py                     — ExecutionEngine 起動スクリプト

モジュール群:
- ai/
  - news_nlp.py                         — ニュースの LLM スコアリング
  - regime_detector.py                  — 市場レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py                    — SQLite 監視 DB 層（スキーマ定義 + CRUD）
  - system_monitor.py                   — システム状態・データ鮮度監視
  - trade_monitor.py                    — 注文滞留・約定異常監視
  - risk_monitor.py                     — ドローダウン・ポジション上限監視
  - kill_switch.py                       — kill.flag 書き込みユーティリティ
  - alert_manager.py                    — LINE Push 通知
  - monitoring_engine.py                — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py              — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ...
- portfolio/
  - portfolio_builder.py                — 候補選定・重み計算
  - position_sizing.py                  — 株数決定・丸めロジック
  - risk_adjustment.py                  — セクターキャップ・レジーム乗数
- research/
  - factor_research.py                  — ファクター計算（Momentum/Volatility/Value）
  - feature_exploration.py              — 将来リターン・IC・統計サマリ等
- tools/
  - paper_verification_report.py        — Paper Trading 検証レポート
- utils/
  - process_priority.py                 — プロセス優先度 / CPU affinity ユーティリティ
- data/                                  — （実行時に利用される DB/フラグ等）

開発者向けメモ / トラブルシュート
-----------------------------------
- SQLite / DuckDB ファイルのパスは Settings で制御されます。複数環境（development / paper_trading / live）を使い分けるときは環境変数を適切に設定してください。
- psutil の優先度設定は権限に依存します。権限不足のログ警告が出た場合は無視しても安全です。
- OpenAI 関連の処理は API 呼び出しの失敗に対して耐性を持つよう作られていますが、API キーが未設定だと例外になります。ローカル検証時はダミーのキーやモック関数で代替してください。
- streamlit ダッシュボードは SQLite を read-only モードで開くことを推奨します（--db に file:// パス + ?mode=ro を指定することで読み取り専用で開く実装例あり）。

ライセンス・貢献
----------------
本リポジトリのライセンスや貢献フローは（必要に応じて）プロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください。

以上がこのコードベースの概要と主要な使い方です。特定の機能やモジュールについて詳しいドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）があれば、それに従って設定・運用してください。必要であれば README を拡張してコマンドサンプルや .env.example を追加できます。