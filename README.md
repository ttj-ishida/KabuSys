# KabuSys

日本株自動売買システムの主要モジュール群をまとめたリポジトリ（ライブラリ & 起動スクリプト群）。

この README はコードベース（src/kabusys 以下）に基づき作成しています。実行前に .env を作成し、必要な依存ライブラリをインストールしてください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能群を提供します：

- 発注エンジン（ExecutionEngine）と注文管理
- 監視（Monitoring）：システム状態、注文状況、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC、統計サマリー）
- AI連携（ニュースセンチメント評価、レジーム判定） — OpenAI を利用
- ツール類（ペーパートレード検証レポートなど）
- 設定管理と検証（.env ウィザード / validate_config）

設計上の特徴：
- 環境変数で挙動を切替（KABUSYS_ENV = development | paper_trading | live）
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用に利用、SQLite を監視・ログ用に利用
- ログは標準出力 + 日次ローテートファイル（logs/<app>.log）

---

## 機能一覧（抜粋）

- 設定管理
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 起動スクリプト
  - 監視ループ: python -m kabusys.run_monitoring
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（秒、デフォルト 60）
    - 監視は常に本番用 sqlite_path を使用
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、専用 DB に記録
- 監視（monitoring/）
  - SystemMonitor: CPU/Mem/Disk、データ鮮度、プロセス生存確認
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件を満たせば data/kill.flag に理由を書き込み、ExecutionEngine を停止させる
  - MonitoringDB: SQLite に対する永続化レイヤ（テーブル作成・マイグレーション含む）
- ポートフォリオ（portfolio/）
  - 候補選定、等重・スコア加重、リスク軸サイジング、セクター制限、レジーム乗数
- リサーチ（research/）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Spearman rank）、ファクター統計
- AI（ai/）
  - News NLP：OpenAI（gpt-4o-mini）でニュースをスコア化して ai_scores に保存
  - Regime Detector：ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提
- Python 3.10+（typing の | や一部構文を使用）
- Git 等でリポジトリを取得済みであること

1. リポジトリをクローン / 配布アーカイブを展開
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール

   主要依存（明示的な requirements.txt がない場合は最低限以下）:

   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証時の YAML 内容チェックを行う場合）
   - Optional: その他テスト/開発用ライブラリ

   例:
   - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 生成後に設定検証:
     - python -m kabusys.validate_config
     - --strict オプションで警告を FAIL 扱いにできます

5. データディレクトリとログディレクトリ
   - デフォルトで data/ や logs/ を参照します。必要なら事前に作成してくださいが、logging_setup は自動作成を試みます。

6. OpenAI を使う機能のために `OPENAI_API_KEY` を .env に設定してください（ai/ の機能を使う場合）。

---

## 主要な環境変数（抜粋）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（ai/ 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

監視・停止関連
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

---

## 使い方（代表例）

1. 設定の準備
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視を起動
   - python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）
     - 監視はデフォルトで本番 sqlite_path を使用（監視データは共有されない）

3. 実行エンジンを起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が用いられ、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます
     - エンジンは data/stop_requested.flag を検知すると停止します
     - エンジンの PID は data/execution.pid に記録される想定

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11

5. AI 系処理（例: ニューススコア）
   - ai.news_nlp.score_news(conn, target_date, api_key=...)
   - python から直接利用するか、独自スクリプトを作成して DuckDB 接続と対象日を渡して呼び出します
   - 注意: OPENAI_API_KEY が必要

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit(1) 扱いになります

停止・Kill Switch
- KillSwitch はリスク条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこのファイルの存在を見て停止します。
- 手動で停止フラグを作るには、data/stop_requested.flag を作成します（run_execution/run_monitoring が検知して安全に終了します）。

ログ
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／モジュールと用途の一覧です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - config_setup.py
    - .env 作成ウィザード（CLI）
  - validate_config.py
    - 設定検証 CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードに対応）
  - utils/
    - logging_setup.py: ログ設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py: SQLite スキーマ定義・永続化ユーティリティ
    - system_monitor.py: システム監視（CPU/Mem/Disk、データ鮮度）
    - trade_monitor.py: 注文関連の監視（trade_logs を参照）
    - risk_monitor.py: ドローダウン・ポジション上限監視（RiskMonitor）
    - kill_switch.py: kill.flag 制御
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - alert_manager.py: （アラート送信機能。LINE 等と連携する想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 発注・注文管理・リスク制御関連（詳細は各ファイル参照）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定・配分・サイジング・セクター制限
  - research/
    - factor_research.py, feature_exploration.py
      - ファクター計算・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュースを LLM でスコア化
    - regime_detector.py: マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成 CLI
  - data/  (実行時に使用 / 生成されるディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (ログファイル出力先、デフォルト)

---

## 開発・運用上の注意

- 環境変数は機密情報を含むため .env を絶対に Git にコミットしないでください（config_setup もその旨コメントを挿入します）。
- 本番運用時は KABUSYS_ENV=live を設定し、validate_config の警告を慎重に確認してください。
- OpenAI を使う機能は API 料金が発生します。キー管理・リクエスト制御に注意してください。
- Paper Trading モードは本番 DB から分離されていますが、設定ミスで本番 DB に書き込まれないよう .env の `KABUSYS_ENV` と `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を確認してください。
- psutil や OS 権限によってはプロセス優先度・CPU affinity の設定が失敗する場合があります（ログで警告が出ますが処理は継続します）。
- DuckDB や SQLite のバージョン差異により executemany の挙動が異なる場合があります。ai.news_nlp などではその点に配慮した実装になっています。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

---

README に書かれている以外の API（内部モジュールや関数）についてはソースコードの docstring を参照してください。追加のドキュメントや実運用手順（systemd ユニット、コンテナ化、バックアップなど）は別途作成することを推奨します。