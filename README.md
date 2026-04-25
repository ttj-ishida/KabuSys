KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株自動売買システム「KabuSys」のコアモジュール群です。  
本READMEではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

要点サマリ
---------
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード対応）
  - run_monitoring.py: SystemMonitor をポーリングして監視・アラート／Kill Switch を管理
- 設定管理
  - .env 自動ロード／対話式ウィザード（config_setup.py）
  - 起動前チェック（validate_config.py）
- 解析 / 研究用
  - research モジュール（ファクター計算、特徴量解析）
- AI 統合
  - news_nlp / regime_detector（OpenAI を使ったニュースセンチメント・レジーム判定）
- 永続化
  - DuckDB（分析用）／SQLite（監視・注文履歴用）
- ユーティリティ
  - ロギング設定・プロセス優先度設定など

機能一覧
--------
主な機能と役割を列挙します。

- 実行エンジン関連
  - ExecutionEngine 起動（run_execution.py）
  - ブローカークライアント抽象化（実口座 / Mock（paper_trading）を切替）
  - 注文管理、リスク管理、照合（Reconciler）等の統合（execution パッケージ内）

- 監視 / 安全装置
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常等の監視（trade_logs 解析）
  - RiskMonitor: ドローダウン／ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件に応じた data/kill.flag 書き込み（ExecutionEngine 停止トリガ）
  - MonitoringEngine: 各モニタを束ねてポーリング・アラート送信

- ポートフォリオ構築（純粋関数）
  - 銘柄選定（スコア降順 / 上位 N 抽出）
  - 重み計算（等分 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（リスクベース、単元株丸め、aggregate cap）

- 研究・ファクター計算
  - Momentum、Volatility、Value 等のファクター計算（DuckDB を用いた SQL ベース）
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）連携
  - news_nlp: raw_news を LLM に渡して銘柄別センチメントを ai_scores に格納
  - regime_detector: ETF の MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定

- コマンド／ツール
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
---------------
以下はローカルで動かすための推奨手順です（例）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
     （このコードベースでは主に以下が必要です）
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証を使う場合）
   - 例: pip install duckdb psutil openai pyyaml

4. .env を作成（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルト）を生成します。機密情報は入力時にマスクされます。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば指摘に従って .env を修正。--strict を付けると警告も失敗扱いになります。

6. データディレクトリの準備（必要なら）
   - デフォルトでは data/ 以下に DB や pid/flag を置きます。必要に応じて .env のパスを変更してください。

主要な環境変数
----------------
（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）

（任意・重要）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い paper_sqlite_path（data/paper_trading.db）へ書込
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI 呼び出し用キー（news_nlp / regime_detector で必要）
- PAPER_FILL_MODE — ペーパートレード時の注文約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

使い方（起動・運用）
-------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_sqlite_path に書き込む（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag があると起動を行わず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止処理を行う
    - 起動時に pid ファイル（デフォルト data/execution.pid）を使用

- 監視プロセス起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 挙動
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path（data/monitoring.db）を使用（環境に依らず）
    - stop フラグ（data/stop_requested.flag）を検知すると監視ループを終了

- 強制停止 / Kill Switch
  - KillSwitch は条件（ドローダウンやポジション上限）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です。
  - manual に実行を停止したい場合は data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数または --db で指定可）
  - 出力される指標: 稼働率、注文成功率（fill rate）、送信率、レイテンシ（P95）など。閾値に基づき PASS/FAIL を判定。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
- デフォルト: stdout（コンソール） + 日次ローテートのファイル出力（logs/<app_name>.log）
- ログディレクトリ: 環境変数 LOG_DIR またはデフォルト logs/

注意点 / 運用上のヒント
---------------------
- .env は機密情報を含むため絶対に Git 等にコミットしないこと。
- KABUSYS_ENV=live のときは特に LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等の設定を慎重に確認すること（validate_config に注意喚起あり）。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーとトークン量に依存します。レート制限やエラー時のリトライ動作は実装済みですが運用時はコストと制限を考慮してください。
- ペーパートレード時の DB は本番と分離されます（デフォルト: data/paper_trading.db）。本番 DB（monitoring.db）と混在しないよう注意。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル・フォルダと簡単な説明です（抜粋）。

- kabusys/
  - __init__.py              — パッケージ初期化（バージョン定義など）
  - config.py                — 環境変数 / Settings クラス、自動 .env ロードロジック
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/               — 発注・エンジン関連（OrderManager / ExecutionEngine 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/              — 監視関連
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/               — Portfolio Construction（純粋関数群）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/                — 研究・解析（DuckDB ベース）
    - factor_research.py
    - feature_exploration.py

  - ai/                      — LLM を使った分析
    - news_nlp.py
    - regime_detector.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - (その他ユーティリティ)

付録: よく使うコマンド例
-----------------------
- .env の作成（ウィザード）
  - python -m kabusys.config_setup

- 設定確認
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 指定 DB を使う: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

最後に
------
この README はコードコメントやモジュールの docstring から要点を抜粋して作成しています。実際の導入・運用時は config/*.yaml（存在する場合）や環境変数の値、ログを十分に確認してください。質問や補足ドキュメントが必要であれば、どの部分を詳しく説明するか教えてください。