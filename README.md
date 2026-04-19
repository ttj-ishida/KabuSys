# KabuSys

日本株自動売買システムのコアライブラリ群および起動スクリプト群。  
このリポジトリは、監視（Monitoring）、発注エンジン（Execution）、研究/ファクター計算、ポートフォリオ構築、AI（ニュースセンチメント／レジーム検出）などのモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を提供します。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由での発注管理、リスク制御、注文再突合せ
- 監視（Monitoring）：プロセス稼働状況、システムリソース、データ鮮度、注文ログ等のポーリング監視とアラート
- ポートフォリオ構築：銘柄選定、重み計算、ポジションサイジング、セクター制約
- 研究（Research）：DuckDB を用いたファクター計算、将来リターン、IC 計算、特徴量探索
- AI モジュール：OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジーム判定
- 運用ツール：環境設定ウィザード、設定検証、ペーパートレードの検証レポート等

設計方針の一部：
- DuckDB / SQLite をデータストアに使用（分析用: DuckDB、監視/発注ログ: SQLite）
- Paper Trading（擬似発注）は本番 DB から完全分離
- ルックアヘッドバイアスを避けるため、日付参照は明示的に渡す設計
- OpenAI 呼び出しは失敗時フェイルセーフ設計（スコア 0 やスキップで継続）

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- 発注エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用（環境に依存せず）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ（選定 / 重み / サイジング / セクター制約）
- 研究用モジュール（モメンタム/ボラティリティ/バリュー等のファクター計算）
- AI モジュール
  - kabusys.ai.score_news: ニュースを LLM でスコアリングして ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: マクロ + ETF MA から日次レジーム判定

---

## 前提条件（推奨）

- Python 3.10+（型記法 X | Y を使用しているため）
- pip（パッケージインストール用）

必要な Python パッケージ（主要）:
- duckdb
- psutil
- openai
- PyYAML（任意、config 検証で YAML をパースする場合）
  
インストール例:
pip install duckdb psutil openai PyYAML

（プロジェクトで requirements.txt を用意している場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数 (.env) の作成
   - 対話式ウィザードを使用:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考にしてください）
5. 設定の検証（オプション）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります
6. データディレクトリとログディレクトリの準備（多くは自動作成されます）
   - デフォルト DB: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - ログ: logs/
   - PID/フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

注意:
- init_monitoring_db() が実行時にテーブルを自動作成 / マイグレーションを行います。起動前にファイルを作る必要はありません。

---

## 環境変数（主なもの）

以下は Settings クラス、config_setup に基づく主要な環境変数とデフォルト値の抜粋です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (選択: development / paper_trading / live, デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)
- KILL_FLAG_CLEAR_ON_START (0/1, デフォルト: 0)
- PAPER_FILL_MODE (paper_trading の MockBroker の振る舞い。instant/partial/never/reject)
- OPENAI_API_KEY (AI モジュール使用時に必要)

特記事項:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を秒で上書き（デフォルト 60）
- 監視側（Monitoring）は環境にかかわらず Settings.sqlite_path（本番 sqlite）を使用します
- 発注エンジン（Execution）は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使用

---

## 実行方法（簡易ガイド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid を作成し、data/stop_requested.flag を検出すると停止します
  - Paper Trading の場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更できます（例: export MONITOR_POLL_INTERVAL=30）
  - 停止は data/stop_requested.flag を作成することで行います（多くのスクリプトはこのファイルを監視）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / 研究系はライブラリ関数として利用可能
  - 例: from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - regime_detector は kabusys.ai.regime_detector.score_regime を使用

ログ:
- デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 標準出力も出力されます

停止・Kill スイッチ:
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止指示を行います（KillSwitch の条件は RiskMonitor 等により判定）
- 管理者が手動で停止フラグを作成することでエンジンを停止できます（data/stop_requested.flag）

---

## 開発 / テストメモ

- DuckDB によるクエリはテスト用にメモリ DB を渡せます（duckdb.connect(":memory:") 等）
- OpenAI 呼び出し箇所はテスト時に関数をパッチ（unittest.mock.patch）してモック化することを推奨
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に自動的に .env/.env.local を読み込みます。自動読込を無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定読み込み
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化レイヤ
    - system_monitor.py             — システム/データ鮮度監視
    - trade_monitor.py              — 注文ログ監視（概要）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - monitoring_engine.py          — 各モニタの統合ループ
    - kill_switch.py                — kill.flag 書き込みユーティリティ
    - alert_manager.py              — アラート配信（LINE 等）※実装箇所参照
  - execution/
    - execution_engine.py           — ExecutionEngine 本体（起動/停止制御）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py          — 候補選定 / 等重 / スコア重み
    - position_sizing.py            — 株数決定（lot 単位丸め等）
    - risk_adjustment.py            — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — IC/統計サマリー等
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - data/                            — 実行時に生成されることが多い（DB/FLAG/PID）
    - monitoring.db (SQLITE)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (Paper trading 用 SQLite)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/                            — ログファイル群（logs/execution.log 等）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください（validate_config にて警告を出します）。
- kill_flag（data/kill.flag）を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です（デフォルトは 0）。
- Monitoring は監視用 DB（SQLITE_PATH）を使用します。監視は本番 DB を参照する設計上の想定があるため環境変数の設定に注意してください。
- OpenAI API を用いるモジュールを運用する場合はレート制限・API コストを考慮してください。実装はリトライとフォールバック（スコア 0）を含んでいますが、実運用ではキー管理やバッチ間隔を制御してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（setup_logging の挙動）。

---

必要であれば、README にサンプル .env、起動スクリプトの systemd サービス例、より詳しい API 用ドキュメント（関数シグネチャ毎）などを追加できます。どの追加情報が必要か教えてください。