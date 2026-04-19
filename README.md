# KabuSys

日本株向け自動売買／リサーチ基盤の軽量実装。  
このリポジトリはトレードの実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI を利用したセンチメント評価）などのモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つコンポーネント群を提供します。

- ExecutionEngine：発注／注文管理（paper_trading モードではモックブローカーを使用）
- Monitoring：システム状態・注文・リスク監視、Kill Switch による自動停止
- Portfolio：候補選定・重み付け・ポジションサイズ計算
- Research：DuckDB 上で動くファクター計算・特徴量解析
- AI モジュール：OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度制御、Paper Trading 検証レポート等

設計方針の例：
- 設定は .env（自動読み込み）または環境変数で管理
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- 監視・記録は SQLite（monitoring.db）、分析は DuckDB（kabusys.duckdb）
- ロギングは stdout と日次ローテートファイルの両方に出力

---

## 主な機能一覧

- env/.env 管理ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）:
  - KABUSYS_ENV に応じて paper_trading（モック）/live（本番）を切替
  - 停止フラグ（data/stop_requested.flag）により安全停止
- Monitoring 起動スクリプト（kabusys.run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - KillSwitch 評価／アラート連携
  - 環境変数 MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブルの管理
- Portfolio 構成関数: 候補選定、等重／スコア加重、リスクアジャストメント、ポジションサイズ計算
- Research（DuckDB）: momentum / volatility / value ファクター、将来リターン計算、IC（Information Coefficient）等
- AI:
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news） — OpenAI API 使用
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime） — ETF MA とマクロニュースを合成
- ツール:
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

---

## 必要環境・依存パッケージ

推奨 Python バージョン: 3.9+（ソースは型注釈等を使用）

主な依存ライブラリ（最小限、プロジェクトにより追加で必要）:
- duckdb
- psutil
- openai (AI モジュールを使う場合)
- PyYAML（設定検証で config/*.yaml をパースする場合に任意）
- sqlite3（標準ライブラリ）

インストール例（仮想環境推奨）:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

※ requirements.txt は本リポジトリに含まれていないため、必要に応じてプロジェクト向けに作成してください。

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定（.env を作ることを推奨）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example がある場合は参考）

5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. データディレクトリ確認 / 作成
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - ログディレクトリ: logs/（setup_logging が自動作成を試みます）

---

## 主要な環境変数（代表）

（デフォルトや説明を併記）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject、デフォルト: instant)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)
- LOG_DIR (ログ出力先フォルダ、デフォルト: logs/)
- OPENAI_API_KEY (AI モジュールを使う場合必須)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔（秒）、デフォルト 60)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_CLEAR_ON_START (0 or 1) — 起動時に kill.flag を自動クリアするか（テスト用。production は 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

※ .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出できる場合に実行されます。

---

## 実行方法（主なコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag を作成すると安全停止処理を実行

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings に基づいて本番 sqlite_path（monitoring DB）へ接続（environment に関係なく production sqlite_path を使用）
    - SystemMonitor と MonitoringDB を使って定期的に状態を記録
    - MONITOR_POLL_INTERVAL でポーリング間隔を調整

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI モジュール（プログラムとして呼び出す）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクトと target_date を受け取り、内部で OpenAI API を呼ぶため OPENAI_API_KEY が必要（引数で上書き可能）

---

## 停止・Kill Switch の仕組み

- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件を満たすと data/kill.flag を書き込みます。このファイルが存在すると ExecutionEngine は停止する設計です。
- 停止フラグ（監視/実行の即時停止用）:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検知して停止します（運用者が手動で停止したい場合など）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（本番では通常 0 を推奨）。

---

## ロギング

- ログ出力は kabusys.utils.logging_setup.setup_logging() によって統一されます。
- 仕様:
  - コンソール出力（stdout）
  - 日次ローテーションファイル出力（logs/<app_name>.log、30 日分保持）
  - LOG_LEVEL / LOG_DIR 環境変数で制御
- 例:
  - 実行エンジンのログ: logs/execution.log
  - 監視のログ: logs/monitoring.log

---

## データベースとスキーマ

- DuckDB（分析用）: data/kabusys.duckdb（settings.duckdb_path）
- SQLite（監視ログ）: data/monitoring.db（settings.sqlite_path）
- Paper Trading 用 SQLite（paper_trading モード）: data/paper_trading.db（settings.paper_sqlite_path）
- monitoring_db.init_monitoring_db(conn) により必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成します。既存 DB に対するマイグレーションも一部実装されています（例: latency_ms カラムなど）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 + MonitoringDB クラス
    - system_monitor.py      — システム / データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （発注ログ監視等; 実装参照）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （アラート送信の統合: 実装参照）
  - execution/               — 発注エンジン関連（OrderManager, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・単元処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — OpenAI を使ったニュースセンチメント評価
    - regime_detector.py     — MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（細かなファイルはリポジトリを参照してください）

---

## 開発上の注意・運用メモ

- 本番運用時は KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を推奨
- OpenAI 呼び出し部は外部 API に依存するため rate-limit やエラーに対するリトライ実装がされていますが、APIキー管理とコストに注意してください
- .env は絶対に Git にコミットしないこと（config_setup のヘッダにも注意書きあり）
- DuckDB / SQLite ファイルは相対パスで指定できますが、運用環境では絶対パスを推奨
- process priority の設定は psutil を使用します。権限が足りない場合は警告が出てスキップされます

---

必要があれば、README にさらに以下を追加できます：
- API（関数）別の詳細な使用例（コードスニペット）
- CI / テスト実行手順
- サンプル .env.example の生成内容（config/*.yaml のテンプレート）