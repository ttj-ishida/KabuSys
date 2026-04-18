# KabuSys

日本株自動売買システムのコアライブラリ群 — 設定 / 監視 / 発注エンジン / 研究・ポートフォリオ構築 / AI 補助モジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供する Python パッケージです。

- 環境変数ベースの設定管理（.env サポート）
- 発注実行エンジン（ExecutionEngine）と注文管理（OrderManager 等）
- モニタリング（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量評価）
- AI 補助（ニュースセンチメント、レジーム判定；OpenAI 経由）
- 各種ユーティリティ（ログ設定、プロセス優先度設定 等）
- ペーパートレード専用 DB を使った検証用ツール

設計方針の一部：
- 本番 DB とペーパートレード DB は分離（paper_trading 環境時のみ paper DB を使用）
- ルックアヘッドバイアス防止（date.today() / datetime.today() を安易に参照しない設計）
- フェイルセーフ：外部 API 失敗時はフォールバックして継続（可能な限り安全側に）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートが検出できる場合）
  - 対話式設定ウィザード (`python -m kabusys.config_setup`)
  - 設定検証 CLI (`python -m kabusys.validate_config`)
- 実行エンジン
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` なら MockBroker を使い paper_trading DB に記録
- 監視
  - `run_monitoring.py`：SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - Kill Switch：条件に応じて `data/kill.flag` を作成し ExecutionEngine を停止
  - 監視ログ: SQLite（デフォルト: `data/monitoring.db`）に永続化
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算（ロット丸め、aggregate cap）
  - セクター上限・レジーム乗数の適用
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI 経由）
  - ニュースを LLM でセンチメント化して `ai_scores` に書き込み（`kabusys.ai.news_nlp`）
  - マクロセンチメント＋ETF MA200 で市場レジーム判定（`kabusys.ai.regime_detector`）
- ツール
  - Paper Trading 検証レポート生成 (`python -m kabusys.tools.paper_verification_report`)

---

## 必要条件（概略）

- Python 3.10+
- 主な Python ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML （設定 YAML の検証に必須。なくても動作するが検証をスキップ）
- SQLite（標準ライブラリで対応）

具体的な requirements.txt はリポジトリに含まれていない場合があるため、上記をインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存をインストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - または最低限: pip install duckdb psutil openai PyYAML

3. `.env` の作成
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - または手動でルートに `.env` を置く。主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_station_password>
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=<your_openai_key>  （AI 機能を使う場合必須）

   自動ロード挙動:
   - OS 環境変数 > .env.local（存在すれば上書き） > .env
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup
    - .env の初期生成 / 更新を対話式で行います

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録。
    - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
    - 実行中は `data/execution.pid` に PID を書きます。停止は `data/stop_requested.flag` を作成することで実行中のスレッドに検知させることができます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - SystemMonitor をポーリングし監視ログを SQLite に記録。MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を上書き可（デフォルト: 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（環境に依存せず監視 DB は共通で使われる仕様）。
    - 停止はリポジトリルートの `data/stop_requested.flag` を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
    - 稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL を出力

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI を使ってニュースセンチメントを ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定を market_regime に書き込む
  - どちらも OPENAI_API_KEY 環境変数または api_key 引数が必要

---

## 主要環境変数（簡易まとめ）

- 必須（少なくとも validate_config が警告・エラーにする）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- DB パス
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- ログ / 実行制御
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）

- 監視間隔
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）

- OpenAI
  - OPENAI_API_KEY（AI 機能を使うときに必要）

その他、多数の閾値やモード（PAPER_FILL_MODE 等）は Settings クラスで定義されています（詳細は kod 内の `kabusys.config.Settings` を参照してください）。

---

## ロギング

- 共通セットアップ: `kabusys.utils.logging_setup.setup_logging` を全起動スクリプトが使っています。
- 出力:
  - コンソール（stdout）
  - ファイル（タイムベースでローテーション、デフォルト保存先 `logs/<app_name>.log`、30 日分保持）
- ログディレクトリは `LOG_DIR` 環境変数で変更可能。作成できない場合はファイル出力はスキップして stdout のみになります。

---

## 停止 / Kill Switch の仕組み

- ExecutionEngine 停止トリガー:
  - `KillSwitch` が `RiskMonitor` 等の結果を評価し、条件を満たすと `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）を書き込みます。
  - `run_execution` は外部フラグ `data/stop_requested.flag` を監視してエンジンの停止を指示します（停止フラグは起動スクリプト同士で共有）。
- 運用上の注意:
  - 本番環境で `KILL_FLAG_CLEAR_ON_START=1` は危険 → validate_config で警告します。
  - kill.flag はファイルの存在で判定するため、必要に応じて削除してクリアしてください（KillSwitch.clear() が実装されています）。

---

## ディレクトリ構成（抜粋）

（以下はパッケージ内の主なファイル・モジュールを示します）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - config_setup.py               — .env 対話ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py            — ログ設定ユーティリティ
      - process_priority.py         — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py            — SQLite 永続化層
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (存在)
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (存在)
    - execution/
      - execution_engine.py         — ExecutionEngine の実装
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/                    — 監視関連（上記）
    - tools/
      - paper_verification_report.py
    - data/                          — 実行時に使用するファイル配置（logs/, data/ 等はプロジェクトルートに作成）
- pyproject.toml / setup.py 等（パッケージ化に応じて存在）

（実際のリポジトリではさらにモジュールやサブパッケージが存在します）

---

## 開発者向けメモ / 注意点

- Python の型ヒント（`X | None` など）を使っているため Python 3.10 以上を推奨します。
- DuckDB 接続を多用するため、大量データの列指向分析に向いています。
- OpenAI API 呼び出しはリトライ・バックオフを実装していますが、API キーの上限や課金に注意してください。
- 監視ログ（SQLite）はスキーママイグレーション処理を含みます（起動時に不足カラムを追加）。
- 実運用では `KABUSYS_ENV` の `live` 設定時は config の中身を十分にレビューしてください（validate_config によるガードあり）。

---

## トラブルシューティング（よくある質問）

- .env が読み込まれない
  - プロジェクトルートが検出できない、または KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている可能性があります。
  - 手動で `.env` をルートに置くか、環境変数を直接エクスポートしてください。

- run_execution が起動しない / すぐ終了する
  - `data/stop_requested.flag` が存在すると起動を行いません。削除して再起動してください。
  - `validate_config` で必須環境変数が不足していないか確認してください。

- AI 機能でエラーが出る
  - OPENAI_API_KEY が未設定であれば ValueError が出ます。環境変数を設定してください。
  - ネットワークや API 制限は復帰処理がありますが、継続的な失敗はログを確認してください。

---

この README はコードベース（src/kabusys 以下）の主要な機能と運用手順の要約です。詳細実装や追加の CLI オプションは各モジュールのドキュメント（モジュール docstring）やソースを参照してください。必要であれば README の補足（例: 具体的な .env.example、systemd ユニットの例、CI/CD のセットアップ例など）を追加できます。希望があれば教えてください。