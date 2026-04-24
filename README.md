# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群のみ）。  
本 README はコードベースの使い方・セットアップ・各機能概観を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした複合モジュール群です。主な役割は次の通りです。

- ExecutionEngine: 発注処理／注文管理／リスク管理（本番／ペーパートレード対応）
- Monitoring: システム稼働・注文状況・リスクを定期監視し、必要時に Kill Switch（停止フラグ）を発行
- Research: ファクター計算・特徴量解析（DuckDB を利用）
- AI: ニュースの NLP スコアリング／市場レジーム判定（OpenAI API を利用）
- Portfolio: 銘柄選定・配分・ポジションサイズ計算（純粋関数群）
- Tools: ペーパートレード検証レポート生成などのユーティリティ

設計方針の一部:
- DB（SQLite / DuckDB）を用いた永続化と分析分離
- 本番とペーパートレードは DB を分離（PAPER_TRADING 用 SQLite）
- 外部 API（OpenAI 等）は明示的な API キー参照で安全に扱う
- 自動ログ／ローテーション、プロセス優先度制御、フェイルセーフ実装

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループ実行（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
- 監視
  - monitoring/ : SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, DB 永続化 (monitoring_db.py)
- 研究・解析
  - research/ : ファクター計算（momentum / volatility / value）、特徴量探索、IC 計算、正規化ユーティリティ
- AI
  - ai/news_nlp.py: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に書込む
  - ai/regime_detector.py: ETF とマクロニュースを使い market_regime を判定
- ポートフォリオ構築
  - portfolio/ : 候補選定、重み計算、セクター制限、ポジションサイズ算出
- ツール
  - tools/paper_verification_report.py: ペーパートレードのヒストリカル検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈の表現により 3.10+ を想定）
- OS によっては psutil によるプロセス優先度変更で権限が必要

1. リポジトリをクローン / ソース取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate (Windows)
3. 必要なライブラリをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 開発/補助:
     - PyYAML（validate_config が config/*.yaml を検証する場合に必要）
   例:
     pip install duckdb psutil openai PyYAML
   （requirements.txt がある場合は pip install -r requirements.txt を利用）

4. 環境変数 / .env の準備
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な可変設定とデフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL: INFO（DEBUG 等も指定可）
     - OPENAI_API_KEY：AI 機能を使う場合に必須
   - .env 作成後:
     python -m kabusys.validate_config で検証（--strict で警告もエラー扱い）

5. データディレクトリ（logs / data 等）の作成は多くのコードで自動作成されますが、権限やマウント先に注意してください。

---

## 使い方（実行例）

基本的な起動方法（仮想環境内で実行）:

- ExecutionEngine を起動（通常モード）
  KABUSYS_ENV を .env で設定し、次を実行:
    python -m kabusys.run_execution

  ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（ポーリング）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使って監視テーブルを更新します
  - 停止は data/stop_requested.flag を作成することで検知

- 設定検証
    python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

- .env を対話式に作成/更新
    python -m kabusys.config_setup

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パス指定可。

- AI 機能（ライブラリ利用例）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  （これらは DuckDB の接続オブジェクトを受け取ります）

---

## 主要ファイル・設定項目（代表的）

- .env（プロジェクトルート）
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - KABUSYS_ENV=development|paper_trading|live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=...（AI を使う場合）

- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - setup_logging() により stdout とファイルに出力

- フラグ / PID:
  - data/stop_requested.flag : 起動中プロセスを止めるための停止フラグ（run_* スクリプトが監視）
  - data/kill.flag : KillSwitch による ExecutionEngine 停止指示（monitoring が書込）
  - data/execution.pid : ExecutionEngine の PID（run_execution が書込）

---

## データベース（監視用 SQLite）テーブル（概要）

monitoring/monitoring_db.py で作成される主なテーブル:

- system_status: cpu/memory/disk/プロセス状態 等の定期ログ
- trade_logs: 発注イベントログ（Created/Sent/Filled 等、latency_ms カラムあり）
- positions: 現在ポジション（code キー）
- risk_logs: リスク関連アラートログ（デデュープ機能有）
- dashboard: ダッシュボード集計（id=1 の1行保持）

init_monitoring_db() は冪等的にテーブルと必要なカラムを作成・マイグレーションします。

---

## ディレクトリ構成

以下はソースツリー（src/kabusys 以下）の概観です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/
    - broker_factory.py      — ブローカークライアント生成（本番 / Mock）
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — スキーマ定義・パイプライン（別モジュール）
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

（実際のリポジトリではさらに細かいファイルやモジュールがあります）

---

## 注意事項 / トラブルシューティング

- 環境変数が未設定だと Settings 内のプロパティで ValueError を投げます。validate_config.py で事前チェックしてください。
- PyYAML が無いと config/*.yaml の内容チェックはスキップされます（警告）。
- psutil による優先度変更は権限が必要な場合があります（特に Linux の負の nice 値）。
- OpenAI API を使用するモジュールは OPENAI_API_KEY を必要とします。API コールの失敗時はフェイルセーフ（デフォルト値・スキップ）で動作する設計ですが、API キーが無いと処理は実行されません。
- run_execution / run_monitoring は stop_requested.flag を監視します。手動停止・自動制御時のフラグ運用に注意してください。
- ペーパートレード（paper_trading）は発注処理と本番 DB を完全に分離するための仕組みが用意されています。テスト時は KABUSYS_ENV=paper_trading を使ってください。

---

README は以上です。必要であれば次の点について追加で書きます:
- 各モジュールの API（関数シグネチャ）一覧
- よくある運用手順（デプロイ・再起動・ログローテーション）
- 既知の制限・TODO リスト

どの情報を追記しましょうか？