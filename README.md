# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注処理・監視・研究ツール・AIを用いたニュース評価などを含む自動売買基盤の一部です。各モジュールはできるだけ副作用を抑えて設計されており、Paper Trading（検証用）と Live（本番）を切り替えて運用できます。

---

## プロジェクト概要

主な目的：
- データ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine による発注管理（本番／ペーパートレード対応）
- 監視（プロセス生存、データ鮮度、滞留注文、異常約定、ドローダウン検知）と Kill Switch
- OpenAI を利用したニュース NLP（銘柄センチメント）・レジーム判定
- Paper Trading 用検証レポート生成ツール

設計ポイント：
- 設定は環境変数（.env/.env.local）で管理。Settings クラスで集約。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
- DuckDB を分析用、SQLite を監視・発注ログ用に使用。
- API 呼び出し（OpenAI 等）は失敗時にフェイルセーフを取る実装。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV による paper/live 切替）
- 監視系
  - run_monitoring.py: SystemMonitor のポーリング実行
  - MonitoringEngine: System/Trade/Risk の総合ポーリングとアラート連携
  - KillSwitch: flag ファイルによる Execution 停止トリガー
- モニタリング永続化
  - monitoring_db: SQLite に監視ログ、trade_logs、risk_logs、dashboard を保存
- リスク管理
  - RiskMonitor: ドローダウン／ポジション数監視、警告ログ記録
  - TradeMonitor: 滞留注文・約定異常検出
- ポートフォリオ構築
  - portfolio: 候補選定、等金額/スコア重み、リスク調整、ポジションサイズ計算
- リサーチ
  - research: ファクター計算（モメンタム/ボラティリティ/バリュー）・将来リターン・IC 計算
- AI（OpenAI）
  - news_nlp: raw_news をまとめて LLM で銘柄スコアリング → ai_scores へ書込
  - regime_detector: ETF の MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - utils/process_priority: プロセス優先度設定（Windows/Linux 抽象化）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック（必須環境変数・config/*.yaml 等）
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成

---

## セットアップ手順

前提
- Python 3.9+（typing/機能要件に応じて適宜）
- OS により psutil のインストールで権限設定が必要な場合あり

推奨手順（例）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 主要依存例:
     - duckdb
     - psutil
     - openai (AI 機能利用時)
     - PyYAML (validate_config で YAML 検証を有効にする場合)
4. 環境変数設定
   - 対話式で作る: python -m kabusys.config_setup
   - もしくは .env ファイルをプロジェクトルートに作成（.env.example を参考）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - 主要な設定例（デフォルトがあるものは省略可能）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
     - LOG_LEVEL
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

ファイル・ディレクトリに対する注意
- data/ ディレクトリは実行時に自動作成されますが、パーミッション等を確認してください。
- kill.flag / stop_requested.flag / execution.pid などの flag/pid 管理を理解してから運用してください。

---

## 使い方（主要コマンド）

基本的にモジュールはモジュール実行（-m）で起動します。

1. .env を作る（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - 振る舞い:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite に書き込む（本番 DB と完全分離）。
     - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）
     - 停止: data/stop_requested.flag を作成するとエンジン起動中に検出して停止します。

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 振る舞い:
     - SystemMonitor.check_once を定期実行（デフォルト 60 秒）
     - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
     - 停止: プロジェクトルート/data/stop_requested.flag を作成すると停止
     - 監視は常に（環境にかかわらず）本番 sqlite_path に対して monitoring DB を初期化／接続します

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db /path/to/paper_trading.db
     - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可

6. AI 機能
   - ニューススコアリング: kabusys.ai.score_news を呼ぶ（スクリプト/ジョブ化して使用）
   - レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ
   - いずれも OPENAI_API_KEY が必要（引数 api_key で明示指定も可能）

停止 / Kill Switch
- KillSwitch は監視結果によって data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時に kill_flag の有無や clear-on-start 設定を参照）。
- kill.flag の自動クリアフラグ: KILL_FLAG_CLEAR_ON_START（1 にすると起動時に自動クリア；本番では 0 推奨）

ロギング
- LOG_LEVEL によりログ出力レベルを制御（Settings.log_level）。各スクリプトは basicConfig(level=INFO) で起動します。

---

## 主要設定項目（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject
- LOG_LEVEL — INFO 等
- OPENAI_API_KEY — AI 機能使用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発用）

.env はプロジェクトルートに置き、決して VCS にコミットしないでください。

---

## 停止 / フラグファイルについて

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がポーリングループで確認する停止フラグ。存在するとループを抜けて終了します。
- data/kill.flag
  - KillSwitch が書き込む。ExecutionEngine 側で起動時やループ中に検出して停止処理を行う想定。
- data/execution.pid
  - ExecutionEngine がプロセス PID を書き込む。SystemMonitor は PID ファイルを監視してプロセス生存チェックを行う。

---

## ディレクトリ構成

下記は src/kabusys 以下の主要ファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 起動前チェック CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースの LLM スコアリング
    - regime_detector.py           — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化・永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py             — （アラート送信ロジックはここに収まる）
  - execution/                     — 発注エンジン関連（OrderManager 等；今回省略ファイル多数）
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（プロジェクトルート）
- .env, .env.local (任意)
- data/                          — デフォルト DB / flag / pid を置く場所
  - kabusys.duckdb (default path)
  - monitoring.db
  - paper_trading.db
  - stop_requested.flag
  - kill.flag
  - execution.pid

---

## 開発上の注意 / 運用メモ

- Paper Trading と本番 DB を明確に分離しています。KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使います。運用時に誤って本番 DB を上書きしないよう注意してください。
- OpenAI API 呼び出しはレート制限やネットワークエラーを考慮したリトライ機構がありますが、API キーやコスト管理は運用者で行ってください。
- monitoring_db.init_monitoring_db は冪等にテーブルを作成し、簡単なマイグレーション（カラム追加）も行います。
- process priority / cpu affinity の設定は OS と権限に依存します。psutil のエラーは警告でスキップされる実装です。
- 大量データ処理は DuckDB を想定。データ取り込みパイプラインは kabusys.data.pipeline 等（今回の抜粋には含まれていません）を参照してください。
- 本 README はコードの一部に基づいています。実際の運用では repository のドキュメント（config/*.yaml、運用手順書）や付随するスクリプトを参照してください。

---

必要であれば、README に含めるサンプル .env テンプレートや、各スクリプトの実行例（systemd ユニット、supervisor、docker-compose 例）も作成します。どれを優先して欲しいか教えてください。