# KabuSys

日本株向け自動売買システム（ライブラリ + 実行スクリプト群）

この README はリポジトリ内のコードベースに基づく概要・セットアップ・利用手順・ディレクトリ構成をまとめたものです。

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えたシステムです。

- 発注エンジン（ExecutionEngine） — 実際のブローカー / ペーパートレーディングの切替対応
- 監視（Monitoring） — システム状態、データ鮮度、注文・リスクの監視とアラート / Kill Switch
- ポートフォリオ構築ロジック（選定・重み付け・株数決定） — 純粋関数群で実装
- リサーチ / ファクター計算（DuckDB を用いた時系列集計）
- AI 補助モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ツール（Paper Trading の検証レポート生成 等）
- 設定管理 CLI（.env ウィザード & 検証ツール）

設計のポイント:
- 本番用 DB（monitoring）とペーパートレード用 DB は分離（KABUSYS_ENV により切替）
- DuckDB を分析用に使用（prices_daily / raw_financials 等のテーブル参照）
- 実行中のログは標準出力と日次ローテーションのログファイルに出力

## 主な機能一覧

- Execution
  - 実際のブローカークライアントと Mock クライアントを環境で切替
  - リスク管理（max position, utilization, circuit breaker 等）
  - 発注管理・注文履歴保存
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度の監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン監視
  - KillSwitch: 条件に応じて data/kill.flag を吐いて ExecutionEngine を停止
  - MonitoringEngine: 各モニタの定期実行・アラート送信
- Portfolio
  - 候補選定、等金額やスコア重みの算出、ポジションサイジング（単元丸め）
  - セクター制限・レジーム乗数等のリスク調整
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - news_nlp: ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores に格納
  - regime_detector: ETF とマクロニュースを使った市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力
- 設定ユーティリティ
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env および config/*.yaml の検証 CLI

## 前提 / 推奨環境

- Python 3.10 以上（型注釈に `|` 演算子を使用）
- OS: Linux / macOS / Windows（psutil による優先度設定は OS に依存）
- 必要な主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に任意）
- SQLite は標準ライブラリに含まれます

インストール例:
- 仮想環境の作成（例）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（requirements.txt があればそれを利用）
  - pip install duckdb psutil openai pyyaml

※ 実運用では各パッケージのバージョン固定を推奨します。

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境を作成・有効化し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

3. .env の作成（対話式）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を環境変数または .env に設定

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトで以下のパスを使用
     - DuckDB: data/kabusys.duckdb
     - monitoring SQLite: data/monitoring.db
     - paper trading SQLite: data/paper_trading.db
     - logs ディレクトリ（ログファイル用）
   - 必要に応じて .env の DU CKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

## 使い方（実行例）

- 監視ループを起動（デフォルトポーリング間隔 60 秒）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に production（本番）用の sqlite_path を使います（環境に依らず）

- Execution エンジン起動
  - 本番/開発/ペーパーは KABUSYS_ENV で切替
  - 本番（例）: KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と完全分離）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も EXIT(1) 扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を明示: --db PATH もしくは環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI モジュール（ニュース / レジーム）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
  - 例: kabusys.ai.score_news(conn, date(2026,4,1), api_key="...")

- 停止・Kill Switch
  - 実行ループの外部停止用フラグ:
    - data/stop_requested.flag: run_monitoring / run_execution のループを止める（スクリプトが検知）
    - data/kill.flag: ExecutionEngine に対する停止シグナル（KillSwitch が書き込む）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリア（注意: 本番では推奨しない）

## よく使う環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DU CKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログ出力レベル
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）

## ログと PID

- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30 日保持）と標準出力
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます
- PID ファイル:
  - ExecutionEngine は data/execution.pid（デフォルト）に PID を書きます（設定で変更可）

## 注意点 / 運用上の備考

- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知トークンなどを適切に設定してください。
- validate_config の live 用チェックでは Kill Switch の自動クリア設定や通知先の未設定を警告します。
- AI（OpenAI）依存機能は API 料金・レート制限に注意してください。失敗時はフェイルセーフでスコアを 0 にフォールバックする箇所がありますが、運用設計に合わせて監視してください。
- データの鮮度チェック（SystemMonitor）は DuckDB の prices_daily を参照します。リサーチ・AI は DuckDB に依存するため、事前にデータ投入が必要です。
- paper_trading モードは本番 DB と分離されるため、実験や検証に安全に利用できます。

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 以下の主な構成:

- __init__.py
- config.py — 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — 市場レジーム判定（LLM + ETF 指標）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — 注文滞留・約定監視（ファイル内に存在）
  - monitoring_engine.py — 複数モニタの統合ポーリング
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — （アラート送信機能、ファイル参照）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

データ・ログ・PID 用ディレクトリ（デフォルト）
- data/
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper trading 用)
  - kabusys.duckdb (DuckDB)
  - execution.pid, stop_requested.flag, kill.flag など
- logs/
  - execution.log, monitoring.log, ...（app_name ごと）

## 開発・テストに関する補足

- DuckDB と SQLite のスキーマはコード内で参照しているため、ローカルでのテスト用にサンプルデータやマイグレーションスクリプトを準備することを推奨します。
- news_nlp と regime_detector は外部 API（OpenAI）に依存します。ユニットテストでは _call_openai_api をモックする設計になっています（関数ラップされているため差し替えが容易）。
- config._find_project_root は .git や pyproject.toml を起点にプロジェクトルートを自動検出するため、パッケージ配布後も動作する設計です。

---

必要に応じて README をプロジェクトの実際の要件（requirements.txt の内容、CI 手順、運用 runbook）に合わせて追記してください。質問や特定の導入手順（Docker 化、systemd サービス化 など）への対応が必要であれば教えてください。