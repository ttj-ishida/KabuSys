# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / 研究 / 監視ユーティリティ群をまとめたモジュール群です。本リポジトリは発注エンジン（ExecutionEngine）、監視システム（MonitoringEngine）、ポートフォリオ構築、ファクター計算、LLM を用いたニュースセンチメント、Paper Trading 検証ツール等を含みます。

---

## 概要

KabuSys は次を目的とした Python ベースのライブラリ／アプリケーション集合です。

- 発注・注文管理・リコンシリエーション（execution）
- システム・注文・リスク監視とアラート（monitoring）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- ファクター計算・研究ユーティリティ（research）
- ニュース NLP / レジーム判定における LLM 連携（ai）
- Paper Trading の検証レポート生成ツール（tools）

各モジュールは可能な限りフェイルセーフに設計され、Paper Trading（環境 `paper_trading`）では本番データベースと分離して動作するようになっています。

---

## 主な機能一覧

- Execution
  - ブローカークライアントの抽象化（Mock / 実ブローカー）
  - OrderManager / OrderRepository による注文の状態管理
  - Reconciler による起動時の自動復旧（OrderSent 照合・ポジション差分検出）
  - リスク管理（RiskManager）やオーダー再送など（実装参照）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：しきい値超過時に `data/kill.flag` を作成して ExecutionEngine を停止
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio
  - 候補選定（score / rank に基づく）、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め・aggregate cap）

- Research
  - ファクター（Momentum / Volatility / Value）計算（DuckDB ベース）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー

- AI
  - ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores へ書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（bull / neutral / bear）
  - API 呼び出しはリトライ・バックオフを実装、部分失敗への耐性あり

- Tools
  - paper_verification_report：Paper Trading DB を元に稼働率・注文成功率・レイテンシ等を出力

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能に依存）を想定しています。

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトで requirements.txt を用意している場合はそれを使用してください）

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
   - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
   - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 実行方法（使い方）

以下は主要なエントリポイント例です。

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 停止方法: Ctrl+C またはプロジェクトルートの `data/stop_requested.flag` を作成

- エンジン起動（ExecutionEngine）
  - 実行前に `KABUSYS_ENV` を設定（paper_trading の場合は MockBrokerClient を使用）
  - python -m kabusys.run_execution
  - 実行中は `data/execution.pid` が作成される
  - 停止: `data/stop_requested.flag` を作成すると安全に停止します
  - paper_trading 環境では `data/paper_trading.db`（あるいは指定された PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開くために URI を使っています（起動中に DB がない場合はエラーを表示）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定 / ニューススコアリング
  - ai モジュールは OpenAI API キーを必要とします（引数で渡すか環境変数 OPENAI_API_KEY を設定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して単体で利用可能

注意:
- 実行スクリプト（run_monitoring/run_execution）は起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存）。権限がない場合は警告が出ますが実行は継続します。
- run_monitoring は監視用 DB（Settings.sqlite_path）を環境にかかわらず使用します（監視は常に本番用パスを想定）。

---

## フラグ / PID / 停止制御

- data/stop_requested.flag
  - run_monitoring / run_execution のループを止めるためのファイル。存在すると安全にループを終了します。

- data/kill.flag
  - KillSwitch により書き込まれる停止フラグ。ExecutionEngine 側で起動時にこれを検出して起動を抑止します。`KillSwitch.clear()`（プログラム経由）や `rm data/kill.flag` で削除できます。

- data/execution.pid
  - run_execution が起動時に書き込む PID ファイル。SystemMonitor はこのファイルと実プロセスの存在を検査して stale PID を検出／削除します。

---

## 環境変数の自動読み込みルール

- 自動読み込み順序:
  - OS の環境変数（優先）
  - プロジェクトルートの `.env`（存在する場合。override=False）
  - `.env.local`（存在する場合。override=True で上書き。ただし OS のキーは保護）

- プロジェクトルート判定:
  - `.git` または `pyproject.toml` を親ディレクトリで探索して決定します。
  - 見つからない場合は自動ロードをスキップします。

- 自動読み込みを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## トラブルシューティング（よくある注意点）

- psutil の優先度設定で AccessDenied 警告が出ることがあります（一般ユーザでは権限不足）。挙動自体は継続します。
- DuckDB / SQLite ファイルのパス（デフォルトは data/ 以下）が読書き可能か確認してください。
- Streamlit で DB を read-only モードで開けない場合は「MonitoringEngine を先に起動して DB を生成」してください。
- OpenAI API 呼び出しで失敗する場合は環境変数 OPENAI_API_KEY の確認とネットワークの到達性を確認してください。各 API 呼び出しはリトライ・バックオフ実装がありますが、API キー未設定は例外になります。
- Paper Trading と本番 DB を混同しないよう、KABUSYS_ENV を正しく設定してください。paper_trading では専用の paper_sqlite_path を使います。

---

## ディレクトリ構成（主要ファイル・モジュール）

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / Settings 管理
- run_monitoring.py                  — SystemMonitor ポーリングループ起動
- run_execution.py                   — ExecutionEngine 起動スクリプト
- utils/
  - __init__.py
  - process_priority.py              — process priority / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py                 — SQLite テーブル作成・CRUD ヘルパ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 execution 関連モジュール)
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/ (実行時に参照／作成される想定)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用デフォルト)
  - kabusys.duckdb (DuckDB ファイル)
  - kill.flag / stop_requested.flag / execution.pid
- tools/
  - __init__.py
  - paper_verification_report.py

（上記はリポジトリ内の主要なモジュールを抜粋したものです。詳細は各ファイルを参照してください。）

---

## 開発・拡張についてのメモ

- DuckDB を分析用に利用しており、research モジュールは prices_daily / raw_financials 等のテーブルを前提としています。データパイプライン側（kabusys.data.pipeline など）でこれらを用意してください。
- AI 関連処理は外部 API に依存するため、テスト時は内部の API 呼び出しラッパー関数をモックすることを推奨します（コード中に patch を想定した注記あり）。
- 設定読み込み・マイグレーションは簡単な冪等処理を備えています（monitoring_db.init_monitoring_db など）。

---

必要に応じて README に追加したい項目（例: サンプル .env, Docker / systemd サービス定義例、詳細な API ドキュメント）があれば教えてください。