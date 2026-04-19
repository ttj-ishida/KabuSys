# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（KabuSys）のリポジトリ内 README。  
この README はコードベース（src/kabusys 以下）を基に作成しています。

注意: 本リポジトリには発注機能が含まれており、本番環境（KABUSYS_ENV=live）で起動すると実際に発注が行われます。実行前に必ず設定を確認してください。

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるモジュール群を提供します。主な役割は以下です。

- データパイプライン / DuckDB ベースのファクター計算（research）
- ポートフォリオ構築・リスク調整・ポジションサイズ決定（portfolio）
- 発注エンジン、注文管理、リスク管理（execution）
- システム監視・アラート・Kill Switch（monitoring）
- ニュースの NLP スコアリング・市場レジーム判定（AI モジュール）
- ペーパートレード用の検証ツール（tools）
- 環境設定ウィザード・設定検証 CLI（config_setup / validate_config）
- ロギング・プロセス優先度ユーティリティなどのユーティリティ群（utils）

設計方針の一部:
- DuckDB を分析に利用、SQLite を監視・取引ログ用に利用
- 本番データ（live）とペーパートレード（paper_trading）は DB を分離
- LLM（OpenAI）連携はフェイルセーフ設計（失敗時は安全側の値で継続）

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
- 取引監視（滞留注文・約定異常の検出）
- リスク監視（ドローダウン検出、保有銘柄上限監視）
- Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止）
- ExecutionEngine（ブローカークライアントを用いた注文実行。paper_trading モードは Mock）
- Paper Trading 用検証レポート生成ツール
- ニュースの LLM（OpenAI）による銘柄センチメント評価（ai.news_nlp）
- マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
- ファクター計算 / 特徴量探索（research）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）

## セットアップ手順

前提:
- Python 3.9 以上（推奨 3.10+）
- OS により psutil の一部機能は権限を要する場合があります

1. リポジトリをチェックアウト（既にある前提）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   例:
   pip install duckdb psutil openai
   - 追加（YAML ファイル検証が必要な場合）: pip install PyYAML
   - 実行スクリプトに合わせて他パッケージが必要な場合があります（requirements.txt を用意している場合はそちらを使用してください）。
4. .env を作成する
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     -（OpenAI を使う場合）OPENAI_API_KEY
   - 主な環境変数（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト 0）

5. 設定検証（起動前推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit 1

6. ログ出力先:
   - デフォルト: logs/<app_name>.log（日次ローテート、30日分保存）
   - コンソールは stdout に出力されます

## 使い方（主要スクリプト）

ここでは開発 / テスト向けの代表的な起動方法を示します。

- 環境（例: ペーパートレード）を指定して .env を作成/編集
  - python -m kabusys.config_setup
  - 必要な環境変数を記入したら python -m kabusys.validate_config で検証

- ExecutionEngine を起動（通常はデーモン運用）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中の停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で停止指示されます
  - 実行時に使用される PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可能:
    MONITOR_POLL_INTERVAL=30  # 秒（デフォルト 60 秒）
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず）
  - 停止は data/stop_requested.flag を作成することでループを抜けます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    --db /path/to/paper_trading.db
    または環境変数 PAPER_TRADING_SQLITE_PATH で指定

- AI 周り（ニューススコアリング・レジーム判定）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定
  - ニューススコアリング（プログラム呼び出し例）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
  - CLI ラッパーは提供していないため、スクリプトやジョブから呼び出してください

- 設定クリア/Kill Switch 操作
  - Kill Switch のフラグ: data/kill.flag
    - KillSwitch.clear() により削除されます（Settings.KILL_FLAG_CLEAR_ON_START=1 により起動時自動クリアも可）
  - 強制停止要求: data/stop_requested.flag（run_monitoring/run_execution 側の停止フラグ）

## 重要な環境変数まとめ

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: 発注はモック、専用 SQLite に記録
  - live: 実際に発注（注意）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔、秒。デフォルト 60）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag 自動クリア: 0/1。production では 0 推奨）

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・ディレクトリ）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定読み込みロジック
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - __init__.py
      - logging_setup.py      — 共通ロギング初期化
      - process_priority.py   — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py      — SQLite のテーブル初期化・永続化層
      - system_monitor.py     — システム監視（CPU/メモリ/ディスク・データ鮮度）
      - trade_monitor.py      — 取引監視（ファイルでは省略）
      - risk_monitor.py       — ドローダウン・ポジション上限監視
      - monitoring_engine.py  — 各種モニタ束ねてポーリング
      - kill_switch.py        — kill.flag 操作ユーティリティ
      - alert_manager.py      — アラート通知管理（ファイルでは省略）
    - execution/
      - execution_engine.py   — ExecutionEngine（ファイルでは省略）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み付け
      - position_sizing.py     — 発注株数計算
      - risk_adjustment.py     — セクター制限・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py    — ファクター計算（momentum/value/volatility）
      - feature_exploration.py— 将来リターン/IC/サマリー
      - __init__.py
    - ai/
      - news_nlp.py           — ニュース NLP スコアリング（OpenAI 呼び出し）
      - regime_detector.py    — 市場レジーム判定（MA + LLM）
      - __init__.py
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
      - __init__.py
    - data/                    — 実行時に想定される配置（DB・フラグ・PID 等）
      - monitoring.db (default)
      - kabusys.duckdb (default)
      - paper_trading.db (default for paper_trading)
      - kill.flag
      - stop_requested.flag
      - execution.pid

※ 実際のリポジトリではさらにファイルが存在します。上は主要ファイルの抜粋です。

## 運用上の注意（安全上のガイドライン）

- 本番で起動する前に必ず validate_config で設定を確認する（特に KABUSYS_ENV=live）。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にしないでください（誤って Kill Switch をクリアしてしまうリスク）。
- OpenAI API の呼び出しは料金が発生します。AI 機能を常時有効にする前にポリシーと課金設定を確認してください。
- psutil によるプロセス優先度設定や CPU affinity は OS 権限が必要な場合があります。実行ユーザーの権限を確認してください。
- データベースファイル（data/*.db）はバックアップを検討してください。特に monitoring.db のログは運用上重要です。
- run_execution は実際の注文を発行しうるため、CI/CD や自動テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD やモックを利用して副作用を避けてください。

## よく使うコマンド（まとめ）

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（スクリプト内呼び出し）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring とソースコードを参照してください。必要であれば README に含める実行例や運用手順をさらに追記します。