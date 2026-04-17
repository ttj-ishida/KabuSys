KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム「KabuSys」の主要モジュール群を含みます。
設計方針としては「実運用を念頭に置いた堅牢さ」と「研究用の分離（DuckDB ベース）」を重視しています。
以下はコードベースの概要・セットアップ・使い方・ディレクトリ構成のまとめです。

1. プロジェクト概要
-------------------
KabuSys は以下の主要機能を含む自動売買基盤のプロトタイプです。

- 注文発行・状態管理（ExecutionEngine、OrderManager、OrderRepository 等）
- 取引監視・リスク監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- モニタリング DB（SQLite）への永続化層（monitoring_db）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 研究用ファクター計算（DuckDB を利用したファクター計算モジュール）
- ニュース NLP による銘柄センチメント算出（OpenAI API を利用）
- 市場レジーム判定（ETF MA とマクロニュースを合成）
- 運用補助ツール（paper trading の検証レポート生成、Streamlit ダッシュボード等）

設計上の重要点：
- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB と分離（デフォルト data/paper_trading.db）。
- 監視は環境にかかわらず本番 sqlite_path を使用する設計（run_monitoring）。
- .env / 環境変数で設定を行い Settings クラスで一元管理。

2. 機能一覧
------------
主な機能（モジュール単位）：

- kabusys.config
  - 環境変数/.env 読み込みと Settings クラス（J-Quants, kabu API, DB パス, 環境種別 等）
- kabusys.execution
  - ExecutionEngine 起動、OrderManager、Reconciler（再起動時の自動復旧）
- kabusys.monitoring
  - SystemMonitor（プロセス・CPU/メモリ/ディスク/データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（条件達成で kill.flag を書いて実行停止）
  - AlertManager（LINE へ通知）
  - MonitoringEngine（各 Monitor を束ねるポーリングループ）
  - streamlit_dashboard（監視ダッシュボード）
- kabusys.portfolio
  - 候補選定・重み計算・ポジションサイズ計算・セクターキャップ適用・レジーム乗数
- kabusys.research
  - ファクター計算（momentum/value/volatility）と特徴量評価（IC 等）
- kabusys.ai
  - news_nlp（ニュースを集約して OpenAI でセンチメント算出、ai_scores テーブルへ書込）
  - regime_detector（ETF MA + マクロニュースで市場レジーム判定）
- tools
  - paper_verification_report（Paper Trading の検証レポート生成）

3. セットアップ手順
-------------------
前提：
- Python 3.9+（ソース中の typing, zone aware などを考慮）
- SQLite（標準ライブラリ）
- DuckDB（Python モジュール）
- psutil, requests, openai, streamlit（使用機能に応じて）

推奨の仮想環境作成例（Unix 系）：
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作る・有効化
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール（requirements.txt が無い場合は個別インストール）
   pip install duckdb psutil requests openai streamlit

4. data ディレクトリを作成
   mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env を作成するか OS 環境変数で設定します。
   - 自動ロードはデフォルトで有効（.env → .env.local の順）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（代表）：
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合に必須）
- PAPER_FILL_MODE: paper trading での約定動作（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG, INFO,...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で利用。デフォルト 60）

6. 起動前の注意
- run_execution はデフォルトで settings.kill_flag_clear_on_start を見るかもしれないため、必要に応じて kill.flag を削除してください。
- 高優先度設定（set_process_priority("high")）は psutil のアクセス制限を受けることがあります（権限が必要な場合あり）。

4. 使い方
----------

実行スクリプト（モジュール実行）：
- 監視ループ（Monitoring）を起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に settings.sqlite_path を使います（環境に関係なく本番 DB を参照する仕様）。

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と完全に分離されます。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します（run_monitoring / run_execution 両方で参照）。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB パスを直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視表示）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

停止・フラグ管理：
- data/stop_requested.flag: run_monitoring / run_execution の起動ループで参照され、存在するとループを終了します。運用側で作成してプロセスに終了を促すために使えます。
- data/kill.flag: KillSwitch（RiskMonitor 等）によって書き込まれる停止シグナル。ExecutionEngine は kill.flag の存在により起動・継続を抑止します。必要なら手動で削除してください。

監視・アラート：
- AlertManager は LINE Messaging API に対する一方的プッシュ通知を行います（token / user が空なら送信は行わずログ出力）。
- 冷却時間（cooldown）により同一カテゴリの通知は一定時間抑制されます。

AI 機能：
- news_nlp.score_news と regime_detector.score_regime は OPENAI_API_KEY を要求します。キー未設定時は ValueError が発生します（例外ではなく、明示的にエラーになります）。
- LLM 呼び出しはリトライ・バックオフ・レスポンス検証を行う設計です（429/ネットワーク/5xx に対応）。

5. ディレクトリ構成（主なファイル）
---------------------------------
（src/kabusys をルートとした主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境・.env 読み込み、Settings クラス
  - run_monitoring.py
    - SystemMonitor をポーリングする起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト

- src/kabusys/monitoring/
  - monitoring_db.py
    - SQLite スキーマ初期化・MonitoringDB クラス（永続化層）
  - monitoring_engine.py
    - 各 Monitor を束ねるポーリングエンジン
  - system_monitor.py
    - システム状態・データ鮮度監視
  - trade_monitor.py
    - 注文滞留・約定異常監視
  - risk_monitor.py
    - ドローダウン・ポジション上限監視
  - kill_switch.py
    - kill.flag 作成ロジック
  - alert_manager.py
    - LINE Push 通知
  - streamlit_dashboard.py
    - Streamlit ベースの簡易ダッシュボード

- src/kabusys/execution/
  - order_manager.py
  - order_repository.py (一部は省略されているが存在)
  - reconciler.py
  - execution_engine.py
  - broker_factory / broker_api ...
  - （Reconciler は起動時の自動復旧に使用）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - process_priority.py
    - psutil を用いたプロセス優先度 / CPU affinity ユーティリティ

- その他
  - data/
    - monitoring.db（デフォルトの監視 SQLite）
    - paper_trading.db（Paper Trading 用）
    - kabusys.duckdb（DuckDB ファイル）
    - execution.pid, stop_requested.flag, kill.flag などのフラグ・PID 管理ファイル

6. 開発・運用上の注意（短く）
----------------------------
- 環境分離に注意：paper_trading を使うときは PAPER_TRADING_SQLITE_PATH を確認してください（本番 DB を上書きしない）。
- OpenAI 呼び出しはコストがかかります。テスト時はモック化（_call_openai_api のパッチ等）してください。
- set_process_priority はプラットフォーム依存の権限制限を受けます。権限不足時は warning を出してスキップします。
- DuckDB のファイルアクセスや executemany の空リスト扱いなど、バージョン依存の挙動に注意（コード内に互換処理あり）。
- 監視 DB のマイグレーション（列追加）は init_monitoring_db 内で冪等に実行されます。

7. よく使うコマンドまとめ
------------------------
- 監視起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

8. 追加情報 / 参考
------------------
- 設定は kabusys.config.Settings で集約されています。新しい環境変数を追加する場合はここを編集してください。
- DuckDB と SQLite は用途が分かれています：DuckDB は研究用の履歴クエリ（prices_daily, raw_financials 等）に、SQLite は監視ログや注文ログに使われます。
- コード内ドキュメント（docstring）に設計意図や注意点が豊富に記載されています。詳細実装やアルゴリズム（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する前提です。

以上が README 相当の概要です。必要であれば、README をリポジトリルートに追加する markdown 形式で作成しますし、.env.example のテンプレートや requirements.txt の候補を作成することもできます。どれを優先しますか？