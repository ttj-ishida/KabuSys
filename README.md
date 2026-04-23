KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤です。本コードベースは以下の主要機能を提供します。

- 実行エンジン (ExecutionEngine): 注文管理、ブローカークライアント連携、リスク管理、約定の照合
- 監視（Monitoring）: システム状態・注文・リスクの定期チェック、Kill Switch（停止フラグ）発動
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限
- 研究（Research）: ファクター計算、将来リターン、IC 計算など（DuckDB を用いた分析）
- AI モジュール: ニュースを LLM（OpenAI）でセンチメント評価 → ai_scores へ保存、レジーム判定
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度設定
- 付帯ツール: Paper Trading 検証レポート生成スクリプト 等

主な機能一覧
--------------
- run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV による paper/live 切替。paper_trading 時は MockBrokerClient を使用し DB を分離）
- run_monitoring: SystemMonitor を周期的に実行する起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定）
- config_setup: 対話式ウィザードで .env を作成 / 更新
- validate_config: .env と config/*.yaml の検査（--strict で警告を FAIL 扱いに可能）
- monitoring DB レイヤー: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / AlertManager による統合監視
- portfolio モジュール: 銘柄選定、重み算出、単元株丸め、セクター上限、レジーム乗数
- research モジュール: モメンタム / ボラティリティ / バリュー等のファクター計算、特徴量解析、IC 計算
- ai モジュール: news_nlp（OpenAI で銘柄別センチメント算出）、regime_detector（MA + マクロセンチメントでレジーム判定）
- tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成立率・レイテンシなど）

セットアップ手順
----------------
1. 前提
   - Python 3.10 以上（型アノテーションで PEP 604 等を使用）
   - SQLite は標準ライブラリで利用
   - 必要パッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 推奨: 仮想環境を作成する (venv / poetry / pipenv 等)

2. リポジトリを取得し、仮想環境を有効化
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - 例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. .env の準備（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants トークン、Kabu API パスワード、データベースパス等を設定
   - 生成された .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - 本番投入前は --strict モードで警告を FAIL 扱いにすることを推奨:
     python -m kabusys.validate_config --strict

6. データディレクトリ（必要に応じて）
   - デフォルト DB / ログパス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可)
     - SQLite (monitoring): data/monitoring.db (SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - ログ: logs/（LOG_DIR で変更可）
   - ログディレクトリは自動作成されますが、権限や配置を確認してください

使い方（主なコマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も異常扱いで exit(1)

- ExecutionEngine を起動（本番 / ペーパートレード混在）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します
  - 停止は data/stop_requested.flag を作成することで行います（Kill Flag は別に存在します）
  - 実行時に data/execution.pid が使用されます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を参照して監視ログを記録します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI / 研究モジュール（ライブラリ関数として利用）
  - ai の機能は Python API として利用できます（例: kabusys.ai.score_news）
  - OpenAI API を利用する関数は OPENAI_API_KEY を参照するか、api_key 引数で渡してください
  - 例（スクリプト内で）:
    from openai import OpenAI
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")

ログ / ロギング
---------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一
- デフォルト出力:
  - コンソール (stdout)
  - 日次ローテーションファイル: logs/<app_name>.log（30日分保持）
- ログレベルは環境変数 LOG_LEVEL（DEBUG/INFO/...）または引数で設定可能
- ログディレクトリは LOG_DIR 環境変数で変更可能

重要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI モジュール利用時必須）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアを防ぐ設定。live 環境で 1 は危険）

安全関連の注意
--------------
- KABUSYS_ENV=live（本番）設定時は特に注意してください。validate_config は live 時に追加警告を出します。
- .env に秘密情報（API キー・パスワード）を保存しますが、絶対にバージョン管理にコミットしないでください。
- Kill Switch / stop flag による停止挙動を理解してから運用してください（data/kill.flag / data/stop_requested.flag 等）。

ディレクトリ構成（抜粋）
------------------------
プロジェクトの主要なファイル・モジュール構成例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          -- .env 対話式ウィザード
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       -- SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py      -- CPU/MEM/DISK / データ鮮度 / プロセス生存チェック
    - risk_monitor.py        -- ドローダウン・ポジション上限監視
    - kill_switch.py         -- KillFlag 管理
    - monitoring_engine.py   -- 各 Monitor を束ねるエンジン
    - trade_monitor.py       -- （注文関連監視、参照あり）
    - alert_manager.py       -- （LINE 等への通知管理、参照あり）
  - execution/
    - execution_engine.py    -- 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py      -- BrokerClientFactory（環境に応じたクライアント生成）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はリポジトリ内の主要ファイルを抜粋しています）

開発・拡張メモ
----------------
- DuckDB を分析用に採用しており、research/ モジュールは DuckDB 接続を受けて SQL と Python を組み合わせて計算します。
- AI（OpenAI）呼び出しはリトライやレスポンス検証を用いた堅牢化が施されています。API キーの管理に注意してください。
- 本番運用では KILL_FLAG_CLEAR_ON_START を 0 に設定し、監視・アラート設定を十分検証してください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動読み込みを抑制できます。

補足
----
- この README はソースコードの主要部分に基づいた概要・運用ガイドです。詳細な API ドキュメントや各モジュールの設計資料（PortfolioConstruction.md, StrategyModel.md 等）があればそちらも併せて参照してください。