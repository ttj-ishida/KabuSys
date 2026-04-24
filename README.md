# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト群）。  
このリポジトリはトレード実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動/ツール）
- 環境変数（主要項目）
- 動作フロー・運用上の注意
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な役割は以下のとおりです。

- ExecutionEngine（発注処理）: ブローカークライアント経由で注文を管理・実行
- Monitoring（監視）: システム状態、注文状況、リスク（ドローダウン・ポジション上限等）の定期チェックとアラート／Kill Switch 制御
- Portfolio（銘柄選定・配分）: シグナルから候補選定、重み付け、ポジションサイズ計算
- Research（ファクター計算）: duckdb を利用したファクター計算・将来リターン/IC 計算
- AI（ニュース NLP / レジーム判定）: OpenAI を利用したニュースセンチメントのスコア化やレジーム判定
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度制御 など

設計方針として、外部 API への依存は必要最小限に抑え、DB（SQLite / DuckDB）や環境変数で設定を管理するようになっています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- Execution 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 環境にかかわらず監視用 DB には本番 sqlite_path を使用
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）
- MonitoringEngine：System / Trade / Risk モニタを束ねポーリング、Kill Switch 判定・アラート送信
- MonitoringDB：SQLite による system_status, trade_logs, positions, risk_logs, dashboard の永続化
- Portfolio：候補選定・重み計算・ポジションサイズ計算（単元株丸め、aggregate cap 等）
- Research：momentum/volatility/value 等のファクター計算、forward returns、IC 計算など（duckdb ベース）
- AI：ニュースセンチメント（OpenAI）を用いた ai_scores 書き込み、レジーム判定（ma200 + macro sentiment）
- tools/paper_verification_report：ペーパートレードの検証レポート生成

---

## セットアップ手順

1. Python 3.9+（ソースに合わせて環境を用意）
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 開発補助:
     - PyYAML（config 検証時に YAML パースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
4. .env の作成
   - 対話型ウィザードを使用:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. ディレクトリ準備（デフォルトで使用されるデータ / ログ ディレクトリ）
   - data/ （SQLite ファイル、pid/flag など）
   - logs/ （ログ出力）
   これらは起動時に自動作成される処理もありますが、権限等の問題がある場合は事前に作成してください。

注意: OpenAI を使う機能を動かすには OPENAI_API_KEY を環境変数に設定してください。

---

## 使い方

基本的なエントリポイントと用途：

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine（取引実行）
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時に PID ファイル (data/execution.pid 等) を扱います
    - 停止は data/stop_requested.flag を作成することで行えます（監視側と統合）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し本番 DB と分離
- Monitoring（監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（例: MONITOR_POLL_INTERVAL=30）
  - ログや監視情報は sqlite_path（Settings.sqlite_path、デフォルト data/monitoring.db）へ保存
  - 実行中にプロセス優先度を high に設定し、SystemMonitor / TradeMonitor / RiskMonitor を定期実行
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照）

例（環境変数を指定して起動）:
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- KABUSYS_ENV=paper_trading python -m kabusys.run_execution

停止フラグ
- data/stop_requested.flag を作成すると run_execution / run_monitoring のループは停止を検知して終了します。
- Kill Switch（監視が検出したリスクによる自動停止）は data/kill.flag を書き込む仕組みです（KillSwitch）。

ログ設定
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を呼び出してログを設定します。
- デフォルトは logs/ ディレクトリ、日次ローテーション、30日分保持。
- LOG_LEVEL, LOG_DIR 環境変数でカスタマイズ可。

---

## 主要な環境変数（抜粋）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

主要（任意・デフォルトあり）
- KABUSYS_ENV — execution モード: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI関連機能で必要）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

kill / stop 関連
- KILL_FLAG_PATH — kill flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 実行開始時に kill.flag を自動クリアするか（"1" で有効；本番では 0 推奨）

---

## 動作フロー・運用上の注意

- 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限がないと警告が出ますが継続します。
- Monitoring は明示的に監視用 DB を初期化（init_monitoring_db）します。古い DB に対しては必要なマイグレーション（カラム追加）を行います。
- ExecutionEngine は KABUSYS_ENV によって本番 DB かペーパートレード専用 DB を選択します。ペーパートレードは本番 DB と完全分離する設計です。
- AI 系（news_nlp, regime_detector）は OpenAI API を使います。API 呼び出しはリトライ・バックオフやフォールバックロジックを含み、API 失敗時は安全側の既定値で継続するよう設計されています（例: macro_sentiment=0.0）。
- Kill Switch：RiskMonitor がドローダウンやポジション上限を検出すると kill.flag を書き込み、ExecutionEngine 側がそれを検知して停止します。
- 停止方法：data/stop_requested.flag にファイルを作成すると起動中の run_execution/run_monitoring が順次停止します。
- DB およびファイルのパスは Settings 経由で取得。Settings は .env（または環境変数）を自動ロードする仕組みがあります（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数/設定管理
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ（代表）
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）処理
  - regime_detector.py — レジーム判定（ma200 + macro sentiment）
- monitoring/
  - monitoring_db.py — SQLite 操作（テーブル作成 / 永続化）
  - monitoring_engine.py — 複数 Monitor のポーリング制御
  - system_monitor.py — システム状態 / データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション数監視
  - kill_switch.py — kill.flag 書き込み / 管理
  - alert_manager.py (参照) — アラート送信管理（LINE 等）
  - trade_monitor.py (参照) — 注文周りの監視ロジック（滞留注文・約定異常等）
- portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数計算・aggregate cap 等
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定

データ・ログ（実行環境）
- data/ — SQLite / pid / flag 等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/ — ログファイル（例: logs/execution.log, logs/monitoring.log）

---

## 参考: よくある操作例

- .env を対話で作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 注意事項 / 運用上の留意点

- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な損失につながる可能性があります。validate_config の警告を必ず確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py もその旨を出力します）。
- OpenAI の利用には API コストがかかります。news_nlp/regime_detector を定期的に運用する場合はコスト管理が必要です。
- psutil を使った優先度設定や CPU affinity は OS 権限に依存します。権限不足時は警告が出ますが処理は続行します。
- DuckDB / SQLite のファイルパスは Settings で制御します。パスの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、権限等に依存します。

---

README は以上です。必要であれば「導入ガイド（詳細セットアップ・systemd / Supervisor の設定例）」「各モジュールの API リファレンス」「運用手順（デプロイ、バックアップ、監査ログ）」など追加ドキュメントを作成します。どの追加情報が欲しいか教えてください。