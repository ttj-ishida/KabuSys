# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システムのコア部分を含むモジュール群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行、監視、AI（ニュースセンチメント／レジーム判定）などを含む設計になっています。

---

## プロジェクト概要

- 設計方針
  - DuckDB を用いた時系列データ分析（prices_daily / raw_financials 等）。
  - SQLite（monitoring DB）で監視ログ・注文ログ・ダッシュボード等を永続化。
  - ExecutionEngine は実際のブローカー（kabuステーション）または Paper Trading 向けの MockBroker を切り替え可能。
  - 監視（MonitoringEngine）は System / Trade / Risk の各モニタを定期実行し、Kill Switch や LINE 通知を行う。
  - AI モジュールは OpenAI（gpt-4o-mini）を利用してニュースをスコアリングし、レジーム判定にも利用する。API 呼び出し失敗時はフェイルセーフで続行する設計。

---

## 主な機能一覧

- execution
  - ExecutionEngine: 実際の発注処理（本番 / ペーパートレード切替）
  - OrderManager / Reconciler / RiskManager: 発注管理とリスク制御

- monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存/データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン検出・ポジション上限検出
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
  - KillSwitch / AlertManager: 停止フラグ・LINE 通知

- portfolio
  - 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索、将来リターン・IC 計算、統計サマリー

- ai
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定

- tools
  - paper_verification_report: ペーパートレード結果の検証レポート生成

- config
  - Settings: 環境変数 / .env 管理（自動ロード機能あり）
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: 起動前チェック（必須環境変数・config YAML・パス確認等）

---

## セットアップ手順（簡易）

1. リポジトリを取得
   - git clone ... （省略）

2. Python 環境（推奨）
   - Python 3.9+ を想定
   - 仮想環境作成: python -m venv .venv && source .venv/bin/activate

3. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai requests
   - YAML の検証を行う場合: pip install PyYAML

   （本リポジトリには requirements.txt が付属していません。上記はコードで参照されている主要ライブラリです。）

4. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（プロジェクトルートに配置）
   - 自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. data ディレクトリの作成（必要なら）
   - mkdir -p data

---

## 必須 / 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV
    - development / paper_trading / live
    - paper_trading では MockBroker を使用し、ペーパートレード用 DB に記録（PAPER_TRADING_SQLITE_PATH）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知に使用）

- 監視ループ関連
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring の場合、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すか（0/1）

- Paper Trading
  - PAPER_FILL_MODE: instant / partial / never / reject

設定ウィザードを利用すると主要項目が対話的に作成できます（.env に保存されます）。

---

## 実行方法（代表コマンド）

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって実挙動が変わる（paper_trading は専用 DB / MockBroker を使用）

- Monitoring（単体ポーリングスクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（秒）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いに

- Paper Trading の検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

- AI の呼び出し（プログラムから）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: API キーは引数または OPENAI_API_KEY 環境変数で指定

---

## 停止 / フラグファイルについて

- stop_requested.flag
  - run_monitoring / run_execution は "data/stop_requested.flag"（プロジェクト内パス）を監視し、存在するとループを終了します。
  - run_execution は起動時に stop フラグが立っていれば起動しません。

- execution.pid
  - run_execution は data/execution.pid を PID ファイルとして利用します。SystemMonitor は PID ファイルを確認してプロセスの存否を判定します。

- kill.flag（Kill Switch）
  - KillSwitch は重大なリスク（ドローダウン超過・ポジション上限超過等）を検出すると data/kill.flag に理由を書き込みます。ExecutionEngine 側はこのフラグを検出して停止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に自動で clear されますが、本番では 0 を推奨します。

---

## 主要な設計・挙動メモ

- process priority
  - 起動時に set_process_priority("high") を呼び出してプロセス優先度を上げようとします（psutil に依存）。権限不足や未対応 OS では警告を出してスキップします。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は存在しないテーブルやカラムを作成・マイグレーションします（冪等）。

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、発注/ログは paper_trading 用 SQLite DB（デフォルト data/paper_trading.db）へ記録され、本番 DB と完全に分離されます。

- LLM（OpenAI）呼び出し
  - news_nlp / regime_detector は gpt-4o-mini を想定。429・タイムアウト・5xx などは指数バックオフでリトライ。失敗時はフェイルセーフ（スコア=0 等）で継続します。
  - レスポンスは JSON モードで期待しますが、パース不良があれば復旧処理を試みます。

---

## ディレクトリ構成（主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動ロード / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — 発注関連（OrderManager 等）（※詳細は別ディレクトリ）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/ (ランタイム / DB やフラグファイルを配置する想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (ペーパートレード用 DB)

---

## よくある運用ワークフロー（例）

1. 仮想環境準備・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を検証
4. duckdb に prices_daily 等のデータを投入（別途データ取り込みスクリプトを実行）
5. 本番起動: systemd / supervisor 等で
   - python -m kabusys.run_execution
   - python -m kabusys.run_monitoring
6. 問題時は monitoring が kill.flag を作成 → ExecutionEngine が停止

---

## 参考・補足

- モジュール単位での呼び出し（ライブラリ利用）
  - ai.score_news, ai.regime_detector.score_regime, research.calc_momentum などは DuckDB コネクションを渡して呼び出せます（単体テストやバッチ処理向け）。

- ロギング
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を使っています。必要に応じて環境変数 LOG_LEVEL を設定してください。

---

もし README をプロジェクトルートに配置する用の具体的な .env の例や systemd のユニットファイル例、依存関係の requirements.txt を作成したい場合は、その例を作成して差し上げます。どの情報を追加しますか？