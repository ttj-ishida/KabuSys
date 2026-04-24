# KabuSys

日本株向け自動売買システムのプロジェクトリポジトリ（簡易ドキュメント）

この README はリポジトリ内のスクリプト群・モジュール構成をもとに作成した概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連する以下の機能を持つモジュール群を提供します。

- 発注・Execution エンジン（実際のブローカ API / ペーパートレード分離）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限など）
- リサーチ（ファクター計算、特徴量探査、IC 計算）
- AI 関連（ニュース NLP によるセンチメント、レジーム判定）
- 運用ユーティリティ（設定ウィザード、設定検証、ペーパー検証レポート）
- 永続化（SQLite を使った監視ログ、DuckDB を使った時系列 / 分析データ）

設計上のポイント：
- Paper Trading（KABUSYS_ENV=paper_trading）は発注処理・DB を本番と分離して安全に検証可能。
- .env ベースの設定（独自パーサ実装）を用い、設定ウィザードで初期作成できる。
- ログは stdout と日次ローテーションファイル（logs/<app>.log）に出力。
- OpenAI を用いる AI 部分は API キーが必要。失敗時はフォールバックして安全に継続する設計。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番/ペーパーを切り替え）
- 監視系
  - run_monitoring.py: SystemMonitor をポーリングで実行し監視ログを記録
  - MonitoringEngine: System / Trade / Risk monitor をまとめて実行、Kill Switch 評価、アラート発行
- 設定関連
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の初期検証ツール
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポート出力
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、リスク調整、株数決定（単体関数群）
- リサーチ
  - research/*: ファクター計算（momentum/value/volatility 等）、IC/統計サマリなど
- AI
  - ai/news_nlp.py: ニュース記事をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - ai/regime_detector.py: ETF とマクロニュースを組み合わせて市場レジーム判定
- 永続化
  - monitoring/monitoring_db.py: 監視ログ用 SQLite テーブルの初期化と CRUD ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 主要な依存（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証用に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: requirements.txt は本リポジトリに含まれていないため、プロジェクトに合わせて依存を管理してください。

4. 設定ファイル（.env）作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成

   重要な環境変数（一部）
   - JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
   - KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
   - KABUSYS_ENV            : 実行環境（development | paper_trading | live） デフォルト: development
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
   - OPENAI_API_KEY         : OpenAI API キー（AI 機能を使う場合）
   - LOG_LEVEL              : ログレベル（DEBUG/INFO/...）
   - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（開発時のみ 1 を推奨、live では 0 推奨）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ準備
   - data/ ディレクトリ（DB やフラグファイルを置く場所）が自動で作成されますが、必要に応じて手動で作成してください。
   - logs/ ディレクトリはロギング時に自動作成されます。

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します
    - 起動後、data/execution.pid に PID が記録されます（設定で変更可）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（デフォルト 60 秒）
  - 監視は Settings.sqlite_path を常に使用（コード設計上、環境にかかわらず本番 sqlite_path を参照します）
  - 停止方法: data/stop_requested.flag を作成するとループが検知して終了します

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI / レジーム判定 / ニューススコアリング
  - ai モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とします
  - 直接の CLI エントリは用意されていませんが、モジュール関数（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）をスクリプトやバッチから呼び出せます

---

## ログ／ファイル／フラグについて

- ログ
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - stdout にも同時出力されます
  - ローテーション: 日次、30 世代保持

- データベース
  - DuckDB: デフォルト data/kabusys.duckdb
  - 監視 SQLite: デフォルト data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 使用時）

- Kill / Stop フラグ
  - data/kill.flag : Kill Switch（監視が検出すると ExecutionEngine を停止させるために作成）
    - KillSwitch は条件に基づきこのファイルを書き込み、既存の場合は上書きしない（冪等）
    - ExecutionEngine は起動時に設定によりこのフラグを自動クリアする（KILL_FLAG_CLEAR_ON_START=1 の場合）
  - data/stop_requested.flag : run_* スクリプトの外部停止制御（存在を監視して安全に停止）
  - data/execution.pid : ExecutionEngine の PID（デフォルトパスは Settings.pid_file_path）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の Python パッケージは src/kabusys 以下に格納されています。主要なファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env 自動ロードのロジック
  - config_setup.py          — 対話式 .env 生成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
- src/kabusys/execution/
  - （ExecutionEngine、OrderManager、BrokerFactory などの実装ファイル群）
- src/kabusys/monitoring/
  - monitoring_db.py         — SQLite テーブル初期化 + ラッパー
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
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py
- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py

（実装の詳細は各ファイルの docstring / コメントを参照してください）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）での運用時は .env の設定値（LINE 通知設定や Kill Switch の挙動）を十分に確認してください。validate_config は本番時の追加チェックを行います。
- OpenAI API を用いる部分は API コストとレート制限に注意してください。失敗時はフォールバックやリトライ戦略が実装されていますが、運用方針を検討してください。
- logs/ および data/ ディレクトリのバックアップや権限設定に注意してください（機密情報やトークンは .env に保存されますが、.env は絶対にリポジトリにコミットしないでください）。
- ポートフォリオ・発注ロジック（リスク管理）は研究/検証目的のため、実運用では十分な監査と追加のガード（監査ログ、手動承認など）を組み込んでください。

---

## よくあるコマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの docstring と構成から自動的に要約したものです。各機能の詳細実装や拡張、デプロイ手順はプロジェクトの運用方針に合わせて補完してください。必要であれば、各モジュールの API 仕様やサンプル実行フローの追加ドキュメントを作成します。