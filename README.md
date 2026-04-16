KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルな日本株自動売買システムのコアコンポーネント群を含みます。
主に以下の機能を提供します。

- 注文実行エンジン（ExecutionEngine）と発注フロー管理
- 監視（Monitoring）: システム状態 / 注文滞留 / リスク監視・アラート
- ポートフォリオ構築ロジック（候補選定・配分・株数算出・セクター制限）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー 等）
- AI を用いたニュースセンチメント解析・レジーム判定（OpenAI）
- Streamlit ベースの監視ダッシュボードや検証ツール（Paper Trading レポート）

この README では、プロジェクト概要、機能一覧、セットアップ手順、使い方（起動例）、
主要ディレクトリ構成を日本語でまとめます。

1. プロジェクト概要
------------------
KabuSys は、実際のブローカー API（kabuステーション 等）と接続する実稼働向けの
構成を想定しつつ、Paper Trading（模擬発注）モード、研究/リサーチ用モジュール、
監視・アラート周りの仕組みを備えた自動売買フレームワークです。

設計方針（抜粋）:
- DB 永続化: SQLite（監視ログ等） + DuckDB（時系列・ファクタ計算用）
- AI 機能は OpenAI API（gpt-4o-mini を想定）と連携可能（OpenAI APIキーが必要）
- Paper Trading モードでは本番 DB と分離された専用 SQLite を用いる
- 監視は flag ファイル（data/kill.flag / data/stop_requested.flag / execution.pid）で
  エンジン停止や制御が可能
- 環境変数・.env ファイルから設定を読み込む（自動ロード、無効化オプションあり）

2. 主な機能一覧
----------------
- Execution
  - 起動スクリプト: src/kabusys/run_execution.py
  - Broker クライアント抽象化 / mock ブローカーによる paper_trading サポート
  - OrderManager / ExecutionEngine / Reconciler による注文管理・自動復旧

- Monitoring
  - 起動スクリプト: src/kabusys/run_monitoring.py
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限検出 -> kill.flag 書込
  - AlertManager: LINE Push による通知（任意）
  - Streamlit ダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py

- Portfolio
  - 候補選定 / 等配分・スコア配分 / 株数算定（単元丸め、リスク・利用率制限、aggregate cap）

- Research / AI
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - forward returns, IC 計算, 統計サマリ等のユーティリティ
  - AI ニューススコアリング（kabusys.ai.news_nlp）
  - レジーム判定（kabusys.ai.regime_detector）

- ツール
  - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py

3. セットアップ手順
-------------------
前提:
- Python 3.10 以上（コード中で | 型記法などを使用）
- Git, SQLite が使える環境

推奨手順（UNIX 系）:

1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate

2) 必要パッケージをインストール
   （requirements.txt がない場合は下記パッケージを個別インストールしてください）
   pip install duckdb psutil requests openai streamlit

   ※ 実際の利用時はプロジェクト用 requirements.txt を用意して pip install -r を推奨します。

3) データディレクトリ作成
   mkdir -p data

4) 環境変数設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込みます。
   自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - paper_trading の場合は実行時に MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH を使う
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を使う場合
   - SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き可能）

5) DB 初期化
   run_monitoring.py / run_execution.py 内で init_monitoring_db が呼ばれます。
   最初の起動時に自動でテーブル作成・一部マイグレーションが行われます。

4. 使い方（起動例）
------------------

- 監視ループを起動（監視のみ）
  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - 監視は Settings に従い monitoring.db と duckdb を使用します。

- 実行エンジンを起動（発注エンジン）
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、
    MockBrokerClient により実取引を行いません（本番 DB と完全分離）。
  - 実行中は data/execution.pid に PID を書き、stop/kill はフラグファイルで制御します。

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  またはデフォルト DB を使う:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ライブラリ的に呼び出す）
  - ニューススコアリング:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
    必要: OpenAI API キー（引数または環境変数 OPENAI_API_KEY）

  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")

- 停止 / 強制停止
  - 監視ループ停止: data/stop_requested.flag を作成すると run_monitoring のループが終了します。
    （run_execution も同様に起動時に stop flag をチェックし、実行中も定期的にチェックします）
  - ExecutionEngine に安全停止を促す（Kill Switch 発動）: data/kill.flag を作成します。
    - KillSwitch は RiskMonitor 等の結果により自動で書き込まれることがあります。

5. 重要な設計・運用上の注意
---------------------------
- Paper Trading モードでは本番 DB と分離されますが、運用時は必ず設定を確認してください。
- OpenAI 呼び出しは課金対象・レート制限があります。API キーの管理とリトライ挙動に注意してください。
- process priority / CPU affinity を設定する機能（psutil に依存）がありますが、権限により失敗する場合はログに記録され処理は継続します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に依存します。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. ディレクトリ構成（主要ファイル）
-----------------------------------
以下は src/kabusys 以下の主要ファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py               (パッケージ定義、バージョン)
  - config.py                 (Settings: 環境変数・.env 読込)
  - run_execution.py          (ExecutionEngine 起動スクリプト)
  - run_monitoring.py         (SystemMonitor 起動スクリプト)

- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - order_record.py
  - execution_engine.py
  - broker_factory.py
  - reconciler.py

- src/kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py
  - __init__.py

- src/kabusys/utils/
  - process_priority.py
  - __init__.py

- data/
  - monitoring.db (SQLite, デフォルト)
  - kabusys.duckdb (DuckDB, デフォルト)
  - paper_trading.db (Paper Trading 用 SQLite, デフォルト)
  - execution.pid / kill.flag / stop_requested.flag (運用用フラグ/ロックファイル)

7. 開発・拡張のヒント
---------------------
- DuckDB 上の prices_daily / raw_financials テーブルを整備すると research モジュールを活用できます。
- AI モジュール（news_nlp / regime_detector）は OpenAI レスポンスのパースやリトライロジックを内包しています。テスト時は内部の API 呼び出しをモックしてください（README 内の docstring にも記載あり）。
- 監視・アラートの閾値は Settings の環境変数で調整できます（CPU / Memory / Disk 閾値等）。
- Streamlit ダッシュボードは read-only URI で DB を開くため、運用中の監視表示に便利です。

8. よくある質問（FAQ）
---------------------
Q. .env をコミットしていいですか？
A. 絶対にコミットしないでください。API キーやパスワード等が含まれます。.env.example を作成して必要なキーを document してください。

Q. 本番モードでの注意点は？
A. KABUSYS_ENV=live の場合は本番 DB を使用し、実注文が流れます。十分なテストとバックアップを行ってから運用してください。

Q. 監視ループを一時停止したい
A. data/stop_requested.flag を作成すると run_monitoring / run_execution のメインループが終了します。再起動時はフラグを削除してください。

9. ライセンス / コントリビューション
-------------------------------------
（ここにプロジェクトのライセンス・コントリビューションルールを記載してください）

以上。必要であれば、環境変数のサンプル .env.example や requirements.txt、運用手順（systemd unit 例、Dockerfile 例）を追記できます。どの情報を優先して追加しますか？