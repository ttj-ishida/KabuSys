# KabuSys

日本株向け自動売買システムの一部モジュール群。戦略構築、ポートフォリオ構成、発注実行、監視、リサーチ、AI（ニュースセンチメント／レジーム判定）などを含みます。

以下はこのコードベースの README です。

---

## プロジェクト概要

KabuSys は「日本株自動売買」を想定したモジュール群です。主要な役割は次のとおりです。

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 注文管理・発注エンジン（execution）
- 監視・アラート（monitoring）
- ニュースを用いた NLP スコアリングや市場レジーム判定（ai）
- 運用補助ツール（tools）

設計方針の一部：
- DuckDB / SQLite をローカル DB として利用（prices_daily, raw_financials, monitoring DB 等）。
- OpenAI（gpt-4o-mini）を利用する機能は API キーを必要とし、失敗時はフォールバックやフェイルセーフを備えています。
- Paper Trading モードでは本番 DB と分離した専用 SQLite（data/paper_trading.db）を使用します。

---

## 主な機能一覧

- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視しログ化
  - TradeMonitor: 注文滞留や約定価格異常を検出・記録
  - RiskMonitor: ドローダウンやポジション上限監視、kill flag 発行
  - AlertManager: LINE Push による一方向通知（クールダウン管理）
  - Streamlit ダッシュボード (streamlit_dashboard.py)

- execution
  - ExecutionEngine を起動して発注セッションを実行（ブローカー抽象化）
  - OrderManager / OrderRepository / Reconciler：発注・同期・リコンシリエーション処理
  - Paper Trading 用の MockBrokerClient（KABUSYS_ENV に依存）

- portfolio
  - 銘柄選定、重み計算、リスク調整、株数算出（単元丸め・スケール調整等）

- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ai
  - news_nlp: ニュース記事から LLM による銘柄センチメントスコア算出 → ai_scores へ書込
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して market_regime を作成

- tools
  - paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力に出す

---

## セットアップ手順

前提
- Python 3.9+ 推奨（コードは型注釈に modern syntax を使用）
- SQLite（標準で同梱）、DuckDB を利用
- ネットワーク接続（OpenAI API を使う場合）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（簡易例）
   - pip install psutil duckdb openai requests streamlit

   ※ requirements.txt がある場合はそちらを利用してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - .env または OS 環境に必要なキーを設定します。自動で `.env` / `.env.local` がプロジェクトルートから読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（例・説明）：
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使い、専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で参照）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB DB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading 時の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

例 (.env)
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-...
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方

基本的な起動方法、ツール、注意点を示します。

1. 監視プロセス起動（SystemMonitor のポーリング）
   - python -m kabusys.run_monitoring
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（正の整数）。
   - run_monitoring は MonitoringDB（SQLite）を初期化します（init_monitoring_db）。

   停止方法:
   - data/stop_requested.flag を作成すると安全にループが終了します。

2. 実行エンジン起動（発注セッション）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
   - 起動時に data/execution.pid（デフォルト）に PID を書く挙動をする想定（Settings.pid_file_path を参照）。
   - data/stop_requested.flag が存在する場合は起動をスキップまたは停止します。

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で監視 DB を開き、Overview / Positions / Orders / System を表示します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
     - オプション:
       --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

5. AI 機能
   - ニュースセンチメント: kabusys.ai.score_news（内部で OpenAI を呼ぶ）
   - レジーム判定: kabusys.ai.regime_detector.score_regime
   - どちらも OPENAI_API_KEY の設定が必要（引数でキーを渡すことも可能）
   - OpenAI 呼び出しはリトライ・バックオフ戦略を実装していますが、API キーの設定やレートに注意してください。

6. kill flag（ExecutionEngine 停止）
   - KillSwitch は監視の結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
   - KillSwitch を手動で操作する場合は、このファイルを確認／削除してください（Settings.kill_flag_clear_on_start で起動時にクリアする挙動もあります）。

ログレベルは環境変数 LOG_LEVEL で設定できます（DEBUG/INFO/...）。

---

## よくあるファイル・フラグ

- data/monitoring.db — 監視用 SQLite（init_monitoring_db がテーブルを作成）
- data/paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb — DuckDB データベース（DUCKDB_PATH）
- data/execution.pid — ExecutionEngine の PID（既存 PID が stale なら削除される）
- data/stop_requested.flag — 起動中プロセスへ停止要求（run_monitoring / run_execution が参照）
- data/kill.flag — KillSwitch による停止フラグ（ExecutionEngine に停止指示）

---

## ディレクトリ構成（ハイレベル）

- src/kabusys/
  - __init__.py (バージョン等)
  - config.py — 環境変数／.env 読み込みロジックと Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング
    - risk_adjustment.py — セクター制限、レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄センチメント取得）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・読み書きラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常監視
    - risk_monitor.py — ドローダウン／ポジション制限
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once/run）
    - streamlit_dashboard.py — Streamlit UI
  - execution/
    - order_manager.py — 発注の外向き API、重複防止等
    - reconciler.py — 起動時の自動復旧・突合せ
    - （その他：broker_factory, execution_engine, order_repository 等は実装ファイルが存在する想定）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

---

## 注意事項 / 運用上のヒント

- .env の自動読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します（config._find_project_root）。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードはテストなどで無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Paper Trading
  - KABUSYS_ENV=paper_trading にすると、発注部分は MockBroker を使い、本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH を使います。実運用前の検証に利用してください。

- OpenAI / ネットワークリソース
  - ai.news_nlp と regime_detector は OpenAI API を使用します。利用には OPENAI_API_KEY が必要です。API 利用料とレート制限に注意してください。
  - 呼び出しはリトライ戦略を実装していますが、失敗時はフェイルセーフ（スコア 0.0 など）を適用します。

- DB マイグレーション
  - init_monitoring_db は冪等でテーブルを作成し、一部カラム（peak_value, latency_ms）の後付けマイグレーションに対応しています。

---

問題や改善要望、追加したいドキュメント（API リファレンス、運用 runbook、デプロイ手順等）があれば教えてください。README を運用向けにさらに詳細化（例: systemd サービス定義、Docker 化、CI での DB 初期化手順など）することもできます。