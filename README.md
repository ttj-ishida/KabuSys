KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォーム向けコードベースです。  
主な目的は「戦略の研究・ファクター算出・ポートフォリオ構築・発注実行・監視・レポート生成」を統合的にサポートすることです。  
本リポジトリはモジュール化されており、実行エントリ、監視、AI を用いたニュース解析、ポートフォリオ構築ロジック、調査用ユーティリティ等を含みます。

主な機能
--------
- ExecutionEngine（発注実行）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ペーパートレード時は MockBroker を使用し DB を分離（data/paper_trading.db）
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）を統合
- Monitoring（監視）
  - システム状態（CPU/MEM/DISK）、Execution プロセス監視、注文・約定ログ監視、リスク監視
  - Kill Switch（閾値超過時に data/kill.flag を書き込み、Execution を停止）
  - モニタリング DB（SQLite）を永続化層として提供
- 研究・リサーチ
  - ファクター（モメンタム / バリュー / ボラティリティ等）の DuckDB ベース計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等
- AI（OpenAI）連携
  - ニュースを LLM でスコアリング（news_nlp）
  - マクロセンチメントと ETF MA を組み合わせた市場レジーム判定（regime_detector）
- ポートフォリオ構築
  - 候補選定、重み計算（等配分／スコア重み）、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定支援
  - 対話式 .env ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）

セットアップ手順
----------------

1. 前提
   - Python 3.9+（ソース内での型ヒントやライブラリを想定）
   - システムパッケージ（必要に応じて）：DuckDB、SQLite は Python パッケージで利用可能
   - 推奨ライブラリ（pipでインストール）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config.yaml の検証を行いたい場合）
   - 例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt が無ければ上記を手動でインストールしてください。

2. リポジトリルートの準備
   - data/ や logs/ ディレクトリが自動で作成されます（一部コードは存在しない親ディレクトリへ mkdir を行いますが、必要に応じて手動で作成してください）。

3. 環境変数 / .env の設定
   - 対話形式で .env を作る:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（例）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
   - 自動ロード:
     - デフォルトでプロジェクトルートの .env, .env.local を自動ロードします。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証
   - 起動前に設定を検証:
     python -m kabusys.validate_config
   - 警告をエラー扱いにする（CI 等で利用）:
     python -m kabusys.validate_config --strict

5. OpenAI を使う機能（任意）
   - AI 機能（news_nlp / regime_detector）を使うには OPENAI_API_KEY を設定してください。
     export OPENAI_API_KEY=sk-...
   - API 呼び出しはリトライロジックを実装していますが、API 利用にはクォータ等に注意してください。

使い方
------

- Execution（発注エンジン）起動
  - 本番 / ペーパーは KABUSYS_ENV により切替:
    - KABUSYS_ENV=paper_trading → paper mode（paper_sqlite_path に記録）
  - 起動:
    python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定し、必要コンポーネントを初期化して別スレッドで実行します。
    - data/stop_requested.flag が存在する場合は起動を抑止、実行中に作成されると停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring（監視）起動
  - 起動:
    python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 動作:
    - SystemMonitor, TradeMonitor, RiskMonitor 等を用いてポーリングし、SQLite（monitoring.db）へログを保存、必要に応じて kill.flag を書きます。
    - 停止フラグ: data/stop_requested.flag により監視ループを終了します。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  （--db オプションで DB パスを指定できる。環境変数 PAPER_TRADING_SQLITE_PATH でも参照）

主な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使うなら必須)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（default: development）
- LOG_LEVEL (DEBUG | INFO | ...)
- MONITOR_POLL_INTERVAL（監視のポーリング間隔、秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動削除するか: 0/1）

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番発注が有効になります。設定（API パスワード / LINE 通知等）を慎重に確認してください。
- Kill Switch（data/kill.flag）は本番環境で重要な安全弁になります。KILL_FLAG_CLEAR_ON_START を 1 にする設定は本番では推奨されません。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合、コンソール出力のみになります。
- DuckDB は分析向けに使われ、prices_daily / raw_financials / raw_news 等のテーブルを想定しています。データの投入とスキーマ準備は別途行ってください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理（.env 自動ロード含む）
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 起動前設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py            — SQLite 永続化層（テーブル定義＋操作）
  - system_monitor.py           — システム状態・データ鮮度監視
  - trade_monitor.py            — （注文/約定監視）※実装ファイル参照
  - risk_monitor.py             — ドローダウン・ポジション数監視
  - kill_switch.py              — kill.flag 管理
  - monitoring_engine.py        — 各 Monitor の統括ループ
  - alert_manager.py            — （アラート送信）※実装ファイル参照
- execution/
  - execution_engine.py         — ExecutionEngine コア（run_session 等）
  - broker_factory.py           — ブローカークライアントの生成（実ブローカ/モック切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py        — 候補選定、重み計算
  - position_sizing.py          — 株数決定・スケーリング
  - risk_adjustment.py          — セクター上限・レジーム乗数
- research/
  - factor_research.py          — ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py      — IC / 将来リターン / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- utils/
  - logging_setup.py            — 統一的ログ設定ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ

data/ と logs/
- data/                        — デフォルトの DB・フラグ・PID ファイル置き場（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）
- logs/                        — ログファイル出力先（logs/execution.log, logs/monitoring.log など）

追加情報 / 開発メモ
------------------
- MonitoringDB.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）も行います。
- .env のパースは独自実装で、シングルクォート / ダブルクォートや export 形式に対応しています。
- AI 呼び出し部分はリトライやレスポンスのバリデーション（JSON モード想定）を実装しており、部分失敗時に既存データを破壊しないよう配慮しています。
- DuckDB を用いた研究モジュールは外部 API へアクセスせず、prices_daily / raw_financials 等のみ参照する設計です。

問題報告 / 貢献
----------------
- バグや改善案は Issue を立ててください。プルリクエスト歓迎です。
- 本 README はコードベースの主要箇所を抜粋してまとめたものです。実装の詳細は各モジュールの docstring を参照してください。

以上。初期セットアップや実行方法について不明点があれば、どの環境（開発 / paper_trading / live）で何をしたいかを教えてください。具体的なコマンドや設定例を補足します。