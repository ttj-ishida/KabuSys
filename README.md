# KabuSys

日本株自動売買システムの部分実装（ライブラリ / ツール群）。  
このリポジトリには、環境設定ウィザード、設定検証、監視ループ、実行エンジン起動スクリプト、ペーパートレード検証レポート、AI / リサーチ / ポートフォリオ構築等のユーティリティ群が含まれます。

概要・機能・設定・使い方・ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連する以下の機能を提供するモジュール群です（実際のブローカー接続やフル実装は別途）:

- 環境変数ベースの設定管理（.env 読み込み・ウィザード）
- 起動前設定検証 CLI
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）
- 監視（Monitoring）ループ：システム状態・注文・リスク監視、Kill Switch
- ペーパートレード用検証レポート生成
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 汎用ユーティリティ（ログ設定、プロセス優先度設定 等）

---

## 主な機能一覧

- config_setup: 対話式ウィザードで .env を生成/更新（python -m kabusys.config_setup）
- validate_config: .env / config/*.yaml の存在や基本整合性を検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading を切り替え）
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用
- run_monitoring: SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- monitoring モジュール: system/trade/risk モニタ、KillSwitch、アラート発行連携
- tools/paper_verification_report: ペーパートレード結果の検証レポート生成
- portfolio モジュール: 候補選定・重み計算・ポジションサイズ計算・リスク調整
- research モジュール: ファクター計算（momentum/value/volatility）・IC / サマリー計算
- ai モジュール: news_nlp（OpenAI を使ったニュースセンチメント）、regime_detector（市場レジーム判定）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. Python 仮想環境の作成（推奨）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール（最低限）
   - duckdb, psutil, openai（必要に応じて PyYAML）
   - 例:
     - pip install duckdb psutil openai
     - 任意で YAML 検証を使う場合: pip install PyYAML

   ※ requirements.txt はこのリポジトリに含まれていないため、環境に応じて必要パッケージを追加してください。

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で作成（.env.example を参考にしてください）

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリ等の作成（通常はスクリプトが自動作成しますが、権限エラーが出る場合は手動で作成）
   - デフォルトデータパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

注意:
- OpenAI API を使う機能（ai.news_nlp / ai.regime_detector）は `OPENAI_API_KEY` 環境変数が必要です。
- 実行スクリプトは `psutil` を使ってプロセス優先度を設定します。権限により設定が失敗することがありますが、警告で処理は継続します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: default "data/kabusys.duckdb"
- SQLITE_PATH: default "data/monitoring.db"
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の DB（default "data/paper_trading.db"）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（"instant"|"partial"|"never"|"reject"）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0"/"1"）

---

## 使い方（主要コマンド）

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切り替え
  - 例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 例（本番）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 動作:
    - paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
    - ストップは data/stop_requested.flag を作成することで可能
    - run_execution は data/execution.pid に PID を書きます

- Monitoring (監視) 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を指定:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 動作:
    - システム状態・データ鮮度・注文・リスク監視を定期実行し、SQLite にログを保存
    - kill.flag を書き込む KillSwitch が動作し得る（ExecutionEngine に停止シグナル）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数で DB 指定:
    - PAPER_TRADING_SQLITE_PATH=/path/to/db.sqlite python -m kabusys.tools.paper_verification_report

- AI / レジーム判定（例）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続と日付、API キーを使って呼び出します（CLI ラッパーはありませんが、モジュール関数を用いて実行可能）。
  - 例（スクリプト内呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

ログ:
- ログ出力先は logs/<app_name>.log（デフォルト）と stdout。
- 日次ローテーション・30日分保持。

停止 / Kill:
- 実行中の Engine を強制停止するには `data/kill.flag` を書き込む（KillSwitch 経由の停止）。kill.flag の自動クリアは設定により変更可能（KILL_FLAG_CLEAR_ON_START）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — （注文周りの監視; コードベースではインポート先あり）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — Monitor をまとめる実行ループ
    - alert_manager.py —（アラート送信管理; 実装参照）
  - execution/
    - execution_engine.py — （実行エンジン本体; インターフェース）
    - broker_factory.py — ブローカークライアント生成（paper vs live 切替）
    - order_repository.py / order_manager.py / reconciler.py / risk_manager.py — 注文管理周り
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（lot 単位丸め・制限）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / value / volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — OpenAI を使ったニュースのセンチメント（ai_scores への書き込み）
    - regime_detector.py — ETF MA + マクロニュースに基づく市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（注）上記はこのコードベースの主要ファイルのみを抜粋しています。詳細は各モジュールの docstring を参照してください。

---

## 実運用上の注意 / トラブルシュート

- .env を絶対に VCS にコミットしないでください（config_setup でも注意書きあり）。
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に変更しようとします。権限やプラットフォームにより失敗することがあり、その場合は警告ログが出ますが処理は継続します。
- OpenAI を使う機能は API キーを必要とします（環境変数 OPENAI_API_KEY）。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は自動作成されますが、権限問題で失敗することがあるため事前に作成しておくと安全です。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更できます。1 未満や不正値はデフォルト 60 秒にフォールバックします。
- ペーパートレード時は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- validate_config が出す警告 / エラーを無視すると本番で重大な事故につながる可能性があります。特に KABUSYS_ENV=live のときは警告を慎重に確認してください。

---

## 参考: よく使うコマンドまとめ

- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution エンジン起動（paper_trading 例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または PAPER_TRADING_SQLITE_PATH=/path/to/db python -m kabusys.tools.paper_verification_report

---

README は以上です。各モジュールに詳細な docstring が含まれているため、実装や API の詳細は該当ファイル（src/kabusys/...）を参照してください。必要であれば各コマンドの具体的な起動例や .env のテンプレートを追記します。どの部分を詳しく追加しますか？