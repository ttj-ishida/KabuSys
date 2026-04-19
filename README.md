KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・バックテスト・運用支援を目的とした小規模なシステム群です。本リポジトリには以下の機能領域が含まれます:

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文管理の実行
- 監視（Monitoring）: システム稼働状況・データ鮮度・リスク検出・Kill Switch
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- リサーチ: ファクター計算・特徴量探索・IC計算
- AI（OpenAI）連携: ニュースセンチメント評価・レジーム判定
- ユーティリティ: .env ウィザード、設定検証、紙トレード検証レポート等

主な特徴
--------
- モジュール化された純粋関数群（portfolio / research）によりテストが容易
- DuckDB（分析用）とSQLite（運用監視用）を併用するデータ設計
- Paper Trading 時は本番 DB から分離された専用 SQLite を使用
- OpenAI を使ったニュース NLP / レジーム検出を内蔵（APIキー必要）
- kill.flag による安全停止機構、監視による自動アラート/停止制御
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力

セットアップ手順（ローカル開発向け）
-------------------------------
1. Python 環境（推奨: 3.10+）を用意する。仮想環境を推奨:
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要なパッケージをインストール（最低限の例）:
   - pip install duckdb psutil openai
   - 追加で開発/検証用に: pip install PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. ディレクトリ作成:
   - data/ と logs/ は多くの処理で自動作成されますが、手動で作る場合:
     - mkdir -p data logs

4. 環境変数の設定:
   - リポジトリルートに .env を置く / または環境変数を設定します。
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 重要なオプション（デフォルト値）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - PAPER_FILL_MODE — instant | partial | never | reject (paper trading の埋め方)

5. 設定検証（起動前推奨）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

環境変数自動読み込み
--------------------
- このプロジェクトは起動時に .env/.env.local を自動で読み込みます（OS 環境変数が優先）。
- 読み込み順:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - Paper Trading 用に起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading 時は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（監視 DB）を常に使用します（KABUSYS_ENV にかかわらず本番 sqlite_path を参照）。

- 停止シグナル / フラグ
  - data/kill.flag を作成すると ExecutionEngine はそれを検出して停止します（KillSwitch）。
  - data/stop_requested.flag は run_monitoring/run_execution の停止検出に使用されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

- AI 関連（OpenAI 必須）
  - kabusys.ai.score_news (ニュースの NLP スコアリング)
  - kabusys.ai.regime_detector.score_regime (市場レジーム判定)
  - どちらも OPENAI_API_KEY を環境変数か引数で指定する必要があります。

ログ
---
- ログ設定は共通ユーティリティ kabusys.utils.logging_setup.setup_logging によって行われます。
- stdout（StreamHandler）および logs/<app_name>.log（日次ローテート、30日分保持）へ出力します。
- ログレベルは優先順: 引数 level > 環境変数 LOG_LEVEL > INFO

注意事項 / 実運用上のポイント
----------------------------
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は必ず設定してください。
- KABUSYS_ENV=live の場合は特に注意: LINE 通知設定や Kill Switch 設定を確認してください（validate_config で警告が出ます）。
- Paper Trading は本番 DB を汚さないよう専用 DB に書き込みます（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しはリトライ・フォールバックロジックを持ちますが、APIキー未設定時は ValueError を送出します。
- MONITORING は監視 DB（sqlite_path）へアクセスします。monitoring の初期化は init_monitoring_db により冪等でテーブルを作成します。
- 実行時プロセス優先度は utils.process_priority.set_process_priority("high") が呼ばれますが、権限不足で失敗する場合はログに警告が出ます。

依存ライブラリ（主要）
--------------------
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に必要）

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要なモジュール一覧（抜粋）です:

- kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数・.env 読み込み・Settings)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)

  - ai/
    - news_nlp.py (ニュース NLP スコアリング / OpenAI 連携)
    - regime_detector.py (市場レジーム判定)
    - __init__.py

  - monitoring/
    - monitoring_db.py (SQLite 監視 DB 層)
    - system_monitor.py (システム状態 & データ鮮度監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - trade_monitor.py (※実装あり) — 取引ログ監視（ファイル内参照）
    - monitoring_engine.py (複数 Monitor を束ねる)
    - kill_switch.py (kill.flag 管理)
    - alert_manager.py (※実装あり) — アラート通知管理

  - execution/ (発注実行周り: BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等)
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数計算・スケーリング)
    - risk_adjustment.py (セクター上限・レジーム乗数)
    - __init__.py

  - research/
    - factor_research.py (momentum/value/volatility ファクター計算)
    - feature_exploration.py (forward returns, IC, summary)
    - __init__.py

  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
    - __init__.py

  - utils/
    - logging_setup.py (共通ログ設定)
    - process_priority.py (プロセス優先度・CPU affinity)
    - __init__.py

追加情報 / 開発ヒント
--------------------
- DuckDB 接続は分析用途で使用され、prices_daily や raw_financials、raw_news などのテーブルに対して SQL を実行します。
- research モジュールは外部 API にアクセスせず、DuckDB の価格データ等のみで完結します（テスト容易）。
- AI 機能を使う場合は API コールに対するレート制限やコストに注意してください。リトライ・バッチ処理・スコアクリップ等の保護ロジックが組み込まれています。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境を固定化すると便利です。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を追記してください）

お問い合わせ
------------
不明点や問題があれば README を更新頂くか、リポジトリの Issues をご利用ください。

以上。導入・運用時に必要な補足があれば追記します。