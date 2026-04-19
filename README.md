# KabuSys

日本株向け自動売買システム（簡易ドキュメント）

この README はコードベース（src/kabusys/...）の概要、機能、セットアップ手順、使い方、主要ファイル構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（アルゴリズム取引）とそれを支えるモニタリング／リスク管理／リサーチ機能を備えた小規模なシステムです。  
主なコンポーネントは次のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム稼働・データ鮮度・注文状態・リスクを定期チェックしアラート／Kill Switch を管理
- Portfolio モジュール：候補選定、重み算出、ポジションサイズ計算などのポートフォリオ構築ロジック（純粋関数群）
- Research：DuckDB 上でファクター計算・特徴量解析を行うモジュール
- AI：OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- CLI ツール：.env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成（paper_verification_report）

設計上の特徴：
- 環境設定は .env / 環境変数経由で管理
- DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- Paper Trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV）
- OpenAI / 外部 API 呼び出しは明示的にキーを必要とする（環境変数または引数）

---

## 機能一覧

- Execution
  - Broker クライアント生成（実運用 or Mock）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた実行フロー
  - PID ファイル管理、停止フラグによる安全停止
- Monitoring
  - CPU/MEM/DISK/プロセス稼働チェック（system_status テーブルへ記録）
  - 注文ログ監視（trade_logs）
  - リスク監視（ドローダウン監視、ポジション上限）
  - Kill Switch（条件成立時に data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信（LINE 等の統合は設定次第）
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単位株・コストバッファ・aggregate cap）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上で完結）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ツール
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（概要）

1. Python 環境を用意
   - 推奨: 3.9+（コード中で typing | 演算子や新しいモジュールを使用）
   - 仮想環境（venv / pyenv / conda 等）を推奨

2. 依存パッケージをインストール
   - requirements.txt はリポジトリにない場合があるため、少なくとも以下をインストールしてください：
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（設定ファイル検証を行う場合・optional）
   - 例:
     pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動し .env を作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI を使う場合:
     - OPENAI_API_KEY を環境変数に設定（または score_* 関数に引数で渡す）

   - 簡易 .env（例）:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

4. ディレクトリ作成（データ / ログ）
   - data/ と logs/ を作成
     mkdir -p data logs
   - 一部処理は起動時に自動で作成される場合がありますが、事前作成を推奨

5. 設定検証（必須ではないが推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（起動コマンド例）

- ExecutionEngine を起動
  - 本番・デフォルト（KABUSYS_ENV に依存）
    python -m kabusys.run_execution
  - paper_trading モード（.env の KABUSYS_ENV=paper_trading を設定）では MockBrokerClient を使用し、data/paper_trading.db に記録されます。

- Monitoring を起動
  - デフォルトは 60 秒ごとのポーリング
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を秒で設定（例: 30 秒）
    export MONITOR_POLL_INTERVAL=30
  - 注意: Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite_path）を使用します（監視は本番 DB を参照する設計）。

- Paper Trading 検証レポートを生成
  - デフォルト DB: data/paper_trading.db
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- .env ウィザード（対話式）
  python -m kabusys.config_setup

- 設定検証（CLI）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0"/"1"）

---

## 停止 / Kill Switch / PID

- 停止フラグ（外部からの停止指示）:
  - data/stop_requested.flag — run_execution/run_monitoring スクリプトで監視される「手動停止」フラグ
  - data/kill.flag — KillSwitch により書き込まれ、ExecutionEngine を停止させるために使用される（監視が判定して書き込む）
- PID ファイル:
  - data/execution.pid — ExecutionEngine が使用（プロセス管理用）
- 実行時の振る舞い:
  - run_execution は起動時に stop flag が既に立っている場合は起動せず終了します
  - run_monitoring は stop flag を検知するとループを終了します

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュール／スクリプト）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings 定義
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + 永続化 API
    - system_monitor.py
    - trade_monitor.py       — （コード参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート統合ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

※上記はコードベースの一部を抜粋した一覧です。実際のリポジトリにはさらに補助モジュールや docs が存在する可能性があります。

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では特に設定を慎重に確認してください（validate_config にて警告あり）。LINE 等の通知設定は必須ではありませんが未設定だとアラートが届きません。
- Monitoring は監視用途で本番 sqlite_path（SQLITE_PATH）を参照します。監視データを意図せず Paper DB に送らないよう注意。
- Paper Trading（KABUSYS_ENV=paper_trading）は MockBroker を利用し DB を分離しますが、設定ミスによる混在に注意してください。
- OpenAI を利用する機能は API 利用制限・コストが発生します。API キーの管理とレート制限に注意してください。
- プロセス優先度設定（set_process_priority）は psutil を使い OS に依存するため、権限や OS によっては設定が反映されない場合があります。ログで警告が出力されます。

---

必要であれば、README に含めるサンプル .env.example や systemd / supervisor 用の起動ユニット例、依存パッケージの requirements.txt や Dockerfile のテンプレートも作成できます。どの情報を追加したいか教えてください。