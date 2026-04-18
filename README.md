# KabuSys

日本株向け自動売買システム（KabuSys）のソースコードです。  
このリポジトリには、発注実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は次の主要機能を持つ自動売買フレームワークです。

- 発注実行（実口座 / ペーパートレードを切替可能）
- 実行中プロセスの監視（CPU/メモリ/ディスク・データ鮮度・プロセス生存）
- リスク監視（ドローダウン、ポジション上限など）と Kill Switch（フラグファイルで停止指示）
- 注文ログ・監視ログの永続化（SQLite）
- 分析用の DuckDB データレイク（ファクター計算・リサーチ）
- ニュースの LLM（OpenAI）によるセンチメント評価・市場レジーム判定
- ペーパートレード検証レポート生成ツール

主要な起動スクリプト・ユーティリティを通じて、ローカル開発・ペーパートレード・本番運用の切替が可能です。

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し paper_trading DB（data/paper_trading.db）へ書き込む。
- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs / dashboard を更新。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- monitoring/...
  - MonitoringDB（SQLite）層、RiskMonitor、TradeMonitor、KillSwitch、MonitoringEngine、アラート管理等。
- portfolio/
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップやレジーム乗数の計算（純粋関数群）。
- research/
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、特徴量探索、IC 計算など（DuckDB を利用）。
- ai/
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとにセンチメントを生成、ai_scores へ書き込み。
  - regime_detector: ETF MA とマクロ記事の LLM センチメントを合成して日次レジーム判定を行う。
- tools/
  - paper_verification_report: ペーパートレード DB に対する検証レポート生成（稼働率・注文成功率・レイテンシ等）。

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing の | 演算子、from __future__ import annotations を使用）
- sqlite3 は標準ライブラリ、DuckDB/psutil/openai などは別途インストール

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合、少なくとも以下を用意）
   - pip install duckdb psutil openai
   - （ツール的に YAML 検証を行う場合）pip install pyyaml

4. 初期設定（.env）
   - 対話式ウィザードで .env を作成 / 更新:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY=<your-key>
   - データベース/ログパス等は .env で上書き可能（デフォルトは data/ と logs/）

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて `--strict` を付けて警告もエラー扱いにできます。

注意: .env は決して Git にコミットしないでください。

---

## 使い方

各主要ユーティリティ / スクリプトの実行例を示します。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - export KABUSYS_ENV=development|paper_trading|live
  - python -m kabusys.run_execution

  補足:
  - paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録され、本番 DB とは分離されます。
  - 起動中に data/stop_requested.flag が作成されると安全に停止します。
  - 実行時に data/execution.pid が使用されます。

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒）
    - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

  補足:
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用してログを保持します。
  - 停止は data/stop_requested.flag を作成することで次のポーリングで検出され終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - SQLite パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定してから、リポジトリ内の呼び出し用 API を利用
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

ログ:
- デフォルトログディレクトリは logs/
- LOG_LEVEL / LOG_DIR は .env で上書き可能
- 日次ローテーション（30日分保持）

停止フラグ / Kill Switch:
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止指示を出します（存在確認 / 冪等処理あり）。
- Execution 側、Monitoring 側は stop_requested.flag / execution.pid を用いて状態管理します。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート通知用（任意）
- MONITOR_POLL_INTERVAL — run_monitoring.py のポーリング間隔（秒）

詳細は `kabusys.config.Settings` を参照してください（コード内にコメントと検証ロジックあり）。

---

## ディレクトリ構成 (主要ファイル)

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
    - news_nlp.py             — ニュースセンチメントスコア (OpenAI)
    - regime_detector.py      — 市場レジーム判定 (OpenAI + ETF MA)
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 / 永続化 API
    - system_monitor.py
    - trade_monitor.py        — （注文監視ロジック: ファイル内に実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

data/ および logs/ ディレクトリは実行時に自動作成されることを想定しています（権限が必要）。

---

## 開発・運用上の注意

- .env は絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定や Kill Switch 設定を慎重に確認してください（validate_config.py に警告ロジックあり）。
- OpenAI を利用する機能（news_nlp, regime_detector）は API コストとレート制限に注意してください。429 や 5xx はリトライ実装がありますが、トラフィック設計が重要です。
- プロセス優先度設定（utils.process_priority）を用いて実行プロセスの優先度を上げていますが、OS の権限や環境によっては設定に失敗することがあります（警告ログのみ）。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパー検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい情報（デプロイ手順、Dockerfile、CI 設定、詳細なアーキテクチャ図、API スペックなど）があれば教えてください。必要に応じて追記・整形します。