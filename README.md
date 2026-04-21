# KabuSys — 日本株自動売買システム

このドキュメントはリポジトリ内のコードベースに基づく簡易 README です。起動スクリプト、設定、監視、ペーパートレード検証、研究ユーティリティなどを含むモジュール群を説明します。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件・依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 主要環境変数
- 運用メモ（監視・停止フラグなど）
- ディレクトリ構成（主要ファイル）

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークです。
- 注文実行エンジン（ExecutionEngine）、監視（Monitoring）、リスク管理、ポートフォリオ構築、研究（ファクター計算）および AI（ニュース NLP / レジーム判定）を含むコンポーネントで構成されています。
- 実行環境は `KABUSYS_ENV` により `development` / `paper_trading` / `live` を切り替え可能。`paper_trading` は本番 DB と分離されたペーパートレード専用 DB を使用します。

主な機能一覧
- Execution
  - ブローカークライアントを用いた注文管理（本番 / ペーパー切替）
  - リスク管理（最大ポジション比率、最大利用率、ドローダウン監視など）
  - 注文リコンサイル・履歴の永続化
- Monitoring
  - システム状態（CPU / メモリ / ディスク）監視
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - トレード / リスク関連の常時監視とアラート発行
  - Kill Switch（条件に応じて ExecutionEngine 停止フラグを書き込む）
- Portfolio
  - 候補選定、等配分／スコア加重、ポジションサイズ計算（単元株丸め含む）
  - セクター上限適用、レジームに応じた投入資金乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース記事の LLM（OpenAI）によるセンチメントスコア化（ai_scores への書込）
  - マクロニュース＋ETF MA 乖離を使った市場レジーム判定と DB 書込
- ツール
  - ペーパートレード検証レポート生成（Paper Trading 検証）
  - 対話式 .env 生成ウィザード、設定検証 CLI

必要条件・依存関係
- Python 3.10+
- 必須 Python パッケージ（代表例）
  - duckdb
  - openai
  - psutil
- オプション
  - PyYAML（config/*.yaml の検証に使用）
- DB
  - SQLite（標準ライブラリの sqlite3 を利用）
- その他
  - ネットワーク接続：kabuステーション API / OpenAI API など必要に応じて

セットアップ手順（ローカルでの初回手順）
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb openai psutil
   - config YAML を検証したい場合: pip install pyyaml
4. .env の準備
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - または `.env.example` を参考に手動で `.env` を作成（リポジトリに例がない場合は次の必須変数を設定）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB、デフォルト: data/paper_trading.db）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - プロセス優先度を high に設定
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、`data/paper_trading.db` を使用（本番 DB と分離）
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor / TradeMonitor / RiskMonitor を初期化してポーリングを行う
    - デフォルトポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
    - 停止は data/stop_requested.flag を作成すると検知して終了
    - 監視は本番 sqlite_path を常に参照（KABUSYS_ENV に依存しない）
- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を生成・更新できます
- 設定検証
  - python -m kabusys.validate_config
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）
- 研究・AI のモジュール利用（ライブラリ的利用）
  - duckdb 接続を渡して関数を呼ぶ:
    - 例: from kabusys.research import calc_momentum; calc_momentum(conn, target_date)
  - AI スコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  — OpenAI API キー必須（引数または OPENAI_API_KEY 環境変数）

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - PID_FILE_PATH（実行エンジンの PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
- ロギング
  - LOG_LEVEL（DEBUG/INFO/...）
  - LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）
- 監視
  - MONITOR_POLL_INTERVAL（監視ループの秒数、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）
- OpenAI
  - OPENAI_API_KEY（AI モジュール使用時に必要）

運用メモ（監視・停止フラグなど）
- 停止フラグ
  - data/stop_requested.flag：run_execution / run_monitoring はこのファイルの存在を検知して終了や停止を行う。手動停止用に利用。
  - data/kill.flag：KillSwitch が書き込むファイル。ExecutionEngine に対する停止要求（より高レベルの停止）。`Settings.kill_flag_clear_on_start` が 1 の場合、起動時に自動クリアされるので本番では注意。
- ロギング
  - ログはデフォルトで stdout と `logs/<app_name>.log`（日次ローテート）に出力されます。ログディレクトリは環境変数 LOG_DIR で変更可。
- PID ファイル
  - 実行エンジンは PID ファイル（デフォルト data/execution.pid）を書きます。起動中のプロセス管理や stale PID 検出に利用されます。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は必要なテーブル・カラムを冪等的に作成します。古い DB に対して一部カラム（例: peak_value, latency_ms）が無ければ ALTER を実行して追加します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動ロード・Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - monitoring_engine.py — 各 Monitor を束ねる
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — （実装ファイルが存在）トレード監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （アラート送信）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（注文ループ）
    - broker_factory.py — BrokerClient の生成（本番/Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・制限・丸めロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等の計算
    - feature_exploration.py — 将来リターン / IC / summary
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA でレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足
- DuckDB は分析用の読み取り専用 DB（prices_daily, raw_financials 等）を想定しています。ry
- 設定検証ツールは PyYAML が無い場合に YAML 検証をスキップします（警告）。必要なら `pip install pyyaml`。
- OpenAI を利用する機能は API 利用制限・課金が発生するため、事前に API キーの管理とコスト確認を行ってください。
- 本 README はコードベースから読み取れる設計・使い方の要点をまとめたものです。運用時は各モジュールの docstring / ソースコードを参照してください。

よく使うコマンドまとめ
- .env を対話式で作る: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要なら README に載せるサンプル .env テンプレートや各 CLI の詳細な Usage、監視アラート先（LINE等）の設定例も追加します。どの部分を詳しく追記しましょうか？