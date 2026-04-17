# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注実行 → 監視・アラートまでを含む自動売買基盤の一部を実装したものです。DuckDB / SQLite をデータ層に用い、OpenAI を利用したニュース NLP やレジーム判定機能も備えています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的・設計方針
- 日本株向けの自動売買基盤を構成するモジュール群（ポートフォリオ構築、ポジションサイズ計算、リスク調整、発注実行、監視、レポート、研究用ファクター計算など）。
- データ分析は DuckDB、監視・発注ログは SQLite を使用。
- Paper Trading モードは本番 DB と分離し、擬似ブローカー（Mock）を用いる設計。
- OpenAI（GPT 系）を利用したニュースセンチメント評価やマクロセンチメントをレジーム判定に組み込む機能あり（API 呼び出しは適切にフォールバック/リトライ処理を行う）。
- 実行中プロセスの優先度制御や PID / フラグファイルによる停止制御、LINE によるアラート通知などの運用機能を備える。

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行スクリプト
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を常に使用（環境に依存せず）

- 監視（monitoring）
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）、約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を書き込みエンジン停止指示
  - AlertManager: LINE Push による通知（トークンが未設定ならログ出力のみ）

- ポートフォリオ構築（portfolio）
  - 候補選定（score / rank）
  - 重み算出（等配分、スコア加重）
  - セクター制限やレジーム乗数（regime multiplier）
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、aggregate cap）

- リサーチ / ファクター計算（research）
  - Momentum / Volatility / Value ファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等

- AI（ai）
  - news_nlp: raw_news を集約して OpenAI で銘柄ごとのセンチメントを算出し ai_scores に書込
  - regime_detector: ETF 1321 の MA200 乖離 + LLM マクロセンチメントで市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
    - 指定期間の稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定

---

## 前提 / 必要なパッケージ

推奨 Python バージョン: 3.10 以上

主要依存（例）
- duckdb
- psutil
- openai
- requests
- PyYAML（オプション: config YAML 検証用）

実行環境に合わせて requirements.txt を用意している場合は以下のようにインストールしてください:
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install --upgrade pip
- pip install duckdb psutil openai requests pyyaml

（プロジェクト内に requirements.txt がない場合は上記のパッケージを個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境作成・パッケージインストール（上記参照）
3. .env 作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（一部）:
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID（アラート送信に必要）
     - PAPER_FILL_MODE（paper_trading 時のマッチング方式: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視ループの秒数、例: 60）
4. 設定検証
   - python -m kabusys.validate_config
   - 重大な問題がないか確認。--strict を付けると警告も失敗扱いになります。
5. データディレクトリの準備
   - デフォルトの DB/フラグファイルは data/ 配下に置かれるため、必要に応じて作成してください（実行時に自動作成されることもあります）。
   - 監視の停止に使うフラグ:
     - data/stop_requested.flag — run_monitoring / run_execution の外部停止用（存在するとループを抜ける）
     - data/kill.flag — KillSwitch により書き込まれる停止指示フラグ

---

## 使い方 (主要コマンド)

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番/ペーパートレード）
  - python -m kabusys.run_execution
    - KABUSYS_ENV によって paper_trading / live / development が切替
    - ExecutionEngine 起動中は data/execution.pid に PID を書き込み
    - data/stop_requested.flag が作成されていると起動を回避または停止

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
    - run_monitoring は本番 sqlite_path（SQLITE_PATH）を参照してログを残します
    - 実行後は system_status / trade_logs / risk_logs / dashboard テーブルが作成される

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH の代替）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定後、該当モジュールの関数を呼び出してください（ライブラリ API）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime など

注意点
- KABUSYS_ENV=paper_trading の場合、発注は MockBroker を使い data/paper_trading.db にログを残します（本番 DB と分離）。
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。

---

## 運用・停止

- 外部から安全に停止するにはプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring / run_execution はこのファイルを検知して終了します）。
- KillSwitch により data/kill.flag が書き込まれると ExecutionEngine 側は停止判定を行います（本番運用では kill flag の取り扱いに注意）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で消します（本番では 0 推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                — 発注エンジン周り（Engine, OrderManager, BrokerFactory 等） ※一部ファイルは省略
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
  - data/ (実行時に使用されるデフォルトパス)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

その他に設定テンプレートや config/*.yaml（system_config.yaml など）が想定されています（config/ ディレクトリ）。validate_config はそれら YAML の存在やパースも検証します（PyYAML 必要）。

---

## 参考情報 / 注意事項

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に不足カラムがあれば簡易マイグレーションを行います（例: dashboard.peak_value, trade_logs.latency_ms）。
- AI モジュールは OpenAI API を利用するため API キーと通信環境が必要です。API 呼び出しはリトライやバックオフを実装していますが、API 料金・利用制限に注意してください。
- 実行ユーザーの権限によりプロセス優先度や CPU affinity の設定が失敗することがあります（その場合はログに警告が出ます）。
- 本リポジトリは自動売買ロジックを含みます。ライブ運用時は設定・リスクパラメータの慎重な確認を行ってください。

---

必要であれば README に「.env の最小例」や具体的な systemd サービス定義、運用手順（ログローテート、バックアップ、監視ダッシュボード接続方法など）を追加できます。追加したい情報を教えてください。