# KabuSys — 日本株自動売買システム

README はこのリポジトリ内の主要モジュールを基に作成しています。  
本ドキュメントはプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。  
主要機能は次の通りです：

- シグナル → ポートフォリオ構築 → ポジションサイズ算出 → 発注（ExecutionEngine）
- 発注・トレード履歴・監視ログの永続化（SQLite / DuckDB）
- 実行プロセスおよびデータ鮮度の監視（Monitoring）
- リスクガード（ドローダウン、ポジション上限等）と Kill Switch（フラグファイルで発注停止）
- Paper Trading モード（本番 DB と分離された専用 SQLite に記録）
- ニュース NLP を用いた銘柄センチメント、レジーム判定（OpenAI API 統合）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- コマンドライン ユーティリティ（.env ウィザード、設定検証、検証レポート生成 等）

設計方針として、ルックアヘッドバイアスを避けるために日付/時刻の扱いに注意し、外部 API 呼び出しは明示的にキーを要求するようになっています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine：発注の管理・リスクチェック・リコンシリエーション
  - BrokerClientFactory：環境に応じて実ブローカー or MockBroker を生成（KABUSYS_ENV=paper_trading 時は Mock）
  - Paper Trading の場合は `data/paper_trading.db`（デフォルト）へ分離記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス状態、データ鮮度を定期記録
  - TradeMonitor / RiskMonitor：滞留注文やドローダウンなどを監視・ログ化
  - MonitoringEngine：各モニタを束ねポーリング実行・アラート送出
  - KillSwitch：条件を満たしたら `data/kill.flag` を書き、ExecutionEngine に停止シグナル
- Portfolio（純粋関数群）
  - 候補選定（select_candidates）、等重・スコア重み付け、ポジションサイズ計算（単元株丸め含む）
  - セクター上限・レジーム乗数適用
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン / IC（Information Coefficient）計算 / 統計サマリー
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント集約と ai_scores 書き込み
  - regime_detector：ETF MA とマクロニュースセンチメントを合成して日次レジーム判定
- ユーティリティ
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート（日次/期間指定出力）
  - 統一的なログ設定、プロセス優先度設定ユーティリティ

---

## 動作要件（推奨）

- Python 3.10+（型ヒント等を利用）
- 必要パッケージ（代表例）：
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度設定・CPU affinity はプラットフォーム依存あり）

依存パッケージはプロジェクトに requirements.txt があればそこからインストールしてください。無ければ上記を pip でインストールしてください。

例:
- pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置
2. Python 環境を用意（venv 等）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存関係をインストール
   - pip install duckdb psutil openai PyYAML
   - （パッケージ化されている場合）pip install -e .
4. データ・ログ用ディレクトリを作成（任意。起動時に自動作成されることも多い）
   - mkdir -p data logs
5. 環境変数の設定
   - 対話式で .env を作成: python -m kabusys.config_setup
   - もしくは .env を直接編集（.env.example を参照）
   - 自動ロードの仕組み:
     - 起動時にプロジェクトルートの `.env`（優先度低）および `.env.local`（優先度高）を自動で読み込む
     - OS 環境変数は .env より優先され保護されます
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

注意:
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でもその旨警告があります）。

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading: MockBroker を使用、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録される
  - live: 実際に発注が行われる
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1: 自動クリア、0: クリアしない；本番は 0 推奨）

---

## 使い方（起動 / CLI）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注/Execution）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 実行中は data/execution.pid に PID を書きます
    - Execution 側の停止は data/kill.flag による Kill Switch もしくは data/stop_requested.flag を立てる方法があります

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視は本番リスクの観点から本番 DB を参照する設計）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI/Regime/Research モジュール（ライブラリ呼び出し）
  - Python スクリプトや REPL から関数をインポートして利用できます。
  - 例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

- ログ
  - デフォルトでは stdout と日次ローテーションのファイル（logs/<app_name>.log）に出力されます。
  - ログ出力先は LOG_DIR で指定可能。

---

## 運用上の重要事項 / 注意点

- Kill Switch・Stop フラグ
  - Kill Switch: Settings.kill_flag_path（デフォルト data/kill.flag）に文字列を書き込むことで ExecutionEngine に停止シグナルを送ります（Monitoring の KillSwitch が書き込み）。
  - Stop フラグ: data/stop_requested.flag は各 run_* スクリプトが存在をチェックして安全に停止するために使用します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では危険なためデフォルトは 0 を推奨します。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視（monitoring）は本番 sqlite_path を参照する設計に注意してください。

- 自動 .env 読み込み
  - プロジェクトルート上の `.env` と `.env.local` を自動読み込みします（OS 環境変数を上書きしない）。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途等）。

- OpenAI API の利用
  - AI モジュールは OPENAI_API_KEY を要求します。未設定時は ValueError を投げます（メソッドに api_key を渡すことでも指定可）。
  - API の失敗時はフェイルセーフ（ゼロやスキップ）で継続する設計の箇所が多くありますが、API 呼び出し料は実運用で注意してください。

---

## ディレクトリ構成（主要ファイル解説）

以下は `src/kabusys/` 配下の主要ファイル・モジュールです（抜粋）。

- __init__.py
  - パッケージ情報（__version__ など）
- config.py
  - Settings クラス（.env / 環境変数の読み込み・検証）
  - 自動 .env ロードロジック
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID 管理、stop flag チェック、paper_trading 分離）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- monitoring/
  - monitoring_db.py：SQLite スキーマ作成・MonitoringDB（読み書きユーティリティ）
  - system_monitor.py：CPU/メモリ/ディスク・データ鮮度・プロセスチェック
  - risk_monitor.py：ドローダウン・ポジション上限監視
  - trade_monitor.py：トレード関連の監視（滞留注文等） — （ファイル内参照あり）
  - monitoring_engine.py：複数 Monitor を束ねる実行ループ
  - kill_switch.py：kill.flag の書き込み・管理
  - alert_manager.py：アラート送信（LINE 等、別実装を想定）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注フローの中核（Engine、Order 管理、Risk）
- portfolio/
  - portfolio_builder.py：候補選定・重み計算
  - position_sizing.py：株数算出・単元丸め・資金配分
  - risk_adjustment.py：セクター制限・レジーム乗数
- research/
  - factor_research.py：Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py：将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py：ニュースを OpenAI でセンチメント付与 → ai_scores テーブルへ
  - regime_detector.py：ETF MA とマクロニュースで日次レジーム判定
- data/
  - （実行時に生成されるファイル）
  - monitoring.db, paper_trading.db（paper モード用）, kabusys.duckdb（分析用）
  - kill.flag, stop_requested.flag, execution.pid 等
- logs/
  - デフォルトログ保存先（日次ローテーション）

また、tools/ 内に Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）が存在します。

---

## 参考コマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL 等からの利用例
  - from kabusys.research import calc_momentum
  - from kabusys.ai.news_nlp import score_news

---

## 最後に / 運用メモ

- 本リポジトリは運用リスクを伴う発注機能を含みます。`KABUSYS_ENV=live` に設定する前に必ず設定検証（validate_config）とテストを実施してください。
- .env に API キー等の機密情報を置く場合は十分に管理してください（Git にコミットしない）。
- monitoring と execution は stop / kill フラグファイルで連携する仕組みがあるため、運用時は data/ 以下のフラグファイルの取り扱いに注意してください。

---

README に追加して欲しい内容（デプロイ手順の詳細、systemd/supervisor 用のサービス定義、CI/CD 設定例、DB 初期データ投入スクリプトなど）があれば教えてください。必要に応じて追記・テンプレート作成します。