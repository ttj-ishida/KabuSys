# KabuSys

日本株向け自動売買システムのライブラリ／ツール群。  
このリポジトリは、発注エンジン・監視・ポートフォリオ構築・リサーチ・AI ベースのニュース解析など、運用に必要なモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するコンポーネント群です。主な責務は次のとおりです。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文を管理・実行
- Monitoring（監視）: システム安定性、注文滞留、ドローダウン等の監視とアラート、Kill Switch（停止判定）
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター上限制御
- Research: DuckDB を使ったファクター計算、将来リターン・IC 計算、統計要約
- AI（OpenAI）: ニュースのセンチメント解析、マクロセンチメントとETF MA を使った市場レジーム判定
- ツール: ペーパートレード検証レポート生成、環境設定ウィザード、設定検証 CLI など

設計上の特徴:
- DB は DuckDB（時系列・分析）と SQLite（監視・小規模永続）を併用
- Paper Trading と本番は DB を分離して運用可能
- .env 自動読み込み（プロジェクトルート基準）・対話式セットアップあり
- OpenAI 呼び出しはリトライとレスポンス検証を備え、フェイルセーフ処理を行う

---

## 主な機能一覧

- 環境設定
  - 対話式ウィザードで `.env` を生成: `python -m kabusys.config_setup`
  - 起動前の設定検証: `python -m kabusys.validate_config [--strict]`
- 実行・監視
  - ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、paper_trading 用 SQLite に記録
  - SystemMonitor ポーリングループ: `python -m kabusys.run_monitoring`
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（秒、デフォルト 60）
  - MonitoringEngine: 各モニター（System/Trade/Risk）を束ねてアラート評価、KillSwitch を実行
- ポートフォリオ構築
  - 候補選定、等重／スコア加重、リスクベースな株数計算、セクター制約、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB に対する純関数）
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計サマリー
- AI（OpenAI）統合
  - ニュースを銘柄別に集約して LLM に投げ、銘柄ごとのセンチメントを `ai_scores` に書き込み
  - マクロニュース + ETF MA200 乖離で市場レジーム（bull/neutral/bear）を判定して `market_regime` に書き込み
- ツール
  - ペーパートレード検証レポート生成: `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化（例: venv / pipenv / poetry）

2. 必要なパッケージをインストール
   - 必須（プロダクションで想定）:
     - duckdb
     - psutil
     - openai
   - 開発 / 便利ツール:
     - PyYAML（設定検証時に config/*.yaml をパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクト設定
   - プロジェクトルートに `.env` を用意（自動ロードを利用）。
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザード実行後、`python -m kabusys.validate_config` で検証してください。

4. ディレクトリと DB の初期化
   - 多くの起動スクリプトは起動時に必要な SQLite テーブルを自動作成します（冪等）。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

5. 環境変数（主なもの）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境:
     - KABUSYS_ENV = development | paper_trading | live
   - DB パス / ログ:
     - DUCKDB_PATH (default data/kabusys.duckdb)
     - SQLITE_PATH (default data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
   - OpenAI:
     - OPENAI_API_KEY（AI モジュールを使う場合）
   - Monitoring:
     - MONITOR_POLL_INTERVAL（秒、監視ループ）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）
   - そのほか: LINE チャンネルや PAPER_FILL_MODE（paper_trading の fill 動作）など  
   - 詳細は `kabusys.config.Settings` の各プロパティを参照してください。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使い `data/paper_trading.db` に記録します。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動されません。
    - エンジンはバックグラウンドスレッドで動作し、`data/execution.pid` に PID が書かれます。

- SystemMonitor（簡易 / 単体）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可能（デフォルト 60）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュールのプログラム的利用
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...)
  - from kabusys.ai.regime_detector import score_regime

- 監視・停止制御
  - Execution を止めたい場合はプロジェクトの `data/stop_requested.flag` を作成すると、`run_execution` / `run_monitoring` のループが検知して停止します。
  - Kill Switch は `data/kill.flag` を書くことで ExecutionEngine 停止をトリガーします（KillSwitch が監視判定により書き込みます）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数 / .env の読み込みと検証
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - 起動前に設定や config/*.yaml を検証する CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 分離対応）
  - run_monitoring.py
    - SystemMonitor ポーリングスクリプト
  - utils/
    - process_priority.py : プロセス優先度・CPU affinity 設定
  - execution/ (発注関連コンポーネント)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
  - monitoring/
    - monitoring_db.py : SQLite テーブル初期化・永続化処理
    - system_monitor.py : システム状態・データ鮮度監視
    - trade_monitor.py : 注文滞留・約定異常監視
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag 書込ロジック
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - alert_manager.py : （アラート送信管理 — 実装箇所参照）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み付け
    - position_sizing.py : 株数計算・投下資金スケーリング
    - risk_adjustment.py : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py : Momentum/Volatility/Value 計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py : ニュースセンチメント解析（OpenAI）
    - regime_detector.py : ETF MA + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート生成
  - data/ (実行時に利用するファイル群を想定)
    - stop_requested.flag
    - kill.flag
    - execution.pid
    - *.db

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では `.env` の中身（認証情報）を十分に管理し、`.env` を Git にコミットしないでください（ウィザードにも警告あり）。
- Kill Switch・PID ファイルの扱いに注意してください。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です。
- OpenAI を利用する機能は API キーが必要です。API の課金やレート制限に注意してください。
- Paper Trading は本番 DB と分離されますが、設定ミスにより本番 DB を指し示さないか確認してください。
- DuckDB / SQLite のバックアップや定期的なメンテナンスを検討してください。

---

## 開発・拡張ポイント（参考）

- ファクター／ポートフォリオロジックは純粋関数として設計されており、単体テストが容易です。
- OpenAI 呼び出しは再試行やレスポンス検証を含んでいます。テストでは API 呼び出し箇所をモックして検証してください（モジュール内に差し替えポイントがあります）。
- 将来的に銘柄別の lot_size（単元株）を導入するための TODO コメントがあります。

---

必要であれば、この README をベースに具体的な起動例、`.env.example`、必要な pip requirements.txt のテンプレートなども作成できます。どの情報を追加しますか？