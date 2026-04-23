README
======

概要
----
KabuSys は日本株向けの自動売買システムの一部を切り出した Python パッケージ群です。本リポジトリには以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）とその周辺コンポーネント（OrderManager, RiskManager 等）
- システム監視（SystemMonitor, TradeMonitor, RiskMonitor）と Kill Switch（停止フラグ）
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（portfolio モジュール）
- 研究用ファクター計算・特徴量解析（research モジュール）
- ニュースに対する LLM（OpenAI）ベースの NLP スコアリングと市場レジーム判定（ai モジュール）
- Paper Trading 検証レポート生成ツール（tools）
- 設定ウィザード・設定検証ユーティリティ（config_setup / validate_config）
- ログ設定・プロセス優先度などのユーティリティ（utils）

主な動作設計方針
- 実運用（live）とペーパートレード（paper_trading）を明確に分離。paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録されます。
- 監視（monitoring）は環境にかかわらず本番用 sqlite_path（デフォルト data/monitoring.db）を使ってログを取ります。
- OpenAI を使う AI 機能は OPENAI_API_KEY を必要とし、API エラー時は安全側でフォールバックします。
- .env / 環境変数で挙動をカスタマイズ可能。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト: run_execution.py
  - 発注管理・リスク管理・照合（Reconciler）機構
  - Paper Trading 用に本番 DB と分離された SQLite を使用可能

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセスチェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止
  - run_monitoring.py によるポーリング起動（MONITOR_POLL_INTERVAL で間隔変更可）

- Portfolio construction
  - 銘柄選定、等金額・スコア加重重み、ポジションサイズ算出、セクターキャップ、レジーム乗数

- Research
  - ファクター（Momentum/Value/Volatility）計算（DuckDB ベース）
  - 将来リターン計算、IC 計算、統計サマリ等

- AI
  - news_nlp.score_news: raw_news を OpenAI に渡して銘柄別センチメントを ai_scores に格納
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 判定を合成して market_regime を更新

- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（| 型ヒント等を使用）
- システムに duckdb, psutil, openai 等の依存が必要

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb psutil openai
   - 追加（設定検証や YAML を使う場合）:
     - pip install PyYAML
   - （プロジェクトで requirements.txt があればそれを使用してください）

4. 環境変数（.env）を用意
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考に必要な環境変数を設定）
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（分析 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - LOG_LEVEL / LOG_DIR など

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------

- 監視ループ起動（Monitoring）
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、1以上）。
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - run_monitoring はプロジェクトルート/data/stop_requested.flag を検知して終了します。
    - あるいは Ctrl+C（KeyboardInterrupt）でも停止します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB に記録。
  - 起動:
    - python -m kabusys.run_execution
    - Paper モードで起動する例:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止:
    - プロジェクトルート/data/stop_requested.flag があるとエンジンを停止します。
    - Kill Switch が発動すると data/kill.flag が書かれ、ExecutionEngine 側で停止処理が行われます。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / Regime 判定・ニューススコア
  - OpenAI API キーが必要（OPENAI_API_KEY）。
  - API を呼ぶ関数はモジュールからインポートして呼び出します（ライブラリ用途）。
    - 例:
      - from kabusys.ai.news_nlp import score_news
      - from kabusys.ai.regime_detector import score_regime
  - 両関数とも API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照します。

重要な挙動・運用メモ
- 監視 DB（SQLite）初期化は init_monitoring_db により自動で行われます（テーブル作成 & マイグレーション）。
- run_execution は起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
- Kill Switch は RiskMonitor の判定などで data/kill.flag を書き込み、ExecutionEngine がそれを検知して安全停止します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアできますが、本番では 0 を推奨します。
- ロギング:
  - 共通の setup_logging を使い、logs/<app_name>.log に日次ローテーションで出力します（デフォルト 30 日保持）。
  - ログレベルは LOG_LEVEL 環境変数で指定（デフォルト INFO）。

ディレクトリ構成
----------------
（src/kabusys 配下を中心に抜粋）

- kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数読み込み・Settings クラス
  - config_setup.py            — .env 作成ウィザード（CLI）
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

  - execution/                 — 実行関連コンポーネント（OrderManager 等）
    - (OrderManager, BrokerFactory, ExecutionEngine 等)

  - monitoring/
    - monitoring_db.py         — SQLite 操作用（テーブル管理・読み書き）
    - system_monitor.py        — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py         — 注文ログ/滞留チェック（存在）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - monitoring_engine.py     — 監視コンポーネント統合ループ
    - alert_manager.py         — 通知管理（LINE 等、存在）

  - portfolio/                 — ポートフォリオ構築ロジック（純関数）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/                  — ファクター計算・特徴量解析
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py       — 市場レジーム判定（MA + LLM）

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト

  - data/                      — 実行時生成ファイル（DB, pid, flag 等）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading)
    - kill.flag, stop_requested.flag, execution.pid など

  - utils/
    - logging_setup.py         — ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

追加の開発・デバッグ情報
- DuckDB を使っているモジュール（research, ai など）は duckdb の接続を引数で受け取り、SQL を直接実行します。DB スキーマ（prices_daily, raw_financials, raw_news 等）に従ったデータの準備が必要です。
- テストや CI では環境変数自動ロードを無効化できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- LLM API 呼び出し部分はリトライやフェイルバックが実装されていますが、テスト時は該当関数をモックして外部依存を切ることを推奨します（コード中に patch 用のコメントあり）。

よくある運用例
- ローカルでの開発検証:
  1. KABUSYS_ENV=development で .env を作成
  2. python -m kabusys.validate_config で問題がないか確認
  3. python -m kabusys.run_monitoring を別プロセスで起動（監視ログ収集）
  4. python -m kabusys.run_execution を起動（発注は行わない / safe モード）

- ペーパートレード検証:
  - KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を確認して起動。取引記録は paper_trading.db に保存され、検証は tools.paper_verification_report で行う。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく技術ドキュメントです。実運用前に設定・依存関係・各種キーの安全な管理（.env の扱い、Git にコミットしない等）を必ず行ってください。
- コントリビューションやバグ報告はリポジトリの Issue を利用してください。

問い合わせ
----------
- 開発者向けの質問はリポジトリの Issues へお願いします。必要であればモジュール単位の動作説明や API サンプルを追加で提供します。