# KabuSys

日本株自動売買システムの Python コードベース。ポートフォリオ構築、発注実行、監視、研究（ファクター計算・特徴量解析）、およびニュース NLP / レジーム判定などの補助機能を含むモジュール群で構成されています。

以下は本リポジトリの概要・セットアップ手順・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主要機能は次のとおりです。

- 発注エンジン（ExecutionEngine） — ブローカークライアントを通じた注文管理と発注
- 監視（Monitoring） — システム状態・データ鮮度・注文の健全性・リスク監視と Kill Switch
- ポートフォリオ構築（Portfolio） — 候補選定・重み付け・ポジションサイズ計算、セクター制約
- 研究（Research） — ファクター計算（Momentum/Value/Volatility）、将来リターン、IC 等
- AI 補助（AI） — ニュースのセンチメント評価、マクロセンチメントによるレジーム判定
- ユーティリティ — ロギング、プロセス優先度設定、設定ウィザード・検証ツール、レポート生成 等

設計上のポイント:
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV=`paper_trading` 時は専用 SQLite を使用）
- ルックアヘッドバイアス回避のため日付の扱いに注意した実装
- OpenAI（ニュース NLP / レジーム判定）用の呼び出しは冪等性・リトライを考慮

---

## 機能一覧（抜粋）

- config_setup: .env を対話式に作成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: 環境変数・config/*.yaml を起動前に検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
- run_monitoring: SystemMonitor のポーリングループ（python -m kabusys.run_monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
- monitoring_engine: 複数モニタを束ねるランナー（テスト用 run_once / 本番用 run）
- tools.paper_verification_report: ペーパートレード検証レポート生成（期間指定可）
- portfolio: 候補選定・重み計算・位置サイズ計算・セクターキャップ・レジーム乗数
- research: ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント評価・レジーム判定
- utils.logging_setup: 統一ログ設定（コンソール + 日次ローテーション）
- utils.process_priority: プロセス優先度設定（Windows / POSIX 対応）
- monitoring.monitoring_db: 監視用 SQLite スキーマ・CRUD ユーティリティ

---

## 必要条件（例）

- Python 3.9+（実行環境に合わせて調整してください）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config YAML 検証を使う場合）
- 任意: J-Quants / kabuステーション の API クレデンシャル（環境変数で指定）

例:
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使ってください）
pip install -r requirements.txt

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または
   - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成
   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LOG_LEVEL（DEBUG/INFO/...）
   - KILL_FLAG_CLEAR_ON_START（本番での自動クリアを防止するためデフォルトは 0 推奨）

5. ディレクトリの作成（手動で必要に応じて）
   - mkdir -p data logs

---

## 使い方（主要なコマンド・モジュール）

基本的にはパッケージをモジュール実行します。パッケージルートで次を実行してください。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

- 実行エンジンの起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が存在する場合は起動しない
    - 停止はデータディレクトリの stop フラグや kill.flag により制御（下記参照）

- 監視ループの起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 常に本番用 sqlite_path（SQLITE_PATH）を使う仕様（監視データは本番 DB に記録されます）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - OpenAI を使うには OPENAI_API_KEY を環境変数に設定
  - ニュース NLP（銘柄ごとのスコア付与）:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ロギング:
- logs/ 以下にアプリ名ごとの日次ローテートログが作られます（utils.logging_setup が行う）。
- LOG_DIR 環境変数で変更可能。

停止・Kill Switch:
- ExecutionEngine 停止: data/kill.flag を書き込むことで Execution 停止シグナル（KillSwitch）を発動可能
  - デフォルトパスは Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch は冪等で、既に存在する場合は再書き込みしません
- 単純な停止フラグ: run_monitoring / run_execution は data/stop_requested.flag の存在を監視してループを終了します
- execution.pid（PID ファイル）: 実行中のエンジンが PID を書き込みます（デフォルト data/execution.pid）

---

## 環境変数の主な一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能用)
- KABUSYS_ENV (development / paper_trading / live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定モード: instant | partial | never | reject)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存先)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒)
- KILL_FLAG_CLEAR_ON_START (0/1。本番では 0 推奨)

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数・設定管理
    - config_setup.py              — .env 対話ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度設定
    - monitoring/
      - monitoring_db.py           — SQLite スキーマ・DB 操作
      - system_monitor.py          — システム監視（プロセス・データ鮮度など）
      - trade_monitor.py           — 注文監視（滞留・約定異常 等）
      - risk_monitor.py            — ドローダウン・ポジション上限監視
      - kill_switch.py             — Kill Switch 実装（kill.flag 書込）
      - alert_manager.py           — （アラート送信管理: LINE 等と連携想定）
      - monitoring_engine.py       — 複数 Monitor を束ねたエンジン
    - execution/
      - execution_engine.py        — 実行エンジン本体（EngineConfig 等）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py       — 候補選定 / 重み計算
      - position_sizing.py         — 発注株数計算（lot 丸め等）
      - risk_adjustment.py         — セクター制約・レジーム乗数
    - research/
      - factor_research.py         — momentum/value/volatility 等
      - feature_exploration.py     — 将来リターン・IC・統計サマリ
    - ai/
      - news_nlp.py                — ニュースを OpenAI でスコア化
      - regime_detector.py         — マクロ + ETF MA によるレジーム判定
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート

---

## 開発時の注意点 / ヒント

- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしておくことを推奨します（自動クリアは危険）。
- Paper Trading は本番 DB と分離されます。KABUSYS_ENV=paper_trading の際は PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を利用する機能は API レート制限やネットワークエラーに備えたリトライロジックを持ちますが、API キー/コスト管理には注意してください。
- ログは console 出力（stdout）と logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリのパーミッションに注意。
- monitoring は本番 sqlite_path を参照する仕様の箇所があるため、監視 DB の設定に注意してください。

---

## よく使うコマンドまとめ

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## サポート / 貢献

- バグ報告・改善要望は Issue を立ててください。
- 新機能追加や修正は Pull Request を送ってください。コード規約・テスト追加を推奨します。

---

README は以上です。追加で「実行例（ログ出力サンプル）」「より詳しい設定項目の説明」や「各モジュールの API ドキュメント」を作成することもできます。希望があれば教えてください。