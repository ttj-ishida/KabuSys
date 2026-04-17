# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

※ この README は src/kabusys 以下のコードベースに基づく概要・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連分析・監視を行うためのモジュール群です。  
主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）とその周辺コンポーネント（OrderManager, RiskManager, Reconciler 等）
- 監視サブシステム（SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定・セクターキャップ等）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- AI 支援モジュール（ニュース NLP によるセンチメント評価、市場レジーム判定）
- 各種 CLI ツール（設定ウィザード、設定検証、Paper Trading 検証レポート生成 等）
- 永続化は DuckDB（分析用） と SQLite（監視 / 発注ログ）を併用

設計の方針としては「テスト容易性」「ルックアヘッドバイアスの排除」「フェイルセーフ性」を重視しており、
本番（live）・ペーパートレード（paper_trading）・開発（development）を環境で切り替えられます。

---

## 主な機能一覧

- Execution（発注）
  - Broker クライアント抽象化（本番 / モック切替）
  - OrderRepository / OrderManager による注文管理
  - RiskManager による制限（ポジション上限、ドローダウン等）
  - ExecutionEngine による実行セッション
- Monitoring（監視）
  - システム監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文監視（滞留注文、約定異常）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch によるフラグファイル停止
  - アラート管理フック（LINE などを想定）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分 / スコア配分
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ、レジーム乗数
- Research（リサーチ）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）等
- AI（LLM連携）
  - ニュース記事のセンチメント化（OpenAI）
  - マクロニュースとETF MA200 を合成した市場レジーム判定
- ツール
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順（ローカル開発向け）

1. Python 環境（3.9+ を想定）を用意する
2. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする
3. 依存パッケージをインストール（例）:

   pip install duckdb psutil openai

   - PyYAML があると config/*.yaml の検証が行われます（optional）。
   - テスト / 実行環境に応じて追加パッケージが必要になる場合があります。

4. .env の作成
   - 対話式ウィザードを使う（推奨）:

     python -m kabusys.config_setup

   - あるいは .env.example を参考に手動で `.env` を作成してください。

   注意: `.env` は機密情報を含むため Git にコミットしないでください。

5. 設定検証（起動前チェック）:

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い

6. データディレクトリ
   - 多くのデフォルト DB/ファイルは `data/` に置かれます（例: data/kabusys.duckdb, data/monitoring.db）。
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite。デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- PAPER_FILL_MODE（paper_trading 時のモック約定モード: instant/partial/never/reject）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒数。デフォルト: 60）

---

## 使い方（コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine.stop() を経由します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は monitoring DB（Settings.sqlite_path）へログを書きます（環境に関係なく本番 sqlite_path を使用する作りです）。
    - data/stop_requested.flag を検出するとループを抜けます。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB の指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH、無ければ data/paper_trading.db を参照します。

- AI モジュール利用（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY（または引数）で API キーを渡す必要があります。
  - AI 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キーが無いと実行できません。

---

## ファイル / フラグ動作（運用メモ）

- data/execution.pid
  - ExecutionEngine が PID を書き込みます。SystemMonitor はこのファイルが指す PID の生存チェックを行い、stale PID の場合は削除してログを残します。

- data/stop_requested.flag
  - run_execution/run_monitoring の両スクリプトがこのファイルの存在を見て安全に停止します（管理者が作成してプロセス停止を促す用途）。

- data/kill.flag
  - KillSwitch（監視側のロジック）が条件を満たしたときに書き込まれるフラグ。ExecutionEngine がこれを見て停止する、あるいは起動時に自動クリアの設定があるため注意。

---

## 主要モジュールの簡単説明

- kabusys.config
  - .env 自動読み込み、Settings クラスで環境変数をラップ。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

- kabusys.execution
  - 発注系の主要コンポーネント（Broker クライアント生成、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository 等）。

- kabusys.monitoring
  - system_monitor, trade_monitor, risk_monitor, monitoring_db（SQLite 永続化層）、monitoring_engine（ポーリング統括）、kill_switch, alert_manager（通知）等。

- kabusys.portfolio
  - portfolio_builder（候補選定/重み算出）、position_sizing（株数計算）、risk_adjustment（セクター制限 / レジーム乗数）

- kabusys.research
  - factor_research（mom/value/volatility）、feature_exploration（forward returns, IC, summary）等。DuckDB に格納された prices_daily / raw_financials を参照。

- kabusys.ai
  - news_nlp（ニュースを LLM でスコアリング）、regime_detector（MA200 + マクロセンチメントでレジーム判定）

- kabusys.utils
  - process_priority（優先度 / CPU affinity 設定）等。

---

## ディレクトリ構成

（抜粋: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境設定読み込み / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/
    - (OrderManager, ExecutionEngine, BrokerFactory, OrderRepository, Reconciler, RiskManager 等)
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/                          — デフォルトの DB / フラグファイル置き場（実行時に作成）

---

## 運用上の注意 / ベストプラクティス

- .env は機密情報を含むため絶対にリポジトリへコミットしないこと。
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行い、validate_config でチェックすること。
- Paper Trading は production DB と完全分離される設計ですが、必ず PAPER_TRADING_SQLITE_PATH を確認してから起動してください。
- OpenAI API を使う機能は API 使用料が発生します。キーの管理と呼び出し頻度に注意してください。
- プロセス優先度設定は OS によって挙動が異なり、権限が必要になる場合があります。psutil の権限エラーはログに出力されスキップされます。
- データ鮮度チェック等は DuckDB の prices_daily を想定しているため、データパイプラインと連携して最新データを投入すること。

---

## 参考コマンドまとめ

- 依存インストール（例）:
  - pip install duckdb psutil openai pyyaml

- .env 作成:
  - python -m kabusys.config_setup

- 設定確認:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に環境変数一覧をさらに詳細に記載したり、ユニットテスト・CI 実行手順、デプロイ手順（systemd / supervisor 用のサンプル unit ファイル）を追記できます。どの情報を優先して追加しますか？