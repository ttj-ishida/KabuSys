# KabuSys — README

本リポジトリは日本株自動売買システム「KabuSys」のコアロジックをまとめた Python パッケージです。  
この README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

※ 本ドキュメントはソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。  
主な役割は次の通りです。

- 株価データ・財務データからのファクター計算（research）
- ポートフォリオ構築（候補選択・重み付け・株数決定）
- 発注ロジック（Order 管理、ExecutionEngine、Reconciler など）
- 監視（システム状態・注文異常・リスク監視）とアラート（LINE）
- Paper Trading 用の分離された DB と検証レポート生成
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを生成・利用する機能

モジュールは可能な限り純粋関数や DB 抽象化で分離されており、本番/ペーパー（検証）環境を想定した設定が組まれています。

---

## 主な機能一覧

- research/
  - ファクター計算: Momentum・Volatility・Value 等（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- portfolio/
  - 候補選定（スコア順）
  - 等分配・スコア加重配分
  - セクター制約の適用、レジーム乗数
  - 株数決定（単元丸め・リスクベース配分・可用現金に基づくスケーリング）
- execution/
  - OrderManager: 注文状態遷移・重複検知
  - Reconciler: 再起動時の注文/ポジション同期
  - ExecutionEngine（起動スクリプト run_execution.py により運用）
- monitoring/
  - SystemMonitor: CPU/MEM/DISK・プロセス存否・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数監視、dashboard 更新
  - KillSwitch: 条件に応じて停止フラグを書き込み自動停止
  - AlertManager: LINE API を使った一方向プッシュ通知（クールダウンあり）
  - MonitoringEngine / run_monitoring.py: ポーリングループで監視を実行
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- ai/
  - news_nlp: raw_news を OpenAI でセンチメント評価し ai_scores に書き込み
  - regime_detector: MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- tools/
  - paper_verification_report: Paper Trading DB を解析し検証レポートを標準出力に生成

---

## 前提 / 推奨環境

- Python 3.10 以上（型注釈や文字列評価を利用）
- SQLite（標準ライブラリ）
- DuckDB（prices_daily 等の分析用テーブル格納）
- 外部ライブラリ（代表）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (LLM 呼び出し)
- ネットワーク接続（OpenAI を使う場合）

requirements.txt がない場合は以下のように最低限インストールしてください（例）:

pip install duckdb psutil requests streamlit openai

---

## 環境変数（主なもの）

設定は .env, .env.local, OS 環境変数の順に読み込まれます（プロジェクトルートに .git または pyproject.toml があることが前提）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数:

- KABUSYS_ENV: 起動環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading の場合、run_execution は MockBrokerClient を使い DB を data/paper_trading.db に記録（本番 DB と完全分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: "1" を設定すると起動時に kill.flag をクリア

.env 例（抜粋）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
4. 環境変数を設定（.env を作成）
   - .env.example があれば参照して作成（本リポジトリにない場合は上記例を参考に）
5. data ディレクトリの用意（必要に応じて）
   - mkdir -p data
   - 実行スクリプトは自動的に monitoring DB のテーブルを作成します（init_monitoring_db）

備考:
- monitoring DB（SQLite）は init_monitoring_db により必要なテーブルを自動作成・マイグレーションします。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定すると run_execution が paper_trading 用 DB を使います。

---

## 使い方（起動 / 実行例）

基本的にモジュールはパッケージモードで実行できます。

1. 監視ループを起動（SystemMonitor 等をポーリング）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
   - 停止: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します。

2. Execution（発注エンジン）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、データは data/paper_trading.db に記録されます。
   - 停止: data/stop_requested.flag の作成により ExecutionEngine が停止します。
   - 実行時、data/execution.pid に PID を書き込みます（プロセス監視用）。

3. Streamlit 監視ダッシュボード（GUI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、ダッシュボード表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可）
   - レポートは稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を出力します。

5. AI 関連（ニューススコア・レジーム判定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使って、DuckDB 接続と target_date を渡して実行します。
   - 実行には OPENAI_API_KEY が必要です（メソッドは api_key 引数からも指定可能）。
   - 例（Python から）:
     from openai import OpenAI  # ライブラリ提供
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, date(2026, 4, 10), api_key="sk-...")

注記:
- run_monitoring / run_execution は stop フラグ（data/stop_requested.flag）を監視して安全に終了します。
- KillSwitch は監視結果に応じて data/kill.flag を書き込み、Execution 側の停止判定に用います。

---

## 主要スクリプト（エントリポイント）

- src/kabusys/run_monitoring.py
  - SystemMonitor を初期化してポーリングループを回すスクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能
- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading 時は MockBroker を使用）
- src/kabusys/monitoring/streamlit_dashboard.py
  - Streamlit による監視ダッシュボード
- src/kabusys/tools/paper_verification_report.py
  - Paper Trading の検証レポートを生成

---

## ディレクトリ構成（概要）

（src/kabusys をルートとする主要ファイル/フォルダ）

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の管理（.env 自動ロード, Settings クラス）
  - run_monitoring.py — 監視ループ起動
  - run_execution.py — ExecutionEngine 起動
  - data/ (実行時に使用するファイル)
    - monitoring DB（data/monitoring.db）など
    - stop_requested.flag, kill.flag, execution.pid などのフラグ/管理ファイル
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 + MonitoringDB クラス
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定価格異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ生成ユーティリティ
    - alert_manager.py — LINE 通知送信
    - monitoring_engine.py — 各 monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — Order の生成・キャンセル等の外向き API
    - reconciler.py — 起動時の自動復旧 / 帳尻合わせ
    - その他実行系モジュール（Engine, BrokerFactory など — 一部抜粋）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコア化して ai_scores に保存
    - regime_detector.py — Market Regime 判定と DB 書き込み
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意 / トラブルシュート

- DB の初期化は自動で行われますが、DuckDB/SQLite のファイルパスは環境変数で適切に設定してください。
- run_execution を paper_trading で動かすと本番用 DB を触らないように分離されます（PAPER_TRADING_SQLITE_PATH を確認）。
- stop/kill フラグファイル:
  - グレースフルに停止させたい場合は data/stop_requested.flag を作成してください（run_monitoring / run_execution が検知）。
  - KillSwitch は監視条件に基づき data/kill.flag を書き込みます。起動時にこれを自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- OpenAI を利用する機能は API のレート制限やネットワーク障害を考慮しており、リトライ・フォールバック処理を持ちますが、API キーは必須です。
- LINE 通知は channel token / user id が未設定だと送信をスキップします。テスト中はログのみ出力されます。

---

## 開発・拡張メモ

- DuckDB に格納するテーブル（prices_daily, raw_financials, raw_news など）を整備することで research / ai 機能を活用できます。
- portfolio / position_sizing のロジックは将来的に銘柄別 lot_size 等を導入することを想定した TODO が残されています。
- モジュールは純粋関数ベースで設計されている箇所が多く、単体テストを追加しやすくなっています。

---

この README はコードベース（src/kabusys 以下）に基づく概要説明です。  
運用やデプロイ時は各モジュールの詳細実装や外部 API の利用規約（kabuステーション、OpenAI 等）に従って設定・権限管理を行ってください。