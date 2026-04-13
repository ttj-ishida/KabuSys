# KabuSys

日本株向けの自動売買・リサーチ基盤（ミニマル実装）。  
このリポジトリはトレード実行・監視・ポートフォリオ構築・因子計算・ニュースNLP 等のコンポーネント群で構成されています。ライブラリとして呼び出せる関数群と、簡易起動スクリプト / ツールを含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- 注文の発行および状態管理（ExecutionEngine / OrderManager）
- 実行状態・データ鮮度・ポジション・リスクの継続監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- 因子計算・リサーチ（モメンタム / ボラティリティ / バリュー 等）
- ニュースを LLM（OpenAI）でスコアリングする機能（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- Streamlit ベースの監視ダッシュボード

設計上のポイント：

- DuckDB / SQLite をデータ永続化に利用
- 環境変数 / .env による設定管理（kabusys.config）
- Paper Trading（テスト）用に本番 DB と分離可能
- 各処理はルックアヘッドバイアス対策やフェイルセーフ設計がなされている

---

## 主な機能一覧

- Execution
  - Order作成 / 送信 / 同期（OrderManager, Reconciler）
  - リスク制御（RiskManager）
- Monitoring
  - SystemMonitor: CPU/Memory/Disk, PID チェック、データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン / ポジション上限監視
  - MonitoringEngine: これらを束ねたポーリングエンジン
  - AlertManager: LINE push による通知（オプション）
  - KillSwitch: フラグファイルによる ExecutionEngine 停止指示
  - Streamlit ダッシュボード（監視表示）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - セクター制約適用（apply_sector_cap）
  - ポジションサイズ決定（calc_position_sizes）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC / 統計サマリー
- AI
  - news_nlp.score_news: ニュース記事をまとめて OpenAI で銘柄別センチメントを生成し ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロニュースで市場レジーム判定
- Tools
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提

- Python 3.10+（型注釈で PEP 604 の `X | Y` を使用しているため）
- git（ローカルで .env 自動ロードを使う場合にプロジェクトルート検出）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .\.venv\Scripts\activate
3. 依存パッケージをインストール（必要なライブラリの一例）
   - pip install duckdb psutil requests openai streamlit
   - （sqlite3 は標準ライブラリ）
   - ※ 実際の requirements.txt がない場合は用途に応じて追加してください
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（使用する機能による）例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（ai モジュール使用時）
   - 主要な設定（Settings クラス参照）:
     - KABUSYS_ENV: development | paper_trading | live（default: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
     - PAPER_TRADING_SQLITE_PATH（Paper DB、default: data/paper_trading.db）
     - SQLITE_PATH（監視用 DB、default: data/monitoring.db）
     - DUCKDB_PATH（DuckDB path, default: data/kabusys.duckdb）
     - PID_FILE_PATH（default: data/execution.pid）
     - KILL_FLAG_PATH（default: data/kill.flag）
     - LOG_LEVEL（DEBUG/INFO/...）
     - CPU/MEMORY/DISK 閾値 など

注意（Paper Trading）:
- KABUSYS_ENV=paper_trading にすると Execution 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。Monitoring のログは環境にかかわらず本番 sqlite_path を使う設計（監視は本番 DB へ記録）。

---

## 使い方（起動・主要コマンド）

基本的にはモジュール実行（python -m）で起動します。

1. 監視ループ（Monitoring）
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可。
   - 実行:
     - python -m kabusys.run_monitoring
     - または python src/kabusys/run_monitoring.py
   - ログや PID ファイル、kill.flag のパスは Settings で設定されたデフォルトパスを使います。
   - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

2. 実行エンジン（ExecutionEngine）起動
   - KABUSYS_ENV が paper_trading のときは MockBrokerClient を使い、Paper DB に記録します。
   - 実行:
     - python -m kabusys.run_execution
     - または python src/kabusys/run_execution.py

3. Streamlit 監視ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite DB を開きます。MonitoringEngine が DB を作成・更新していることが前提です。

4. Paper Trading 検証レポート生成（ツール）
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db path/to/paper_trading.db
   - 出力: 標準出力に検証レポート（稼働率・注文成功率・レイテンシ等）

5. AI（ニューススコア / レジーム判定）
   - これらはライブラリ関数として提供（スクリプトは同梱していません）。
   - 例（Python REPL またはスクリプト内で呼び出す）:
     - from kabusys.ai.news_nlp import score_news
       - score_news(duckdb_conn, target_date, api_key="...")
     - from kabusys.ai.regime_detector import score_regime
       - score_regime(duckdb_conn, target_date, api_key="...")
   - OPENAI_API_KEY を環境変数で設定しておくと api_key を省略できます。

その他のポイント
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）。0 以下や整数でない値は無効扱いされ 60 秒にフォールバックします。
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするかどうか（"1" で有効）。

---

## 設定（主な環境変数）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（ai モジュール）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動: instant | partial | never | reject
- PID_FILE_PATH — ExecutionEngine PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — kill.flag path（default: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default: 60）
- LOG_LEVEL — ログレベル（INFO 等）

---

## ディレクトリ構成（主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor をポーリングする起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 分離対応）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/Mem/Disk、PID、データ鮮度のチェック
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, OrderRepository, RiskManager 等の実装群)
    - reconciler.py — 再起動時の注文・ポジションの突合
    - order_manager.py — 注文の作成 / 送信 / 同期ロジック
    - （その他、brokerファクトリ・execution engine 関連）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - risk_adjustment.py — セクター制約 / レジーム乗数
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
    - __init__.py
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores を更新
    - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
  - data/ （実行時に生成／格納される想定）
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意

- Paper Trading 実行時は本番 DB と分離することを強く推奨します（既に設計済み）。
- OpenAI など外部 API 呼び出しを行う箇所はリトライ・フェイルセーフ実装がありますが、APIキーや課金設定の管理に注意してください。
- monitoring のログ構造・マイグレーションは monitoring_db.init_monitoring_db に記述されています。DB スキーマ変更時はマイグレーションに注意。
- 権限の関係でプロセス優先度や CPU affinity の設定が失敗することがあります（ログに警告が出ますが処理は継続します）。
- kill.flag を用いた停止は冪等になっています。ExecutionEngine 起動時に kill.flag を消去したい場合は Settings.kill_flag_clear_on_start を利用してください。

---

もし README に追加したい「使い方の具体的な例（サンプル .env, 起動手順のスクリプト等）」や、各コンポーネントの詳細ドキュメント（API の引数詳細・戻り値例）を別途作成したい場合は教えてください。必要に応じてサンプル .env と簡易デプロイ手順（systemd / Dockerfile のテンプレート）も用意できます。