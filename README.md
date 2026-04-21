# KabuSys

日本株自動売買システム（軽量版）  
この README はリポジトリの主要スクリプト／モジュール群に基づいて作成した日本語ドキュメントです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数（主要）
- よく使うコマンド
- ディレクトリ構成（概略）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤の骨格を提供する Python プロジェクトです。主な機能は次の通りです：
- 注文実行エンジン（ExecutionEngine）と発注ロジックの土台
- システム監視（SystemMonitor）・取引監視（TradeMonitor）・リスク監視（RiskMonitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI ベースのニュースセンチメント評価および市場レジーム判定（OpenAI API を利用）
- ペーパートレード向け検証レポート生成ツール

設計上の特徴：
- 設定は .env（自動読み込み）と環境変数で管理
- 本番・ペーパートレードを分離（DB 等を切り替え）
- DuckDB（時系列ファクター等）と SQLite（監視・トレードログ）を併用
- ログ管理は統一的に setup_logging を利用（stdout + 日次ローテートファイル）

---

## 機能一覧

- config 管理
  - Settings クラス：環境変数をプロパティとして参照
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

- 実行関連
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により paper_trading では MockBrokerClient を使用）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可能）

- 監視
  - monitoring_db.py：SQLite に監視レコードを永続化（テーブルの初期化 / マイグレーション含む）
  - system_monitor.py：CPU/メモリ/ディスク/プロセスの監視とデータ鮮度チェック
  - risk_monitor.py：ドローダウン・ポジション数監視
  - kill_switch.py：条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - monitoring_engine.py：複数の monitor を束ねるランナー

- ポートフォリオ構築
  - portfolio_builder.py：候補選定・重み計算
  - position_sizing.py：株数・単元丸め・キャッシュスケーリング
  - risk_adjustment.py：セクターキャップ、レジーム乗数

- リサーチ
  - research/factor_research.py：モメンタム、バリュー、ボラティリティ等のファクター計算（DuckDB 利用）
  - research/feature_exploration.py：将来リターン計算、IC 等の統計処理

- AI（OpenAI）
  - ai/news_nlp.py：ニュース記事を LLM（gpt-4o-mini）で評価し ai_scores に書込
  - ai/regime_detector.py：ETF の MA＋マクロニュースで市場レジーム判定

- ツール
  - tools/paper_verification_report.py：ペーパートレード DB を集計して検証レポートを出力

- ユーティリティ
  - utils/logging_setup.py：一貫したロギング設定
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

以下は一般的なセットアップ例です。プロジェクトの依存に関しては適宜 requirements.txt を参照するか、必要なパッケージをインストールしてください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 実行環境に応じて他の依存（例: jquants 用クライアント等）を追加

4. 環境変数（.env）を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考に）
   - 自動ロードはデフォルトで有効（プロジェクトルートに .env があれば読み込まれる）
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳格扱いしたい場合は --strict を付与

6. データディレクトリ作成
   - デフォルトでは data/ と logs/ にファイルが作成されます。必要に応じて権限を確認してください。

注意:
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config の警告が有用です）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を別スレッドで実行。KABUSYS_ENV が `paper_trading` のとき、専用の paper DB を使用します。
  - 停止方法（外部から）：プロジェクトルート/data/stop_requested.flag を作成すると起動ループが検知して停止します。
  - ExecutionEngine 自身は data/execution.pid に PID を書きます（設定は Settings.pid_file_path で変更可能）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書き可能、デフォルト 60 秒）
  - 停止方法：プロジェクトルート/data/stop_requested.flag を作成してループを止めます。
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path（デフォルト data/monitoring.db）を使用します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 引数 --db で DB パスを明示的に指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジームスコア（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - どちらも OPENAI_API_KEY（または引数 api_key）が必須

ログ:
- デフォルトログディレクトリ: logs/
- app_name に応じたファイルが作成される（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout に出ます

---

## 主要な環境変数（抜粋）

必須（実行前にセットする／.env に設定する）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

重要（デフォルトあり）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — Monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能で必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

監視 / Kill Flag
- KILL_FLAG_PATH — Kill Switch が書き込むフラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に Kill Flag を自動クリアするか（"1"=クリア）

自動 .env 読み込み
- プロジェクトルートに .env があれば自動で読み込まれる。無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止 / Kill の仕組み

- stop_requested.flag
  - run_monitoring.py と run_execution.py はそれぞれプロジェクト内の data/stop_requested.flag をポーリングして存在を検知すると優雅に終了します。運用側から強制停止したい場合、このファイルを作成してください。

- kill.flag（Kill Switch）
  - monitoring の各監視結果に基づいて KillSwitch が data/kill.flag を書き込むと、ExecutionEngine はそのファイルを検出して安全に停止します。
  - KillSwitch はドローダウンやポジション上限などの条件でフラグを書き込みます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリの概略です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py      — システム監視
    - risk_monitor.py        — リスク監視（ドローダウン等）
    - trade_monitor.py       — （存在: 取引監視ロジック）
    - monitoring_engine.py   — 各監視をまとめるエンジン
    - kill_switch.py         — Kill Switch

  - execution/               — Execution エンジン / 注文管理 等（ファクトリ等）
    - (OrderManager, ExecutionEngine, BrokerClientFactory, etc.)

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数算出・単元処理・キャップ
    - risk_adjustment.py     — セクター上限・レジーム乗数

  - research/
    - factor_research.py     — ファクター計算（mom/value/volatility）
    - feature_exploration.py — forward returns / IC / 統計

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

data/ と logs/ は実行時に使用される（デフォルトパス）。config/*.yaml がプロジェクトで利用される可能性あり（validate_config で確認）。

---

## 補足・運用上の注意

- データベース接続
  - monitoring（監視）は環境にかかわらず monitoring.db（Settings.sqlite_path）を使用し、本番監視テーブルを参照します。
  - run_execution は KABUSYS_ENV が `paper_trading` の場合に paper_sqlite_path を使用して本番 DB と分離します（ペーパートレードの安全確保）。

- OpenAI 利用
  - news_nlp と regime_detector は OpenAI を利用します。API 呼び出しはリトライ／バックオフ等のロジックを備えているものの、API 制限や料金に注意してください。
  - OPENAI_API_KEY の管理を厳重に行ってください（.env を Git で管理しないこと）。

- ログ
  - ログディレクトリに書き込み権限がないとファイル出力は無効になり、標準出力のみになります。運用時は logs/ の作成とパーミッションを確認してください。

---

README はプロジェクトの現状コードベースに基づいて作成しました。追加で下記のような情報があれば README をより具体化できます：
- requirements.txt（依存パッケージ）や Dockerfile
- 実行時の systemd / supervisor / cron の推奨設定例
- ExecutionEngine, OrderManager, BrokerClient の詳細仕様ドキュメント

必要であれば、それらを元にさらに詳しい導入手順や運用ガイドを作成します。