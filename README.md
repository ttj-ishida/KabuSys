# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買 / 研究 / 監視コンポーネント群をまとめた Python コードベースです。本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

なお、本リポジトリは複数のモジュール（ExecutionEngine、Monitoring、AI/NLP、Portfolio Construction、Research utilities など）から構成されています。各モジュールは概ね純粋関数または副作用を限定した小さなクラスに分割されており、DuckDB / SQLite をデータ層として利用します。

---

## プロジェクト概要

- 目的: 日本株の自動売買パイプライン（シグナル生成 → 発注 → リコンシリエーション）と、運転中の健全性監視・アラート、研究用ファクター計算、ニュース NLP（OpenAI）を統合する。
- 設計方針:
  - DB（SQLite / DuckDB）を用いた永続化と分析。
  - Paper Trading 環境と Live 環境を分離（Paper 用の DB を用意）。
  - 監視は独立プロセスとして実行し、監視結果に応じて Execution の停止指示（kill flag）を発行可能。
  - AI 呼び出しは OpenAI（gpt-4o-mini）を利用（APIキー必須）。失敗時はフェイルセーフにより継続可能な設計。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文作成・管理・リスク制御
  - Reconciler による再起動後の自動復旧（ブローカーと照合）
  - BrokerFactory による本番/モッククライアント切り替え（KABUSYS_ENV）

- Monitoring / Alerting
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/PID チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：閾値超過時に停止フラグ（data/kill.flag）を書き込み
  - AlertManager：LINE Messaging API を使った通知（任意）

- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算
  - ポートフォリオ候補選定、重み算出、ポジションサイズ決定、セクターキャップ、レジーム乗数

- AI
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄別 ai_score を ai_scores テーブルへ格納
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM 解析を組み合わせて市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - Streamlit ダッシュボード: 監視データの可視化

---

## セットアップ手順（開発）

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 代表的な依存: duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください。）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD に依存しない探索）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数 (少なくとも実行に必要なもの)
   - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（Settings.jquants_refresh_token）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（Settings.kabu_api_password）
   - OPENAI_API_KEY — AI 機能を利用する場合（任意。news_nlp / regime_detector で使用）

   その他の主要設定（デフォルト値を利用可能）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 参照（デフォルトは data 以下）

5. データディレクトリ作成（実行前）
   - mkdir -p data

---

## 使い方（主要コマンド）

- 監視プロセス起動（monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（monitoring DB）を使用。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を利用します。
  - 停止方法:
    - プロジェクトルートの data/stop_requested.flag を作成するとループは終了します（run_monitoring, run_execution 共通の停止フラグ）。
    - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止シグナルとして利用します（監視 → kill.flag を生成）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - BrokerClient は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離されます。
  - stop の仕組み:
    - 起動時に data/stop_requested.flag が既に存在すれば起動しません。
    - 途中で data/stop_requested.flag が作られると engine.stop() が呼ばれて安全に停止します。
  - 実行中の PID は data/execution.pid（デフォルト）に書かれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to   YYYY-MM-DD （終了日）
    - --db PATH （SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可能）
  - レポートには稼働率、注文成功率、送信率、レイテンシ（P95）等が含まれ、PASS/FAIL 判定を表示します。

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで DB を開きます。MonitoringEngine を先に起動してデータを蓄積してください。

- AI 機能
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）。
  - news_nlp.score_news() と regime_detector.score_regime() は DuckDB 接続と日付を受け取り、ai_scores / market_regime に書き込みます。
  - API 呼び出しはリトライロジックとレスポンス検証を備えています。失敗時は安全にフォールバック（例: macro_sentiment=0.0）します。

---

## 主要環境変数（Settings 参照）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (AlertManager を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の MockBrokerClient の動作を制御）

.env ファイルの自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします（OS 環境変数より低優先）。
- .env.local は .env の上書き（override）として読み込まれます。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 注意点 / 運用メモ

- Paper Trading と Live は DB を分離して運用してください（Settings.is_paper 判定で paper_sqlite_path を使用）。
- Monitoring は Settings.sqlite_path（監視 DB）を使う設計で、KABUSYS_ENV に依存せず監視 DB を参照します。
- プロセス優先度設定（set_process_priority）は psutil を用いて OS に依存した操作を行います。権限が不足すると警告が出てスキップされます。
- kill.flag / stop_requested.flag:
  - kill.flag は KillSwitch（監視が条件を満たしたとき）により生成される停止指示。Execution 側の停止条件と組み合わせて使われます。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution が自分自身の停止を検知するための汎用フラグ。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等で、既存テーブルにカラムがなければ ALTER TABLE による追加を行います。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py                      — ニュース NLP / OpenAI スコアリング
    - regime_detector.py               — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py                 — SQLite 監視ログ層（テーブル定義・CRUD）
    - system_monitor.py                — システム状態・データ鮮度チェック
    - trade_monitor.py                 — 注文滞留・約定異常チェック
    - risk_monitor.py                  — ドローダウン・ポジション上限チェック
    - kill_switch.py                    — kill.flag の書き込み / 管理
    - alert_manager.py                 — LINE 通知ラッパー
    - monitoring_engine.py             — 複数 Monitor をまとめるエンジン
    - streamlit_dashboard.py           — Streamlit ベースの監視ダッシュボード
  - execution/
    - execution_engine.py              — ExecutionEngine（主ループ等はここ）
    - order_manager.py                 — OrderManager（外向き API）
    - order_repository.py              — OrdersDB 操作
    - reconciler.py                    — 再起動時の同期・照合ロジック
    - broker_factory.py                — ブローカークライアント生成（Mock/Live 切替）
    - broker_api.py / broker clients   — ブローカーインターフェース
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み計算
    - position_sizing.py               — 発注株数計算（lot/rounding 等）
    - risk_adjustment.py               — セクター上限・レジーム乗数
  - research/
    - factor_research.py               — 各種ファクター計算（duckdb）
    - feature_exploration.py           — 将来リターン・IC・統計サマリ
  - data/                              — 実行時に使用する SQLite / duckdb / flag / pid 等（リポジトリ外に配置することも可）
  - tools/
    - paper_verification_report.py     — Paper Trading 検証レポート生成 CLI

  - utils/
    - process_priority.py              — プロセス優先度 / CPU affinity ユーティリティ

---

## 例: よく使うコマンドまとめ

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 貢献 / 拡張のヒント

- DuckDB を用いたクエリは性能重視で記述されているため、テーブルスキーマを変える場合はクエリ部分も見直してください。
- AI 周り（news_nlp, regime_detector）は API 仕様や SDK の変更により修正が必要になる可能性があります。テスト用に _call_openai_api をモック化する設計になっています。
- 単体関数（portfolio, research）は純粋関数として設計されているためユニットテストが書きやすく、CI での検証がおすすめです。

---

必要に応じて README に含める詳細（例: .env.example のテンプレート、requirements.txt、Docker/Kubernetes 用の起動手順、運用チェックリスト 等）を追加できます。追加したい項目があれば教えてください。