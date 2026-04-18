# KabuSys

日本株向け自動売買システムの Python モノリポジトリ（ライブラリ + 実行スクリプト群）。

本 README ではリポジトリの概要、主要機能、セットアップ手順、実行方法、およびディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は、株価データの解析・ファクター算出、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）および AI 補助（ニュースセンチメント・レジーム判定）を備えた日本株自動売買支援システムです。DuckDB / SQLite をデータ格納に用い、kabuステーション API や J-Quants など外部サービスと連携して運用できます。

設計方針の一部：
- 分析・研究ロジック（DuckDB）と発注ロジック（ブローカークライアント）を分離
- Paper Trading 環境を本番 DB と完全に分離（data/paper_trading.db）
- モジュールは副作用を避け、テスト容易性を重視（純粋関数を多用）
- OpenAI を用いた NLP はフェイルセーフ（API失敗時に安全なフォールバック）

---

## 機能一覧（主な機能）

- 実行制御
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視）

- 環境設定 / 検証
  - config_setup.py: 対話式で `.env` を生成・更新するウィザード
  - validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI

- 監視（Monitoring）
  - system_monitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度検査
  - trade_monitor: 注文の滞留・約定異常等のチェック（trade_logs を参照）
  - risk_monitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - monitoring_engine: モニタ群を束ねてポーリング／アラート発火
  - kill_switch: 条件により `data/kill.flag` を書き込み実行エンジンを停止

- ポートフォリオ構築（Portfolio）
  - 銘柄候補選定、等重/スコア重み計算、ポジションサイズ（リスクベース等）
  - セクターキャップ / レジーム乗数の適用

- 研究 / ファクター計算（Research）
  - momentum, volatility, value 等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI（OpenAI 経由）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成（稼働率・成功率・レイテンシ等）

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config: .env 自動ロード・設定管理

---

## 要件（推奨）

- Python 3.10+
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証を有効にしたい場合）
- その他: SQLite は標準で利用可能

（プロジェクトには requirements.txt がないため、環境に応じて必要なパッケージを pip でインストールしてください）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <this-repo>
   cd <this-repo>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil openai pyyaml

4. データディレクトリ / ログディレクトリを作成（通常はコードが自動作成）
   mkdir -p data logs

5. .env を作成（推奨）
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいは .env を手動で作成（以下は主要項目の例）
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

6. 設定検証（任意）
   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱いになります
   python -m kabusys.validate_config --strict

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、Execution は MockBrokerClient を利用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。

- DB 関連
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB デフォルト data/paper_trading.db

- ログ / その他
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI を使う機能で使用（news_nlp, regime_detector）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止用）

---

## 実行方法（代表的なコマンド）

- ExecutionEngine を起動（本番または paper_trading によって挙動が変わる）
  python -m kabusys.run_execution

  動作:
  - 起動時にプロセス優先度を high に設定し、SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用します。
  - data/stop_requested.flag が存在すると起動をスキップまたは実行中に停止します。
  - プロセス PID を data/execution.pid に書きます（設定により変更可）。

- Monitoring を起動（定期ポーリング）
  python -m kabusys.run_monitoring

  動作:
  - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず monitoring は本番 DB を見る設計）。
  - data/stop_requested.flag を検出するとループを終了します。

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## 停止・Kill Switch の扱い

- 実行の停止要求（両スクリプト共通）
  - 管理用フラグファイル:
    - data/stop_requested.flag: run_monitoring / run_execution の外部停止要求に使用（存在すれば起動を停止、実行中は監視ループで検出して停止）
    - data/kill.flag: KillSwitch による致命的停止シグナル（ExecutionEngine に対する停止トリガー）
  - KillSwitch は RiskMonitor の判定（ドローダウン超過など）により `data/kill.flag` を書き込みます（既存の場合は上書きしない）。

- 起動時クリーンアップ
  - 設定により KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番環境では推奨しません）。

---

## ライブラリ / API の簡単な使い方

- ポートフォリオ構築
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- 研究用ファクター計算（DuckDB 接続が必要）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

- AI スコアリング（プログラムから呼ぶ）
  from kabusys.ai import score_news
  # DuckDB 接続と target_date, OPENAI_API_KEY の用意が必要
  count = score_news(duckdb_conn, target_date, api_key="sk-...")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="sk-...")

- 監視 DB の操作（MonitoringDB）
  from kabusys.monitoring.monitoring_db import MonitoringDB
  mdb = MonitoringDB(sqlite_conn)
  mdb.log_trade_event(...)

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しています。
- 出力: stdout（StreamHandler） + 日次ローテートファイル（logs/<app_name>.log、30日保持）
- LOG_DIR 環境変数でログ出力先を変更可能

---

## ディレクトリ構成（主なファイル / モジュール）

- src/kabusys/
  - __init__.py
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する前提のモジュール)
  - execution/               (Execution 関連コンポーネント群: Engine, OrderManager 等)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                    (データファイル置き場: monitoring.db, paper_trading.db, kabusys.duckdb 等)
  - logs/                    (デフォルトのログ出力先)

（注）一部モジュールはここに示した以外にも存在します。上は主要なものの抜粋です。

---

## 開発・運用上の注意点

- monitoring モジュールは監視用の SQLite を使用しますが、run_monitoring は KABUSYS_ENV に関係なく「本番 sqlite_path」を参照する設計になっています。運用時は設定に注意してください。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI を利用する機能は API コストやレート制限の影響を受けます。環境変数 OPENAI_API_KEY の管理に注意してください。
- Kill Switch / stop flag はファイルベースで実装されています。自動化スクリプトから停止する際はファイルの存在・削除を適切に扱ってください。
- 設定検証（validate_config.py）およびウィザード（config_setup.py）を初期導入時に必ず実行し、必須環境変数が設定されていることを確認してください。

---

もし README に追加したい具体的な情報（例: systemd ユニットファイル例、Dockerfile、CI 設定、詳細な API ドキュメント等）があれば教えてください。必要に応じて追記します。