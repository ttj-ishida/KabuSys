# KabuSys

日本株向け自動売買システムのモノリスライブラリ（パッケージ）。  
このリポジトリはトレードロジック、監視、リサーチ、AI（ニュースセンチメント／レジーム判定）などを含む主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な複数コンポーネントをまとめたパッケージです。主な責務は以下のとおりです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- リスク管理、オーダー管理、再整合（reconciler）
- システム稼働監視・トレード監視（Monitoring）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI を使ったニュースセンチメント評価 / 市場レジーム判定（OpenAI 経由）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、ルックアヘッドバイアス防止や本番/ペーパートレードの明確な分離、フェイルセーフ（API失敗時に中断させない）などが取られています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper Trading モードをサポート（設定により MockBrokerClient を利用）
  - Paper Trading は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine の強制停止（Kill Switch）
  - 監視ログ永続化用 SQLite（monitoring.db）初期化と操作（monitoring_db モジュール）

- Portfolio construction
  - 候補選定、等分/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ算出（単元株丸め、aggregate cap スケーリング）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー

- AI（OpenAI）
  - ニュースを LLM でセンチメント評価して ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA200 を合成して日次レジーム判定を行い market_regime に書き込み

- 開発ツール
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、Python 仮想環境を作る
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - プロジェクトに requirements.txt が無い場合は、最低限以下をインストールしてください：
     - duckdb, psutil, openai, pyyaml
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合は `.env.example` を参照して `.env` を作成してください（リポジトリに .env はコミットしないでください）。

4. 設定検証（必須項目やパスなどをチェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB 等は `data/` 配下に配置されます。自動で作られることもありますが、必要に応じて手動作成してください。
   - ログは `logs/` 配下へ出力されます（LOG_DIR で変更可能）。

注意: `kabusys.config` モジュールは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動探索し、`.env` / `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV: execution の挙動を切り替える。値: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Paper Trading 用 DB を使い MockBroker を選択
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（monitoring）デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア。デフォルト "0"）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（起動 / コマンド例）

- ExecutionEngine を起動する
  - シンプル実行:
    - python -m kabusys.run_execution
  - Paper Trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading は PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 実行時にプロセス優先度を "high" に設定します（可能な場合）。
  - 実行は別スレッドで Engine.run_session を回し、data/stop_requested.flag を検知すると停止します。PID ファイルは data/execution.pid（デフォルト）に書き出されます。

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視モジュールは本番の sqlite_path（settings.sqlite_path）を使って monitoring テーブルを初期化します（環境にかかわらず本番パスを使用する仕様に注意）。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）をプログラムから呼ぶ
  - 例（Python スクリプト / REPL）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
    - score_regime(conn, target_date, api_key="...")

注意点:
- OpenAI を利用する機能は OPENAI_API_KEY の設定が必要です（関数にも api_key を渡せます）。
- monitoring の DB 初期化は init_monitoring_db を経由して安全に行われます。

---

## 停止 / Kill Switch

- 強制停止フラグ:
  - ExecutionEngine / Monitoring はプロジェクトの data/stop_requested.flag を監視しています。停止させたい場合はこのファイルを作成してください（空ファイルで可）。
- Kill Switch:
  - RiskMonitor が条件を満たすと `KILL_FLAG`（デフォルト data/kill.flag）を書き込み、外部の ExecutionEngine 起動プロセスに停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 配下の構成に基づきます）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py            # .env 対話型ウィザード
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py         # ログ初期化ユーティリティ
    - process_priority.py      # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py         # （一覧に依存ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         # （通知管理、ファイルは存在）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/                 # 監視関連（上記）
  - (その他: data, config, logs 等は実行時に参照/生成されます)

---

## 実装上の注意・設計メモ

- 環境に依存しない自動 .env ロード:
  - config.py はプロジェクトルートを探索し `.env` / `.env.local` を自動で読み込みます。テスト時等に無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading と本番 DB の分離:
  - run_execution は `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使用します（本番 DB と完全分離）。

- 監視（monitoring）は環境に関係なく本番 sqlite_path を使用する箇所があり、設計上の注意が必要です（run_monitoring の docstring 参照）。

- OpenAI 呼び出し:
  - ニュース NLP / レジーム判定は OpenAI API を使用します。API 呼び出しはリトライ（指数バックオフ）やレスポンス検証を行い、失敗時はフェイルセーフとして中立値やスキップで継続します。

- ロギング:
  - 共通の setup_logging を用いて root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定します。ログディレクトリが作成できない場合はコンソールログのみになります。

---

## トラブルシューティング / よくある質問

- 「必須環境変数が未設定」エラーが出る場合:
  - python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してください。

- OpenAI 関連で認証エラーが出る場合:
  - OPENAI_API_KEY を設定する、あるいは score_ 系関数に明示的に api_key を渡してください。

- ログファイルが出力されない:
  - LOG_DIR の指定とディレクトリ作成権限を確認してください。ディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります。

---

README は以上です。運用に合わせて .env の値やログ出力先、DB パスを調整してください。必要であれば、README を実行例や追加の運用手順（systemd / Docker / Supervisor 用の起動スクリプト）に拡張できます。