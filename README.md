# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはリポジトリ内の主要なモジュールと運用手順（セットアップ・起動・停止方法）を日本語でまとめたものです。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
モジュールは大きく以下に分かれます：

- execution: 発注エンジン・注文管理・リスク管理
- monitoring: システム監視、リスク監視、アラート / Kill Switch
- portfolio: 銘柄選定・配分・ポジションサイズ算出
- research: ファクター計算・特徴量解析
- ai: ニュース NLP（OpenAI）を用いたセンチメント、レジーム判定
- tools: ペーパートレード検証レポートなどユーティリティ
- utils: ロギング設定、プロセス優先度設定など共通ユーティリティ
- config: 環境変数管理・`.env` ウィザード・設定検証

設計方針の例:
- DuckDB / SQLite をデータ層に使い、分析と監視は DB を通じて行う
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して専用 SQLite を使用
- AI（OpenAI）呼び出しはフェイルセーフ（API失敗時はフォールバック）で実装

---

## 主な機能

- ExecutionEngine（発注エンジン）起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、data/paper_trading.db（既定）へ記録
- System / Trade / Risk Monitoring
  - system_status, trade_logs, risk_logs, dashboard 等の永続化
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine を止める）
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ決定
  - セクター上限やレジーム乗数の適用
- 研究用モジュール
  - モメンタム・ボラティリティ・バリューのファクター計算（DuckDB を利用）
  - 将来リターン／IC（Information Coefficient）計算など
- AI モジュール
  - ニュース記事を LLM（OpenAI）でセンチメント評価 → ai_scores テーブルへ書き込み
  - マクロセンチメント + ETF MA200 乖離で市場レジーム判定
- 運用ツール
  - 対話式 .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 共通ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil 利用）

---

## 前提 / 必要環境

- Python 3.9+ を推奨（コードは型ヒント等を使用）
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に利用）
- 実運用では OpenAI API キー（OPENAI_API_KEY）や各種 API トークンが必要

（requirements.txt は本リポジトリには含まれていません。使用環境に合わせて pip install を行ってください。）

---

## 環境設定（.env）

推奨ワークフロー：

1. .env を作成する（ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話式に必要な環境変数を設定し `.env` を生成します

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要な環境変数（抜粋）：
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI を使う機能は必須
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（run_monitoring の仕様）。
- paper_trading は発注系を分離するため専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使います。

---

## セットアップ手順（例）

1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（環境に応じて）
   - pip install duckdb psutil openai PyYAML

3. .env を作成
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK が出ます

5. データディレクトリやログディレクトリを確認（必要なら作成）
   - data/ （DB・PID・flag ファイル格納）
   - logs/ （ログファイル格納）

---

## 使い方（起動 / 停止 / ツール）

起動スクリプト（モジュールとして実行）:

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中は data/execution.pid を使用
    - 監視用 DB のテーブル作成を保証（init_monitoring_db）

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視処理は本番 sqlite_path を使用（KABUSYS_ENV に無関係）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループは検知して終了します

停止 / Kill Switch:
- kill.flag（data/kill.flag）:
  - KillSwitch が条件を満たすとこのファイルを書き込み ExecutionEngine に停止シグナルとして扱います
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では推奨されません）
- stop_requested.flag（data/stop_requested.flag）:
  - run_execution と run_monitoring はこのファイルの存在をチェックし、あればループ／起動を停止/スキップします

その他ツール:
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（または --db オプション）
- AI 関連機能を使うには OPENAI_API_KEY を設定してください（news_nlp / regime_detector）

ログ:
- デフォルトで stdout にログ出力し、日次ローテーションで logs/<app_name>.log に保存します
- LOG_DIR 環境変数でログディレクトリを変更できます

注意点:
- set_process_priority によりプロセス優先度を上げるため psutil が必要です。また権限により優先度変更が失敗することがあります（警告でスキップされます）。
- OpenAI 呼び出しはエラーに強い実装になっていますが、APIキー・料金に注意して運用してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリは `src/kabusys` 配下が実装のルートです。主要ファイルを列挙します（抜粋）。

- src/kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数読み込み・Settings)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (Monitoring 起動スクリプト)

- src/kabusys/execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  （※発注ロジック、ブローカ抽象化など）

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite 用永続化層)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py
  - __init__.py

- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- data/ （運用時に使用）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/ （デフォルト LOG_DIR）

---

## 開発 / 運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を必ず確認してください。validate_config は live 時に注意喚起を行います。
- .env は絶対にリポジトリにコミットしないでください（config_setup も README 内にその注意が出力されます）。
- Monitoring は監視データを本番 sqlite に書き込みます。テスト用に監視 DB を分離したい場合は運用レベルでパスを変更してください。
- OpenAI 呼び出しを行うモジュール（news_nlp, regime_detector）は API の呼び出し回数とリトライ・バックオフを実装していますが、コストとレート制限に注意してください。
- psutil を用いたプロセス優先度 / CPU affinity の変更はプラットフォーム依存・権限依存です。失敗時はログに警告が出ます。

---

必要であれば、README に追加してほしい内容（具体的な環境変数一覧のテンプレート、より詳細な起動手順、データベーススキーマの説明や運用例の runbook 等）を教えてください。必要に応じて追記します。