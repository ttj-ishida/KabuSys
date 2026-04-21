KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システムのコアライブラリ群と運用用のスクリプト群を含みます。
主要コンポーネントは注文実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、
ポートフォリオ構築・ポジションサイジングや研究用ユーティリティ群、AI を使ったニュース解析などです。

主な特徴
--------
- ExecutionEngine（発注エンジン）とモニタリングの起動スクリプトを提供
- Paper Trading（ペーパートレード）モードに対応（本番 DB と分離）
- 監視ログ（SQLite）と分析用データベース（DuckDB）を使用
- Kill Switch / stop フラグによる安全停止機構
- ポートフォリオ構築・リスク制御・ポジション決定の純粋関数実装
- ニュース NLP（OpenAI）を使った銘柄ごとのセンチメント評価
- 設定ウィザード（.env 生成）と設定検証ツール

インストール / セットアップ
---------------------------
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   本リポジトリに requirements.txt は含まれていませんが、以下を少なくともインストールしてください。
   - duckdb
   - psutil
   - openai
   - pyyaml (config の YAML 検証を行いたい場合)
   例:
     pip install duckdb psutil openai pyyaml

3. プロジェクトルートに data/ と logs/ ディレクトリを作成（多くの機能は自動作成しますが事前作成しておくと安全です）
   mkdir -p data logs

4. 環境変数設定 (.env)
   - 初回は対話式ウィザードで .env を作成できます:
       python -m kabusys.config_setup
   - またはサンプルファイル（.env.example があれば参照）を編集して .env を作成してください。
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（ai 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（本番で自動クリアするのは危険。デフォルト 0）

5. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（起動と運用）
-------------------

- ExecutionEngine（注文実行）の起動
  - 本番または開発環境で実行:
      python -m kabusys.run_execution
    実行時は Settings に基づいて DB パスや PID ファイルが解決されます。
  - ペーパートレードで起動する場合:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    paper_trading モードでは専用の mock ブローカークライアントが使用され、
    デフォルトで data/paper_trading.db に記録され、本番 DB と完全に分離されます。

  - 停止:
    - run_execution はプロジェクトルート/data/stop_requested.flag を監視します。
      このファイルが存在するとエンジンは停止します（外部から強制停止したい場合に使用）。
    - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch が書き込み、
      ExecutionEngine に対する停止シグナルとして機能します。kill.flag は ExecutionEngine 起動時の設定により自動クリアされる場合があります（KILL_FLAG_CLEAR_ON_START=1）。

  - PID ファイル:
    - 実行時に data/execution.pid（デフォルト）などの PID ファイルを書きます。

- Monitoring（監視）の起動
  - 監視は常に本番 sqlite_path を参照します（環境にかかわらず監視用 DB は本番パス）。
    python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視の停止:
    - プロジェクトルート/data/stop_requested.flag を作成すると監視ループは終了します。

- ログ
  - 共通ログ設定ユーティリティ (kabusys.utils.logging_setup) を各スクリプトで使用しています。
  - デフォルトログディレクトリ: logs/
  - ログファイルは日次ローテーションされ、logs/<app_name>.log に出力されます（app_name は "execution" や "monitoring" など）。

ツール
-----
- ペーパートレード検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  デフォルト DB: data/paper_trading.db。--db オプションでパス指定可。

設定関連 CLI
------------
- 環境設定ウィザード（.env 生成・更新）:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
  --strict を付けると警告を FAIL として扱います。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- OPENAI_API_KEY — OpenAI API キー（ai 機能で必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

注意事項 / 運用上のポイント
--------------------------
- 本番運用時は KABUSYS_ENV=live を正しく設定し、LINE 通知設定等を確認してください。validate_config は live に特有のガードチェックを行います。
- kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。デフォルト 0 を推奨します。
- run_monitoring は Monitoring 用に本番 SQLite（Settings.sqlite_path）を常に参照します。紙トレードの監視データを分離したい場合は設定を調整してください。
- AI 関連機能（news_nlp, regime_detector）は OpenAI API を使用します。API キーの管理とコストに注意してください。API エラーはフェイルセーフで扱われる設計ですが、運用時のリトライやレート制限に配慮してください。
- ログディレクトリ作成やファイル書き込みに失敗した場合、ログは標準出力にフォールバックします。システム運用時は logs/ に書き込み権限があることを確認してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings クラス
- config_setup.py                  — .env 対話的ウィザード
- validate_config.py               — 設定検証 CLI
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — Monitoring 起動スクリプト

- utils/
  - logging_setup.py                — ログ設定ユーティリティ
  - process_priority.py             — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py                — SQLite 永続化層
  - monitoring_engine.py            — 各 Monitor の束ね
  - system_monitor.py               — システム状態 / データ鮮度監視
  - trade_monitor.py                — 注文・約定監視（実装あり）
  - risk_monitor.py                 — ドローダウン / ポジション上限監視
  - kill_switch.py                  — kill.flag 管理
  - alert_manager.py                — アラート通知（LINE 等、実装参照）

- execution/                        — 発注エンジン関連（OrderManager, RiskManager, Engine 等）
- portfolio/                        — ポートフォリオ構築・サイジング・リスク調整
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/                         — ファクター計算・特徴量解析
  - factor_research.py
  - feature_exploration.py

- ai/                               — AI 関連処理
  - news_nlp.py
  - regime_detector.py

- monitoring/monitoring_db.py       — 監視 DB の初期化と CRUD
- tools/
  - paper_verification_report.py     — ペーパートレード検証レポート

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください）

開発者向けメモ
---------------
- ローカル開発では KABUSYS_ENV=development を使い、実際の発注 API 呼び出しを行わない shim が適用される設計の箇所があります。
- 単体関数（ポートフォリオ構築、ポジションサイズ計算、研究モジュール等）は副作用が少なくテストしやすい実装を目指しています。
- OpenAI 呼び出し部分は再現可能性のために明確に分離され、テスト時は該当関数をモックできます（例: unittest.mock.patch）。

ライセンス / バージョン
-----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

お問い合わせ / 追加情報
----------------------
実運用にあたっては各種設定（APIキー、DB バックアップ、監視アラート設定、運用手順）を整備してください。README に補足したい点や運用フローのテンプレート作成が必要であればお知らせください。