# KabuSys

日本株向け自動売買プラットフォームの一部を構成するライブラリ群および起動スクリプト群です。本リポジトリには、ポートフォリオ構築、リスク制御、監視、ペーパートレード用検証ツール、LLM を用いたニュース分析・レジーム判定などの機能が含まれます。

---

## プロジェクト概要

KabuSys は以下の機能を目的としたモジュール群を提供します。

- 日次／リアルタイムの戦略実行（ExecutionEngine）
- システム稼働状況の監視（Monitoring）
- リスク検出と Kill Switch（停止フラグ）による安全停止
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ用ファクター計算・特徴量解析（DuckDB ベース）
- OpenAI を利用したニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- ペーパートレード検証レポート生成ツール

設計上の特徴：
- 設定は .env / 環境変数で管理（Settings クラス）
- 本番とペーパートレードの DB を分離可能
- ログは stdout と日次ローテート（logs/）へ出力
- 外部 API 呼び出し（OpenAI 等）はキーによる明示的な設定を前提

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード切替）
  - ブローカーの抽象化（BrokerClientFactory）
  - 注文管理、リスク管理、再整合（Reconciler）など

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch による停止フラグ出力（data/kill.flag）
  - 監視ログ永続化（SQLite, monitoring_db モジュール）

- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 等分配・スコア重み配分（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- リサーチ / データ処理
  - DuckDB を使ったファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算、統計要約（feature_exploration）

- AI（OpenAI）連携
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に格納
  - regime_detector.score_regime: マクロ記事 + ETF ma200 乖離で市場レジーム判定

- ツール
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - psutil
  - PyYAML（config 検証に任意）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション API / OpenAI を使う場合）

※ requirements.txt はリポジトリに含めていない想定です。上記パッケージを pip でインストールしてください。

例:
pip install duckdb openai psutil pyyaml

---

## セットアップ手順

1. ソースを取得して仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai psutil pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動編集（例を下に記載）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要であれば）
   - mkdir -p data logs

6.（OpenAI を使う場合）OPENAI_API_KEY を .env に設定

注意:
- KABUSYS_ENV が paper_trading の場合、実行エンジンは MockBrokerClient を使用し、デフォルトで data/paper_trading.db を用います。本番 DB（monitoring.db 等）とは分離されます。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（kill.flag が自動で消えるため）。production では 0 を推奨。

---

## 使い方

基本的には Python モジュールとして起動します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。

- 監視モニタを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（省略時は 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

ログ:
- logs/<app_name>.log に日次ローテートで出力（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout を使用

停止フラグ:
- 停止指示（外部からの停止）: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが安全に終了します
- Kill Switch: 監視側から data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与える設計です（KillSwitch）。

注意点:
- プロセス優先度（set_process_priority）は高優先に設定します。OS 権限により失敗する場合がありますが、警告ログを出して継続します。
- PID ファイルは data/execution.pid（デフォルト）に書き込まれます。権限や競合に注意してください。

---

## 主要な環境変数（例）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password

一般（よく使う／デフォルトあり）:
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...（news_nlp / regime_detector を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN=（アラート送信用）
- LINE_USER_ID=（アラート送信先）

監視関連:
- MONITOR_POLL_INTERVAL=60  （run_monitoring のポーリング間隔 秒）
- KILL_FLAG_PATH=data/kill.flag
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_CLEAR_ON_START=0 or 1（起動時に kill.flag を自動クリアするか。開発用にのみ 1 を推奨）

推奨: .env を作成し上記を管理（config_setup.py で生成可能）。プロジェクトルートの .env が自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

例 .env（機密値はマスク）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxx
KILL_FLAG_CLEAR_ON_START=0

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境設定読み込み / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — マクロ + ETF ma200 によるレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - trade_monitor.py       — （注文関連監視; 実装ファイル参照）
  - monitoring_engine.py   — 複数モニタの統合ループ
  - kill_switch.py         — Kill Switch 実装
  - alert_manager.py       — アラート送信（LINE 等）（実装参照）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity
  - その他ユーティリティ

ルート（実行やデータ保存先）:
- data/                    — デフォルト DB / フラグファイル / pid が置かれる想定
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/                    — ログファイル出力

---

## よくあるトラブルと対処

- 「.env の必須変数が未設定」と言われる
  - python -m kabusys.config_setup で .env を生成し、必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

- OpenAI が使えない／キーがない
  - ai.news_nlp / regime_detector は OPENAI_API_KEY が必要です。キーが無い場合は該当機能を使わないでください（またはモック実装に差し替え）。

- logs ディレクトリが作成できない
  - setup_logging はログディレクトリ作成に失敗するとコンソールのみの出力にフォールバックします。権限を確認しディレクトリを手動で作成してください。

- プロセス優先度設定でエラーが出る
  - set_process_priority は権限や OS により失敗する場合があります。警告ログが出て続行します。必要なら管理者権限で実行してください。

- 停止できない／ループが終わらない
  - run_execution / run_monitoring は data/stop_requested.flag の存在を監視します。停止したい場合はこのファイルを作成してください（安全停止）。また Kill Switch は data/kill.flag を書き込みます。

---

## 開発者向けメモ

- DuckDB 接続は research／ai モジュールで使われます。prices_daily / raw_financials / raw_news 等のテーブル構造に依存しています。
- monitoring_db.init_monitoring_db() で SQLite の初期テーブルを自動作成します（冪等）。
- 多くのモジュールは「外部依存（API）」の失敗をフェイルセーフに扱い、ログを残して処理を継続する設計です。
- テストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動の .env ロードを抑制できます。

---

必要であれば、この README の英語版や systemd ユニットファイル例、docker-compose 例、requirements.txt のテンプレート、または各モジュールの API 使用例（コードスニペット）を追加で作成します。どれが欲しいか教えてください。