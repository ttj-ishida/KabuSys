# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築、発注実行、監視、研究（ファクター計算）、AI を用いたニュース評価などの機能を含みます。

以下はこのリポジトリに含まれる主要な機能、セットアップ、起動方法、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを持つ自動売買システムです。

- ExecutionEngine（発注処理、リスク管理、オーダーマネージャ）
- Monitoring（システム・発注・リスク監視、Kill Switch）
- Portfolio（候補選定、重み計算、ポジションサイズ決定、セクター制約）
- Research（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定、DB 初期化）
- CLI ツール類（環境設定ウィザード、設定検証、Paper Trading 検証レポート など）

設計上のポイント:
- 環境変数／.env ベースの設定管理
- DuckDB／SQLite を利用した分析・監視用データ永続化
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントやレジーム判定（任意）
- Paper Trading（KABUSYS_ENV=paper_trading）用に本番 DB と分離した挙動

---

## 主な機能一覧

- 環境セットアップウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し DB を分離
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムメトリクス、データ鮮度、プロセス監視、監視ログ保持
  - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の変更
- MonitoringEngine（複数モニタを束ねてアラート・Kill Switch を評価）
- RiskMonitor（ドローダウン監視、ポジション数監視）
- KillSwitch（kill.flag による ExecutionEngine 強制停止）
- Portfolio モジュール（候補選定、重み付け、ポジション決定、セクター制約）
- Research（ファクター計算：momentum/value/volatility、forward returns、IC）
- AI（ニュース NLP による銘柄スコアリング、レジーム判定）
- ツール: Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.10 以上推奨（型ヒントで | を使用）
- Git 等でリポジトリをチェックアウト済み

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

2. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil openai
   - OpenAI を使わない場合は openai は不要
   - 設定検証で YAML を検査したい場合は PyYAML を追加: pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. .env を作成
   - 対話式に作成する: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプト（run_monitoring/run_execution）を起動すると必要なテーブル（監視用）は自動で作成されます。
   - DuckDB、SQLite のパスは .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH で指定可能（デフォルトは data/ 以下）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）

重要／よく使う（デフォルト値を示す）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 SQLite パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite。デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（INFO 等）。デフォルト: INFO
- OPENAI_API_KEY — OpenAI API を使う場合に設定
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視・停止関連

注意:
- .env は Git にコミットしないでください（secret 情報を含むため）。
- config_setup により .env の雛形を対話的に作成できます。

---

## 使い方（よく使うコマンド）

- 環境ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も FAIL）： python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  実行中に停止したい場合はプロジェクトルートの data/stop_requested.flag を作成するとループが安全に終了します（run_monitoring/run_execution はこのフラグを監視します）。

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - Paper trading mode にするには .env で KABUSYS_ENV=paper_trading を設定
    - Paper trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（サンプル、OpenAI API キーが必要）
  - Python から直接呼び出す例:
    - python - <<'PY'
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      print(score_news(conn, date(2026,4,1), api_key="sk-..."))
      conn.close()
      PY`
  - 上記は duckdb 上に raw_news/news_symbols/ai_scores 等のテーブルが存在することが前提です。

ログ:
- ログはデフォルトで logs/ に日次ローテーションで保存されます（logs/<app_name>.log）。LOG_DIR 環境変数で変更可能。

停止・強制停止:
- Monitoring 側からの強制停止は KillSwitch が data/kill.flag に理由を書き込みます（ExecutionEngine は起動中に kill.flag を検出して停止します）。
- 実行プロセスを安全に止めたい場合は data/stop_requested.flag を作成します（run_monitoring/run_execution が検出して正常終了します）。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（ma200 + マクロニュース）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化 / CRUD
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注関連の監視、未抜粋ファイルあり）
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — （通知管理、未抜粋ファイルあり）
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py — BrokerClient（実ブローカ / Mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（lot サイズ・aggregate cap 等）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum, value, volatility 等のファクター計算
    - feature_exploration.py — forward returns, IC, summary 等
  - monitoring/, portfolio/, research/ は主に純粋関数群または DB 接続を受け取る形で設計
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/ や logs/ 等のランタイムファイルはプロジェクトルートで管理（例: data/monitoring.db, data/paper_trading.db, logs/）

---

## 注意事項 / 運用メモ

- 本番（KABUSYS_ENV=live）に切り替える際は設定（LINE 通知、kill flag の扱い、DB パス等）を十分確認してください。validate_config は本番向けガードチェックがあります。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を必要とし、呼び出し回数や料金に注意してください。API の失敗はフェイルセーフ的に扱われる実装になっていますが、運用ポリシーに合わせて制御してください。
- run_execution は paper_trading モードであれば本番 DB と分離します。実際の発注を伴う live モードでは十分なテストと運用監視を行ってください。
- プロセス優先度・CPU affinity の設定は psutil に依存します。権限や OS によって設定できない場合があります（警告を出してスキップされます）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml のある場所）を基準に行われます。テストで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## さらに調査したい箇所

この README の作成はコードベースの主要な公開 API・スクリプトに基づいています。細かな実装・追加設定（例: alert_manager の通知先設定、execution_engine の詳細な EngineConfig、BrokerClient 実装など）は各モジュールの docstring / ソースコードを参照してください。

---

必要であれば、README に以下を追加できます:
- 実際の .env のサンプル（.env.example 形式）
- systemd / supervisor / docker-compose 用の起動例
- CI / テスト実行手順
- よくあるトラブルシューティング（DB マイグレーション、権限問題、OpenAI エラー対応）

追加希望があれば指示ください。