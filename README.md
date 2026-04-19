# KabuSys

日本株向け自動売買 / 研究基盤ライブラリのリポジトリ（簡易 README、日本語）。

このプロジェクトは取引実行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）などの機能を含むモジュール群で構成されています。各種起動スクリプトはモジュールとして実行可能です。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）の起動・管理
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ペーパートレード（paper_trading）向け分離 DB とモックブローカー
- ポートフォリオ構築（候補選定、配分、ポジションサイジング、セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算など） — DuckDB を想定
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証等）
- レポート生成ツール（Paper Trading の検証レポート）

設計上の注意点：
- 環境変数・.env を用いた設定管理（自動ロード機構あり）
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視は本番 sqlite_path を常に参照（monitoring は環境に依存しない）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動（KABUSYS_ENV に応じてモック/実ブローカーを切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env / config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成
- ai/news_nlp.py: raw_news を OpenAI でセンチメント評価して ai_scores に保存
- ai/regime_detector.py: マクロ + ETF MA200 乖離で市場レジームを判定
- monitoring/*: system / trade / risk の各種モニタ、KillSwitch、アラート連携
- portfolio/*: 候補選定、重み計算、リスク調整、ポジションサイジング
- research/*: ファクター計算、特徴量探索、IC 計算など（DuckDB 接続で動作）
- utils/logging_setup.py: 統一ログ設定（stdout + 日次ローテーション）
- utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール
   - 本リポジトリに requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存例（必要に応じてインストール）:
     - pip install duckdb psutil openai
   - YAML 検証を有効にする場合:
     - pip install pyyaml

4. 初期設定（.env 作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でリポジトリルートに `.env` を作成します（下記に簡易例あり）。
   - 自動ロード: kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データディレクトリ
   - デフォルトで以下ファイル/ディレクトリが想定されます。必要に応じて作成してください（スクリプトが自動作成する場合もあります）。
     - data/ (DB・フラグファイル)
     - logs/ (ログ出力先)

---

## 主要環境変数（よく使うもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション（デフォルト値を示す）:
- KABUSYS_ENV: execution モード
  - 値: development | paper_trading | live
  - default: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/（ログファイル保存先）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、default 0）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject、default "instant"）

（詳細は kabusys.config.Settings のプロパティ参照）

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（実行コマンド）

各スクリプトはモジュールとして実行できます（プロジェクトルートで実行）。

- 対話式設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時に data/stop_requested.flag があれば起動せず終了。
    - PID ファイルを data/execution.pid（Settings.pid_file_path）に作成します。
    - 停止は data/stop_requested.flag の作成により指示可能。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Monitoring は常に本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
    - data/stop_requested.flag が存在するとループを抜けて終了。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で SQLite ファイルパスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究系はライブラリ API として利用
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI を使う場合は OPENAI_API_KEY を設定してください。

停止・Kill Switch:
- KillSwitch は条件（ドローダウン超過・ポジション上限超過など）で data/kill.flag を書き込みます。ExecutionEngine はこれを検出して安全に停止する設計になっています（KillSwitch は冪等にファイルを書きます）。
- 手動でプロセスを停止する場合は data/stop_requested.flag を作成することで run_execution / run_monitoring が検知して終了します。

ログ:
- 共通ユーティリティ setup_logging() により stdout 出力と日次ローテーションログ（logs/<app_name>.log）が設定されます。ログ出力先は LOG_DIR で変更可能。

---

## ディレクトリ構成（主要ファイル・説明）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py — 環境変数・.env の読み込みと Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込み
    - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化 / 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py — (注文関連監視; 実装あり)
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル管理
    - monitoring_engine.py — 各種 monitor を束ねるループ
    - alert_manager.py —（アラート送信管理: LINE 等）※実装箇所参照
  - execution/
    - execution_engine.py — Execution ロジック（Engine）
    - broker_factory.py — ブローカークライアント生成（モック/実ブローカー切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注・管理・調整・リスク管理
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算（ロット丸め / aggregate cap 等）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - data/ (想定: DB・フラグファイルを置く)
    - monitoring.db（SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - kill.flag, stop_requested.flag, execution.pid
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity

---

## 開発・デバッグのヒント

- 設定検証を先に行うのが安全:
  - python -m kabusys.validate_config
- .env は絶対にリポジトリにコミットしない（config_setup.py でも注意書きあり）
- DuckDB 接続を多用するため、大量の価格データを格納する際は DUCKDB_PATH のディスク容量に注意
- OpenAI API 呼び出しを含む機能は API キーと課金が必要です。テスト時は該当関数をモックして回避可能に設計されています（コード内コメント参照）。
- ログレベルを DEBUG に上げると内部の処理状況がより詳細に出力されます（LOG_LEVEL 環境変数）。

---

必要であれば、README に実際のコマンド例・.env.example を追加したり、各コンポーネント（ExecutionEngine / MonitoringEngine / ブローカー実装等）の詳細設計ドキュメントをまとめて展開できます。どの部分を詳述したいか教えてください。