# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュール・スクリプトの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

注意: 実行には外部 API キーや DB ファイルなどが必要です。サンプル実装・ユーティリティを中心に含まれており、本番用にそのまま運用する前に設定確認とテストを行ってください。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群をまとめたライブラリ／アプリケーション群です。主な機能は次の通りです。

- 注文管理・発注（ExecutionEngine 相当の起動スクリプトを含む）
- モニタリング（プロセス・データ鮮度・注文の監視、kill flag、LINE 通知）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI 連携（ニュースの NLP スコアリング、レジーム判定：OpenAI を利用）
- ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

設計方針の例:
- DuckDB を用いた時系列データ処理（prices_daily, raw_financials 等）
- SQLite（monitoring / paper_trading）による監視ログ・注文ログ永続化
- 環境変数 / .env による設定管理（Settings クラス）
- Paper Trading と Live（本番）を明確に分離可能

---

## 機能一覧（抜粋）

- 設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可）
  - Settings クラスで各種環境変数をラップ（KABUSYS_ENV, OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）
- 実行（Execution）
  - 起動スクリプト: run_execution.py
  - Broker クライアントの切り替え（paper_trading 時は MockBrokerClient を使用し DB を分離）
  - OrderManager / RiskManager / Reconciler 等による堅牢な発注フロー
- 監視（Monitoring）
  - run_monitoring.py によるポーリング監視ループ
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE）
  - Streamlit ダッシュボード用スクリプト
- ポートフォリオ構築
  - 候補選定、等重配分・スコア重み配分、リスク調整（セクターキャップ、レジーム乗数）、株数決定（lot 単位丸め）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC・統計サマリー
- AI（OpenAI）
  - ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores に保存（score_news）
  - マクロニュース + ETF MA200 乖離から市場レジームを判定（score_regime）
- ツール
  - paper_verification_report.py: Paper Trading DB を解析して検証レポートを出力
  - streamlit_dashboard.py: 監視ダッシュボードを Streamlit で表示

---

## セットアップ手順

以下はローカルで開発 / 実行する際の最小セットアップ例です。

前提: Python 3.9+ を想定（duckdb・openai 等の互換性を確認してください）。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージインストール
   - pip install duckdb psutil requests streamlit openai

   （必要に応じて他パッケージを追加してください。sqlite3 は標準ライブラリです。）

3. プロジェクトルートに .env ファイルを作成
   - サンプル: .env.example を参照して必要な環境変数を設定してください。
   - 自動ロード: デフォルトで .env と .env.local をプロジェクトルート（.git または pyproject.toml がある場所）から読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 主な環境変数（代表）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（データ取得等で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（ブローカー API）
   - SQLITE_PATH: 監視用 SQLite DB のパス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境で使用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

5. データディレクトリの作成
   - mkdir -p data

---

## 使い方（主要スクリプト）

※ 設定は Settings クラスで定義された環境変数から取得されます。

- 監視プロセス起動（ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 実行時にプロセス優先度を "high" にセットし、MonitoringDB（SQLite）へ system_status を定期記録します。

- 実行エンジン起動（発注セッション）
  - KABUSYS_ENV=paper_trading の場合、paper_trading DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用して本番 DB と完全分離されます。
  - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション --db で DB パスを指定可能（指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db が使われます）。
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などのサマリーと PASS/FAIL 判定。

- Streamlit ダッシュボード（監視ビジュアライズ）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き、Overview / Positions / Orders / System タブを表示します。

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を集約して OpenAI に投げ、ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ日次判定を記録します。
  - どちらも OPENAI_API_KEY を設定するか api_key 引数でキーを渡してください。

---

## 主要設定（Settings）の挙動抜粋

- 自動 .env 読み込み順序:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- 重要なプロパティ（一部）
  - env: KABUSYS_ENV（development / paper_trading / live）
  - sqlite_path / duckdb_path / paper_sqlite_path
  - pid_file_path（デフォルト: data/execution.pid）
  - kill_flag_path（デフォルト: data/kill.flag）
  - PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant / partial / never / reject）
  - log_level: LOG_LEVEL（DEBUG/INFO/...）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings 定義 (.env 自動ロード含む)
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading での分離対応）

packages / サブモジュール:
- kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と MonitoringDB クラス（永続化層）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- kabusys/execution/
  - order_manager.py — 発注の外向き API / ステートマシン管理
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジション突合）
  - （その他: broker_factory, execution_engine, order_repository 等 — 一部はこの抜粋に含まれています）
- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数決定・利用可能現金・スロット丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- kabusys/research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でセンチメント化して書き込む処理
  - regime_detector.py — マクロニュースと ETF MA 乖離を用いた市場レジーム判定
- kabusys/tools/
  - paper_verification_report.py — Paper Trading DB 向け検証レポート生成ユーティリティ
- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・設定:
- data/
  - kabusys.duckdb（DuckDB、デフォルト path は data/kabusys.duckdb）
  - monitoring.db（SQLite、デフォルト data/monitoring.db）
  - paper_trading.db（Paper Trading 用 SQLite、デフォルト data/paper_trading.db）
  - execution.pid / kill.flag（PID / 停止フラグ）

---

## 実行時の注意点・運用上のポイント

- Paper Trading と Live は DB を分離して取り扱う設計です。KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用します。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。0 以下の値は無効でデフォルト 60 秒にフォールバックします。
- run_execution と run_monitoring は起動時にプロセス優先度を "high" にしようとします。権限がない場合は警告が出ますが処理は継続します。
- OpenAI を呼び出す際はネットワークエラー・429 等を考慮してリトライが実装されていますが、API キーとコスト管理には注意してください。
- monitoring_db.init_monitoring_db は冪等（スキーマ作成 / マイグレーションの一部）なので初回起動で DB を準備します。
- kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine を外部から停止する仕組みがあります。起動時に自動でクリアするオプションがあります（Settings.kill_flag_clear_on_start）。

---

## 参考コマンド例

- 監視を起動（デフォルト設定）
  - python -m kabusys.run_monitoring

- 実行エンジンを起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## ライセンス / 責務

このドキュメントはコードベースの抜粋に基づく概要説明です。実稼働に用いる場合は追加の安全対策・検証（ブローカー接続の実証、注文フローの単体・統合テスト、監査ログ、障害復旧手順など）を必ず実施してください。

---

必要なら、README に含める具体的な .env.example のテンプレート、ユニットテストの実行方法、CI 設定例なども作成します。どの情報を追加しますか？