# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
このドキュメントはコードベースから抽出した概要・使い方・セットアップ手順をまとめた README です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買/研究プラットフォームです。主な役割は以下の通りです。

- 市場データ（DuckDB）を使ったファクター計算・研究モジュール
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（発注ロジック）とそれを監視する Monitoring
- Paper Trading と Live の運用モードに対応
- ニュースを LLM（OpenAI）で解析してスコア化する AI モジュール
- 監視用の SQLite（monitoring.db）によるログ・アラート記録
- コマンドラインでの設定ウィザード・設定検証ツール・レポート生成ツール

設計上の特徴:
- DuckDB を分析用 DB として利用
- SQLite を発注/監視ログ用に利用（paper_trading は専用 DB）
- .env / 環境変数による設定管理（自動ロードありだが無効化可能）
- OpenAI を用いた NLP 処理は外部キー（OPENAI_API_KEY）を必要とする
- プロセスの優先度設定やログローテーション等の運用ユーティリティを備える

---

## 主な機能一覧

- config_setup: 対話式に .env を作成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env / config/*.yaml の簡易検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine を起動（実際の発注処理、paper_trading 時は MockBroker を使用）
- run_monitoring: SystemMonitor をポーリングで実行（リソース監視・データ鮮度等）
- monitoring: RiskMonitor / TradeMonitor / SystemMonitor を束ねる MonitoringEngine（アラート・KillSwitch）
- ai.news_nlp: ニュース記事を LLM でスコアリングし ai_scores に書き込む
- ai.regime_detector: 市場レジーム判定を行い market_regime に記録
- research: ファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析ツール
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約適用
- tools.paper_verification_report: Paper Trading の検証レポート出力ツール

---

## 前提・依存関係

- Python 3.10 以上（| 型注釈 等を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 任意（検証用）:
  - PyYAML（config/*.yaml の中身検証に使用）
- SQLite は標準ライブラリで利用可能

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai
# 設定検証で YAML を読みたい場合:
pip install pyyaml
```

必要に応じて requirements.txt を作成して pip install -r で管理してください。

---

## 環境変数（代表的なもの）

重要な環境変数の一覧（.env に設定する想定）:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアする(1/0)

注意:
- .env の自動読み込みはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- .env の生成は対話式ウィザード（python -m kabusys.config_setup）を利用できます。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を作成
   - まずウィザードで .env を生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL 扱いにしたい場合:
     python -m kabusys.validate_config --strict
     ```
5. データディレクトリを作成（必要に応じて）
   - data/ (SQLite 等)
   - logs/（ログ出力先。logging_setup が自動で作成するが権限が必要）
6. DuckDB / SQLite の初期化は各スクリプト起動時に必要なテーブルを自動作成します（init_monitoring_db 等）。

---

## 使い方（代表的なコマンド）

各スクリプトはパッケージモードで実行できます（パスにプロジェクトルートを含めることを前提）。

- ExecutionEngine（発注エンジン）起動
  - paper_trading モードなら .env の KABUSYS_ENV を `paper_trading` に設定してから実行
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行時の挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - PID ファイルや data/stop_requested.flag を監視して安全に停止

- Monitoring（監視ループ）起動
  ```bash
  # ポーリング間隔を 30 秒にしたい場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は Settings に関わらず本番 sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを永続化します
  - data/stop_requested.flag を置くことで監視ループの停止を指示できます

- 設定ウィザード（.env の作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None) — ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込み
  - これらは OPENAI_API_KEY が必要（引数で渡すことも可能）

---

## 運用上の注意 / 実装上のポイント

- Execution 起動時に data/stop_requested.flag が存在すると起動をスキップします。停止させたい場合は flag 書き込み/削除の運用に注意してください。
- Monitoring は process 停止の検出、データ鮮度チェック、滞留注文・約定異常などを検知してアラートを投げる仕組みがあります（AlertManager 経由）。
- Kill Switch: リスクしきい値（ドローダウン、ポジション上限）を超えた場合、data/kill.flag を書き込んで Execution を停止させる仕組みを持ちます。KILL_FLAG_CLEAR_ON_START に注意。
- Paper Trading の DB は本番と分離されています（settings.paper_sqlite_path）。
- OpenAI 呼び出しはリトライとバリデーションを備えていますが、API キー & 料金管理に注意してください。
- logging_setup は stdout とファイル（logs/<app_name>.log 日次ローテーション）に出力します。ログディレクトリ作成に失敗した場合はコンソールのみになります。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下に実装がまとまっています。主要ファイル/モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py

サブパッケージ:
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照実装あり)
- src/kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/data/ (データパイプライン / stats 等)
- src/kabusys/tools/
  - paper_verification_report.py
- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py

補助:
- config/  — 設定用 YAML ファイル（system_config.yaml 等を想定）
- data/    — SQLite / duckdb / pid / flag ファイルを置くためのデフォルトディレクトリ
- logs/    — ログファイル出力先（デフォルト）

（実際のファイル一覧はプロジェクトルートでツリー表示してください。）

例:
```
src/kabusys/
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  └─ risk_monitor.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ utils/
│  ├─ logging_setup.py
│  └─ process_priority.py
├─ run_execution.py
├─ run_monitoring.py
├─ config.py
└─ config_setup.py
```

---

## よくある運用コマンドまとめ

- .env を作る / 更新する:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に / 追加情報

- config/*.yaml（system_config.yaml 等）はプロジェクトルートの config ディレクトリに置かれる想定です。validate_config は PyYAML が存在すれば YAML のパース検証も行います。
- 本 README はコードベースから抽出した情報に基づき要点をまとめたものです。運用方針（kill.flag の扱い、ログ管理、DB バックアップ等）は組織のルールに合わせて運用してください。

必要であれば、各モジュール（ExecutionEngine の起動手順、RiskManager のパラメータ説明、AI モジュールの利用方法など）をさらに詳細にまとめたドキュメントを作成します。どの部分を深掘りしたいか教えてください。