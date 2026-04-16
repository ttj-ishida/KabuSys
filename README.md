KabuSys — 日本株自動売買システム（簡易 README）
====================================

概要
----
KabuSys は日本株向けの自動売買 / 監視 / 研究ツール群を含むコードベースです。
主な要素は以下の通りです。

- ExecutionEngine: 注文発行・状態管理・リスク制御（本番 / Paper Trading 対応）
- Monitoring: システム稼働・注文状態・リスク（ドローダウン / ポジション上限）監視、LINE へのアラート、Streamlit ダッシュボード
- Portfolio: 候補選定・配分・株数決定・リスク調整（純粋関数で実装）
- Research / AI: ファクター計算、将来リターン、LLM を利用したニュースセンチメント（OpenAI）
- Tools: Paper Trading の検証レポート生成スクリプト 等

主な特徴
--------
- 本番 / 開発 / Paper Trading（分離 DB）を環境変数で切替可能（KABUSYS_ENV）
- 監視ログは SQLite（data/monitoring.db 等）へ永続化。DuckDB は時系列データ分析用途に使用
- Paper Trading 時は MockBrokerClient を用い、本番 DB と完全分離して data/paper_trading.db に記録
- OpenAI を用いてニュースセンチメントやレジーム判定を行う（API キー必要）
- kill.flag / stop_requested.flag を用いたプロセス停止シグナリング、pid ファイル管理
- Streamlit による監視ダッシュボードを提供

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo_url>

2. Python 環境構築
   - 推奨: pyenv / venv などで仮想環境を作成
   - Python 3.10 以上を想定（コードは typing | None 型などを使用）

3. 依存パッケージをインストール
   - 明示的な requirements.txt は含まれていませんが、以下パッケージが必要になります（少なくともこれら）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード用)
   - 例:
     pip install duckdb psutil requests openai streamlit

   - 開発時はリポジトリルートでパッケージを編集インストールすると便利:
     pip install -e src

   - もしパッケージをインストールせずに直接実行する場合は PYTHONPATH を通す:
     PYTHONPATH=src python -m kabusys.run_monitoring

4. data ディレクトリ作成（必要に応じて）
   mkdir -p data

5. 環境変数設定
   - .env / .env.local を利用可能（config.Settings モジュールが自動読み込みを試みます）。
   - 必須な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要な環境変数（説明は後述）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
     - OPENAI_API_KEY: OpenAI API キー
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
基本的な起動方法（パッケージをインストールしている前提）:

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に保存されます。
    - 起動時、KILL フラグ / stop フラグが立っていれば起動を中止します。
    - 実行中は data/execution.pid に PID を書きます。run_execution は内部で stop_requested.flag を監視して安全に停止します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
    - 監視は Settings.sqlite_path（監視 DB）を使って永続化します（環境にかかわらず本番 sqlite_path を使う実装）。
    - stop_requested.flag を検知すると終了します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB に read-only URI を付与して開く想定です（MonitoringEngine が先に起動していること）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能（デフォルト data/paper_trading.db）

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用可能
  - OPENAI_API_KEY が必要。API 呼び出しは再試行やフォールバックを備えた実装になっています。

停止 / フラグ
---------------
- stop_requested.flag:
  - run_monitoring / run_execution が監視しているフラグファイル（data/stop_requested.flag）。存在するとループを終了します。
- kill.flag:
  - KillSwitch は重大条件（ドローダウン、ポジション上限など）で data/kill.flag に理由を記入して ExecutionEngine 停止を促します。
  - Settings.kill_flag_clear_on_start が True の場合、起動時に kill.flag を自動でクリアできます。

主な環境変数（Settings より抜粋）
-----------------------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH: Execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag をクリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- LOG_LEVEL: ログレベル（例: INFO）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - …（発注 / ブローカー関連）
- monitoring/
  - monitoring_db.py        — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意
------------
- Paper Trading は本番 DB と分離されていますが、必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API 等の外部 API 呼び出しにはコストとレイテンシが発生します。API キーは安全に管理してください。
- process priority / cpu affinity の設定はプラットフォームに依存します。権限不足で失敗することがありますが、ライブラリは失敗をログに残してスキップする挙動です。
- 監視機能は稼働率・滞留注文・約定異常などを自動で記録し、条件を満たすと kill.flag を発行します。kill.flag を手動で消す場合は内容を確認のうえ clear してください。
- DB スキーマの簡単なマイグレーションロジックが含まれており、既存 DB に列が無ければ追加します。

開発 / 貢献
------------
- コードはモジュール化されており、ユニットテスト（別途作成）が適用しやすい設計です。
- プルリクエスト・イシューは歓迎します。設計ドキュメント（PortfolioConstruction.md 等）に基づく変更を推奨します。

問い合わせ
----------
- 実運用上の設定や導入に関する質問は、リポジトリの issue またはプロジェクト管理者にお問い合わせください。

付録 — 早見コマンド
-------------------
- 起動: python -m kabusys.run_execution
- 監視: python -m kabusys.run_monitoring
- ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であればサンプル .env ファイル例や詳細な運用手順 (systemd / Supervisor 用 unit ファイル例など) を追記します。どの情報がほしいか教えてください。