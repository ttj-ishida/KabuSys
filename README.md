KabuSys
=======

日本株自動売買システムのライブラリ / 実行スクリプト群。  
このリポジトリは、戦略計算、ポートフォリオ構築、発注エンジン、監視／アラート、研究用ユーティリティ、AI（ニュースセンチメント）連携などを含むモジュール群で構成されています。

概要
----
KabuSys は次の機能を持つモジュール群で構成された自動売買基盤です。

- 市場データ（DuckDB）を用いたファクター計算・研究モジュール
- ポートフォリオ構築（候補選定、重み付け、ポジション決定）
- 発注処理を担う ExecutionEngine（本番 / ペーパートレードの分離）
- システム監視（CPU/メモリ/Disk、データ鮮度、発注ログ監視）と Kill Switch
- OpenAI を用いたニュース NLP（銘柄別センチメント）とレジーム判定
- 設定ウィザード・検証ツール・レポート生成スクリプト
- ロギング・プロセス優先度設定などのユーティリティ

主な機能一覧
--------------
- kabusys.config: .env 自動読み込み、Settings クラス（環境変数ラップ）
- config_setup: 対話式ウィザードで .env を作成 / 更新
- validate_config: .env と config/*.yaml の整合性チェック CLI
- run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録
- run_monitoring: SystemMonitor をポーリングして system_status 等を記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- monitoring: RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager 統合
- monitoring.monitoring_db: SQLite ベースの永続化レイヤ（監視ログ、trade_logs、risk_logs 等）
- portfolio: 候補選定、配分計算、リスク調整、ポジションサイジング
- research: ファクター計算（momentum/value/volatility）と特徴量解析ツール
- ai.news_nlp / ai.regime_detector: OpenAI と連携したニュースセンチメント / レジーム判定
- tools.paper_verification_report: ペーパートレード検証レポート生成スクリプト

セットアップ手順
----------------
前提:
- Python 3.9+（適宜プロジェクトの pyproject.toml を参照）
- DuckDB、psutil、openai（必要機能に応じて）などが必要

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
   （本コードベースでは主に duckdb, psutil, openai, PyYAML が必要または推奨）

   例:
   - pip install duckdb psutil openai PyYAML

4. ディレクトリ作成
   - data/ と logs/ は実行時に自動作成される場合がありますが、必要に応じて作成:
     - mkdir -p data logs

5. .env を作成
   - 対話式: python -m kabusys.config_setup
   - 手動: リポジトリルートに .env を配置（必須環境変数は下記参照）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

推奨 / 主要な環境変数
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- LOG_LEVEL: ログレベル（INFO デフォルト）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" or "1"）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

使い方（主なコマンド）
--------------------

1) 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - ウィザード完了後、.env が生成されます。

2) 設定検証
   - python -m kabusys.validate_config
   - 警告を fail として扱う: python -m kabusys.validate_config --strict

3) 発注エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
     - 停止シグナル: data/stop_requested.flag（存在すると起動を停止または停止処理を行います）
     - 実行中の PID ファイル: data/execution.pid（pid ファイルのパスは Settings で指定可能）

4) 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
   - 監視は Settings の sqlite_path（monitoring DB）を使用（環境にかかわらず本番 DB パスを参照）
   - 停止トリガー: data/stop_requested.flag を作成するとループを抜けます

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

6) AI / レジーム判定（ライブラリ関数）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（DuckDBPyConnection）を渡し、target_date のニューススコアを ai_scores テーブルへ書き込む
     - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへ判定結果を書き込む

ログとローテーション
-------------------
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一されています。
- デフォルトでは logs/<app_name>.log に日次ローテーション（30 日分保存）
- LOG_DIR 環境変数でログディレクトリを変更可能
- コンソール出力は標準出力（stdout）へ出力されます

停止 / Kill Switch
-----------------
- KillSwitch: リスク条件（ドロウダウン、ポジション上限超過等）に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促す仕組みがあります。
- 手動停止:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して終了します。
- 起動時挙動:
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag を自動クリアします（本番では "0" 推奨）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                    — Settings と .env 自動ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                — ニュースセンチメント取得
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                    — ExecutionEngine 関連（broker, order_manager 等）
  - data/                         — データファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
  - logs/                         — デフォルトのログ出力先

重要な実装上の注意点
--------------------
- 環境（KABUSYS_ENV）:
  - development: テスト用（発注を行わない等の差分がある想定）
  - paper_trading: 実際の発注は行わず、MockBrokerClient により data/paper_trading.db にログを保存（本番 DB と分離）
  - live: 実際の発注を行うモード。設定ミスは重大な影響を与えるため validate_config での注意が必要
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と一部カラム追加（マイグレーション）を行います
- OpenAI 連携:
  - AI モジュールは OPENAI_API_KEY を必要とします。API エラー時はフェイルセーフとして部分的に無害なデフォルト（0.0）にフォールバックする実装が多く採用されています
- テスト性:
  - OpenAI への呼び出し関数はモジュール単位で切り替えやパッチしやすい設計になっています（ユニットテストでモック可能）

典型的な起動フロー（例）
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. 必要なデータベースを用意（DuckDB ファイルをロード / 準備）
4. 監視プロセスを起動（python -m kabusys.run_monitoring）
5. 発注エンジンを起動（python -m kabusys.run_execution）

追加情報 / 開発メモ
------------------
- settings オブジェクト（kabusys.config.settings）を使うことで、環境変数への直接参照を避けられます
- ロギングや優先度設定は各起動スクリプトの先頭で統一的に適用されます
- 各モジュールは可能な限り副作用を少なくする設計（例: research モジュールは DuckDB を読み取り専用で使用し、発注 API へはアクセスしない）

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を記載してください）

問い合わせ / バグ報告
--------------------
Issues に記載してください。

---

この README はリポジトリ内の主要スクリプト / モジュールを元に作成しています。実行前に python 環境および依存ライブラリのインストール、.env の正確な設定を必ず行ってください。