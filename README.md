# KabuSys

日本株向け自動売買システム（ライブラリ兼起動スクリプト群）

このリポジトリは、売買実行エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュースNLP/レジーム判定）などを含む自動売買プラットフォームのコードベースです。起動スクリプトと CLI ツールを提供しており、ローカル開発・ペーパートレード・本番（live）に対応します。

バージョン: 0.1.0

---

## 概要（Project overview）

- ExecutionEngine: ブローカークライアントと注文管理・リスク管理を組み合わせて発注を行う。
  - KABUSYS_ENV=`paper_trading` の場合は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離します。
- Monitoring: System / Trade / Risk モニタをポーリングしてログを残し、条件によって Kill Switch を発動（data/kill.flag）します。
- Portfolio モジュール: 銘柄選定、重み算出、ポジションサイズ計算、セクター上限など純関数群を提供。
- Research モジュール: DuckDB 上の時系列データからファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析を行う。
- AI モジュール: OpenAI を利用してニュースをスコア化（news_nlp）し、マクロニュースと ETF の MA 乖離を合成して市場レジーム判定（regime_detector）を行う。
- ユーティリティ: ログ設定、プロセス優先度設定、設定読み込み/ウィザード/検証ツールなど。

---

## 主な機能一覧（Features）

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- DB 周り
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）
  - SQLite（監視ログ・発注ログ: data/monitoring.db、ペーパートレード時は data/paper_trading.db）
  - init_monitoring_db によるスキーマ作成・マイグレーション
- 監視・アラート
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度チェック
  - TradeMonitor / RiskMonitor: 取引/ドローダウン/ポジション上限等の監視（ログ・risk_logs）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
- ポートフォリオ構築・サイズ計算（等重/スコア重み/リスクベース）
- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
- AI 機能（OpenAI）
  - ニュースセンチメントのスコアリング（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 によるレジーム判定（market_regime テーブルへ書き込み）

---

## 必要な依存（主な外部パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- （任意）PyYAML（config/*.yaml の検証を行う場合）
- その他の標準ライブラリ

（requirements.txt は本リポジトリに含まれていないため、上記を環境にインストールしてください）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（Setup）

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install duckdb psutil openai pyyaml
4. .env を用意
   - 対話式ウィザードを利用（推奨）
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（下記の例参照）
5. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. 必要に応じて data ディレクトリや logs ディレクトリが自動作成されます（ログ設定がディレクトリ作成に失敗した場合はコンソール出力のみになります）

.env のサンプル（代表的なキーとデフォルト値）
- KABUSYS_ENV=development|paper_trading|live (デフォルト: development)
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

（.env は絶対にリポジトリにコミットしないでください）

---

## 使い方（Usage）

起動スクリプトはモジュールとして実行します。

- ExecutionEngine を起動（本番またはペーパー）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。停止は stop フラグ作成かプロセスに終了を送信してください。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト: 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は監視結果を sqlite（settings.sqlite_path）に書き込み、duckdb に接続してデータ鮮度などを確認します。
  - 停止はリポジトリルート/data/stop_requested.flag ファイルの作成で検知して終了します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で .env を生成・上書きできます。

- 設定検証
  - python -m kabusys.validate_config
  - 必須環境変数や config/*.yaml の存在チェック、パスの親ディレクトリの有無などを検証します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）
  - 稼働率・注文成功率・送信率・レイテンシなどを集計して PASS/FAIL を判定します。

注意: AI 機能（news_nlp, regime_detector）を利用する場合は OPENAI_API_KEY を設定してください。OpenAI 呼び出しに失敗した場合はフォールバック（ゼロ扱い）して継続する設計になっていますが、正しい API キーの設定を推奨します。

停止と Kill Switch
- Monitoring の KillSwitch は RiskMonitor の結果に応じて data/kill.flag を書き込み、ExecutionEngine 側で検知して停止します。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効化できますが、本番では 0（クリアしない）を推奨します。

ログ
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力（30 日保持）。コンソールは stdout に出力されます。
- アプリケーション: "execution" / "monitoring" 等を指定して起動スクリプトから呼ばれます。

---

## 主要モジュール説明（短め）

- kabusys.config / Settings: 環境変数の抽象化。自動 .env ロード機構・必須変数チェックを提供。
- kabusys.run_execution: ExecutionEngine の起動スクリプト。paper_trading 時は専用 DB に切り替え。
- kabusys.run_monitoring: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔制御。
- kabusys.monitoring.*: MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, monitoring_db（永続化層）、KillSwitch, AlertManager（アラート送信）等。
- kabusys.portfolio.*: 銘柄選定・重み計算・ポジションサイズ計算・セクター上限・レジーム乗数。
- kabusys.research.*: DuckDB を使ったファクター計算（calc_momentum/calc_volatility/calc_value）、IC 計算等。
- kabusys.ai.*: news_nlp（ニュースセンチメントを OpenAI でスコア化）、regime_detector（ETF MA + マクロセンチメント合成）。
- kabusys.utils.*: logging_setup（統一ログ設定）、process_priority（プロセス優先度/Cpu affinity 設定）。

---

## 環境変数（代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: ブローカークライアントは Mock を使用、DB は PAPER_TRADING_SQLITE_PATH に記録
  - live: 本番モード（注意して設定を行ってください）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1)

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py                    # 環境変数読み込み・Settings
    config_setup.py              # 対話式 .env ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # SystemMonitor 起動スクリプト
    utils/
      logging_setup.py           # ログ設定ユーティリティ
      process_priority.py        # プロセス優先度設定
    monitoring/
      monitoring_db.py           # SQLite 永続化層
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
    execution/                    # 発注関連（Engine, OrderManager, BrokerFactory 等）
      ...
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    tools/
      paper_verification_report.py
    data/                         # （実行時に利用する想定）data/*.db, stop/kill フラグ等
    logs/                         # ログ出力先（デフォルト）

---

## 運用上の注意（補足）

- 本番（KABUSYS_ENV=live）では .env の中身（API トークン等）管理に十分注意してください。validate_config は live の場合に追加警告を出します。
- kill.flag 周りは重要な安全機構です。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険な自動クリアが行われるため推奨されません。
- OpenAI 利用時は API のレートリミットやエラーを考慮した設計（リトライ、バックオフ、部分失敗時のデータ保護）が組み込まれていますが、API キーの管理とコスト監視を行ってください。
- ログディレクトリ作成に失敗した場合はファイル出力は無効化され、コンソールログのみとなります。CI/cron 等で実行する場合は logs/ の書き込み権限に注意してください。

---

この README はコードベースの主要点をまとめたものです。機能の詳細・拡張・内部実装は各モジュールの docstring / コメントを参照してください。必要であれば各コンポーネントごとの詳細ドキュメントも作成できます。