README
=====

概要
----
KabuSys は日本株の自動売買・研究パイプラインを想定した Python パッケージです。  
主な目的は次のとおりです：

- 売買シグナル → 発注までの Execution Engine（本番 / ペーパートレード対応）
- システム稼働・注文状態の監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- ファクター計算・特徴量探索（Research: DuckDB ベース）
- ニュースの LLM によるセンチメント評価・市場レジーム判定（AI）
- 運用支援ツール（設定ウィザード、設定検証、検証レポート 等）

このリポジトリはライブラリ化されており、各モジュールはコマンドラインから実行できるスクリプト / ツール群を含みます。

主な機能
--------
- Execution
  - ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerClientFactory により本番ブローカー or MockBroker を選択
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler などの連携
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス死活・データ鮮度監視
  - TradeMonitor：注文の滞留・約定異常検出（trade_logs テーブル参照）
  - RiskMonitor：ドローダウン・ポジション上限監視（dashboard / positions）
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：監視のポーリング制御とアラート連携
  - MonitoringDB：SQLite を用いた永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio（純関数群）
  - 候補選定、等配分 / スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- Research（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）
  - news_nlp: raw_news を LLM でセンチメント評価し ai_scores テーブルへ保存
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - 設定ウィザード（config_setup）
  - 設定検証（validate_config）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度設定・CPU affinity（utils.process_priority）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ
--------
前提
- Python 3.10+（型注釈に | を使用）
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（設定ファイル検証を行う場合、任意）
- SQLite（標準ライブラリで可）

手順（ローカル開発向け）
1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt があればそちらを利用）
   - pip install duckdb psutil openai
   - PyYAML を利用する場合: pip install pyyaml

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env に以下の必須キーを設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY を設定
   - その他の推奨設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動削除するか。開発でのみ 1 を推奨）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与

5. データディレクトリ作成
   - data/ ディレクトリ（既定の DB やフラグファイル用）を作成しても良いが、多くは自動作成される

使い方
-----
主要なコマンドと使用例：

- 設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告があると終了コード 1）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（売買エンジン）の起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で制御
  - 例（ペーパートレードで起動）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 既に data/kill.flag が存在する場合は起動をスキップします
  - engine は data/execution.pid に PID を出力

- Monitoring（システム監視）を起動
  - ポーリングループで定期実行されます
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可（デフォルト: 60）
  - 例:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（デフォルト data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH）:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY が必要（.env または環境変数）
  - news_nlp.score_news / regime_detector.score_regime はライブラリ API として呼び出し可能
  - 例（ライブラリ呼出）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

停止手段（Kill Switch / Stop flag）
- 実行中の ExecutionEngine / Monitoring ループはプロジェクト内のフラグファイルに依存しています：
  - data/kill.flag : Kill Switch による Execution 停止指示（KillSwitch が書き込む）
  - data/stop_requested.flag : run_execution / run_monitoring の外部停止用フラグ（存在するとループ終了）
- kill.flag のクリアは以下で行えます:
  - 手動でファイルを削除
  - 起動時の自動クリア（開発専用）:
    - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に自動クリア（本番では推奨しない）

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- データパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- AI:
  - OPENAI_API_KEY
- ログ:
  - LOG_LEVEL (例: INFO)
  - LOG_DIR （既定: logs/）
- モニタリング:
  - MONITOR_POLL_INTERVAL（秒、既定 60）

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリーの主要部分（src/kabusys）です。完全なファイルは実際のリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - __version__ (パッケージ版数)
  - config.py                — 環境変数 / .env 自動ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - /ai/
    - news_nlp.py            — ニュースセンチメントの LLM 呼び出しと書き込み
    - regime_detector.py     — 市場レジーム判定
  - /monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文監視（trade_logs 参照）  ←（実装ファイルが存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグ書き込みによる停止ロジック
    - monitoring_engine.py   — 監視コンポーネントの統合ランナー
    - alert_manager.py       — アラート送信（LINE など）（実装ファイルが存在）
  - /portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング・lot 単位丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - /research/
    - factor_research.py     — momentum / volatility / value 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - /utils/
    - logging_setup.py       — 統一的なログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - /tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

注意事項 / 運用上のガイドライン
-----------------------------
- KABUSYS_ENV=live（本番）設定時は特に注意：
  - LINE 通知や kill flag 設定、DB パス等を十分に確認してください。
  - KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 世代保持）
  - ログディレクトリ作成に失敗した場合はコンソール出力のみになります
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成し、一部カラムのマイグレーション（ALTER TABLE）も含みます
- AI 呼び出し:
  - OpenAI API の呼び出しは外部 API 依存のため、失敗時はフォールバックやスキップする処理が組み込まれていますが、API キーや料金・レート制限に注意してください
- テスト:
  - ユニットテストでは環境変数自動ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます

問い合わせ / 貢献
-----------------
- バグ報告・改善提案はリポジトリの Issue へお願いします。Pull Request は歓迎します。
- 大きな設計変更や本番稼働を想定した改修を行う際は事前に設計方針を共有してください（特に注文ロジック・リスク管理・Kill Switch 関連）。

以上が README 相当の概要です。必要であれば、導入手順の詳細（requirements.txt、Dockerfile、systemd ユニット例、CI 設定例）や各モジュールの API ドキュメントを追加で作成します。どの部分を詳しく書きますか？