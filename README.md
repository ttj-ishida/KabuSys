# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ/実行スクリプト群）。  
この README はコードベースの主要コンポーネント、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買プラットフォームのモジュール群です:

- 取引実行（ExecutionEngine） — ブローカークライアント経由で発注を行うエンジン。`KABUSYS_ENV` によって paper_trading（モック） / live（本番）を切替可能。
- 監視（Monitoring） — システム状態、注文・約定ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、必要なら Kill Switch（停止フラグ）を発動。
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、単元丸め、リスク調整などの純粋関数群。
- リサーチ（Research） — DuckDB 上の株価・財務テーブルを用いたファクター計算・特徴量解析。
- AI（news_nlp / regime_detector） — OpenAI を使ったニュースセンチメント集計・市場レジーム判定（OpenAI API キーが必要）。
- ユーティリティ — ログ設定、プロセス優先度設定、設定読み込み/ウィザード、設定検証 CLI、レポートツール等。

設計方針の一部：
- DuckDB と SQLite を使い、分析データと監視/履歴データを分離。
- Paper trading（ペーパートレード）は本番 DB と分離された専用 SQLite を使用。
- LLM を使う部分（news_nlp, regime_detector）は API キーが必要。API失敗時はフェイルセーフで継続する設計。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（デーモン的にセッションを実行）
  - ブローカークライアント切替（実口座 / MockBroker for paper_trading）
  - リスク管理（制限・レート制御・サーキットブレーカー）
- 監視系
  - run_monitoring.py: SystemMonitor をポーリングして system_status 等を記録
  - MonitoringEngine: SystemMonitor, TradeMonitor, RiskMonitor を束ねてアラート・Kill Switch評価
  - KillSwitch: data/kill.flag による ExecutionEngine 停止シグナル
- ポートフォリオ
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp: ニュース記事を LLM で評価し ai_scores に書き込み
  - regime_detector: ETF とニュースを組合せてレジーム判定
- ツール
  - config_setup.py: .env 対話ウィザード（初期設定）
  - validate_config.py: .env / config/*.yaml の検証 CLI
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

前提:
- Python 3.9+ がインストールされていること（DuckDB/psutil/OpenAI クライアント等は pip でインストール）
- 必要なネイティブライブラリ（OS に依存する）については各ライブラリのドキュメント参照

1. リポジトリをクローン / 作業ディレクトリに配置。

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（requirements.txt がない場合は主要依存のみ）:
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他のパッケージを追加）

4. .env を作成:
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（例は下記参照）

5. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

6. データディレクトリの作成:
   - デフォルトでは `data/` 配下に SQLite / pid / flag が置かれるため、書き込み可能なディレクトリを確保してください。`setup_logging` が logs/ を作成します。

環境変数の自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動的に読み込まれます（OS 環境 > .env.local > .env）。無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主要な環境変数（一部抜粋とデフォルト）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject", デフォルト: instant)
- LOG_LEVEL (DEBUG/INFO/...)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒数、デフォルト 60)

例 (.env)
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方

### 設定ウィザード
- .env を対話式で作成:
  - python -m kabusys.config_setup

### 設定検証
- 設定の簡易チェック:
  - python -m kabusys.validate_config
- 警告も失敗扱いにする:
  - python -m kabusys.validate_config --strict

### 実行エンジン（ExecutionEngine）
- 実行開始（通常は systemd / supervisor / コンテナ 等で起動）:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID を書きます。停止は Kill Switch（data/kill.flag）や stop_requested.flag によるシグナルで行います。

### 監視（SystemMonitor）
- 監視ループ開始:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
- 挙動:
  - 監視は monitoring DB（Settings.sqlite_path）にログを残します（環境に関わらず本番 sqlite_path を参照する設計箇所あり）。
  - 停止はプロジェクトルート/data/stop_requested.flag を検出して終了します。
  - システム状態（CPU/Mem/Disk）、データ鮮度、プロセス死活などを評価して監視用テーブルへ記録します。

### Kill Switch（停止フラグ）
- Kill Switch は監視側や手動操作で `data/kill.flag` に理由テキストを書き込み、ExecutionEngine に停止シグナルを送ります。
- KillSwitch.evaluate はドローダウン超過やポジション上限超過を検出したときにフラグを書きます。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は起動時に kill.flag を自動クリアするオプションがあります（本番では推奨されません）。

### Paper Trading 検証レポート
- ペーパートレードの検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルトの DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

### AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーを環境変数 `OPENAI_API_KEY` にセットしてください。
- news_nlp.score_news / regime_detector.score_regime を呼び出すことで ai_scores / market_regime テーブルへ書き込みます。
- API 失敗時はフェイルセーフ（0.0 など）で続行する設計です。

---

## 実行上の注意点

- 本番環境（KABUSYS_ENV=live）の場合、設定ミスは重大な発注ミスを招くため validate_config で十分にチェックしてください。
- `.env` は絶対にコミットしないでください（config_setup のヘッダにも記載）。
- Paper trading は実取引を行わない設計ですが、実装の差に依存するため挙動はコードを確認してください。
- ログは `logs/<app_name>.log` に日次ローテーションで出力されます（デフォルト 30 日保存）。`LOG_DIR` 環境変数で変更可能。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル/モジュールの構成（リポジトリ内のファイル群に基づく抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数/.env ロードと Settings クラス
    - config_setup.py            # .env 対話ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py              # ニュースセンチメント（OpenAI）
      - regime_detector.py       # 市場レジーム判定（OpenAI）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py         # SQLite のスキーマ・永続化操作
      - system_monitor.py
      - trade_monitor.py         # （trade_monitor 実装あり）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py         # （アラートマネージャ実装あり）
    - utils/
      - __init__.py
      - logging_setup.py         # ログ初期化ユーティリティ
      - process_priority.py      # プロセス優先度 / CPU affinity
    - execution/                  # 発注関連コンポーネント（エンジン/リスク/リコン/リポジトリ 等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/                 # 上述（監視関連）
    - research/                   # 上述（リサーチ関連）

（実際のリポジトリではさらに細分化されたファイルが存在します。上は主要モジュールの概観です。）

---

## 追加情報 / トラブルシューティング

- 自動環境ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると `.env` の自動ロードがスキップされます（テスト時便利）。
- ログディレクトリ作成に失敗した場合:
  - `setup_logging` は失敗を検出してコンソール（stdout）のみにフォールバックします。パーミッション等を確認してください。
- DuckDB / SQLite のパスが存在しない場合:
  - validate_config は親ディレクトリの存在有無を警告します。起動時に自動で作成されることが多いですが、権限等を確認してください。
- OpenAI 呼び出しのテスト:
  - news_nlp 内の `_call_openai_api` はテスト時にパッチしやすいように分離されています（unittest.mock.patch 推奨）。

---

この README はリポジトリ内の主要スクリプトとモジュールに基づいて作成しています。詳細な設計（アルゴリズム、シグネチャ、DB スキーマの詳細）は各モジュールの docstring / ソースコードを参照してください。必要であれば各モジュールごとの使い方サンプルを追加で作成します。