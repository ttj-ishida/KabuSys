# KabuSys — README

本ドキュメントはこのリポジトリ（KabuSys）の概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群です。  
主な目的は以下のとおりです：

- シグナルに基づく注文発行・状態管理（Execution Engine）
- 注文・約定・ポジション・ダッシュボードの永続化（SQLite）
- システム稼働状況・注文監視・リスク検出（Monitoring）
- ポートフォリオ構築・ポジションサイズ算出（Portfolio）
- ファクター計算・リサーチ用ユーティリティ（Research）
- ニュース NLP（OpenAI）を用いたセンチメントスコアリング（AI）
- Paper Trading の検証レポート生成ツール

設計方針として、DuckDB を分析用途のデータベース（価格・財務情報等）に使用し、SQLite を監視ログ／注文ログ等の永続化に使用します。外部 API 呼び出し（kabuステーション、J-Quants、OpenAI 等）は抽象化され、paper_trading モードでは本番 DB と完全に分離されるようになっています。

---

## 機能一覧（抜粋）

- Execution
  - Broker クライアントの抽象化（実口座 / モックの切り替え）
  - 起動時のリコンシリエーション（Reconciler）：OrderSent 等の復旧
  - OrderManager による状態遷移管理・送信・キャンセル処理
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン／ポジション上限監視と dashboard 更新
  - KillSwitch：条件に応じてフラグファイルを書き ExecutionEngine 停止指示
  - AlertManager：LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定（スコア順）、等金額 / スコア加重の重み計算
  - 単元株丸め・リスクベースの株数算出、セクター上限適用、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）・統計サマリ
- AI
  - ニュース集約 → OpenAI によるセンチメント算出 → ai_scores へ格納
  - 市場レジーム判定：ETF MA + マクロニュースセンチメントで判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 前提条件 / 依存関係

- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- 標準ライブラリ: sqlite3, datetime, os, logging 等

pip でのインストール例（仮の requirements を想定）:
pip install duckdb psutil requests openai streamlit

注意:
- OpenAI を使う機能は環境変数 OPENAI_API_KEY が必要です。
- psutil によるプロセス優先度設定は OS により権限が必要な場合があります。

---

## 環境変数（主なもの）

アプリ設定は環境変数またはプロジェクトルートの .env / .env.local によって読み込まれます（自動ロード。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数：

必須（実運用で使用する場合）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / デフォルトあり
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
  - paper_trading の場合は MockBroker を使い DB を data/paper_trading.db に保存
- DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）デフォルト "instant"
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除（"1" で有効）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）

.env の書式は一般的な shell 形式に準拠しており、コメント・クォート等をパースして読み込みます。

---

## セットアップ手順（ローカルでの例）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil requests openai streamlit

4. .env を用意する
   プロジェクトルートに .env（または .env.local）を作成し、必要な環境変数を定義します。
   例:
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=your_token
     OPENAI_API_KEY=sk-...

5. データディレクトリを作成
   mkdir -p data

6. DuckDB / SQLite の初期化
   - 多くのモジュールは起動時にテーブル作成（冪等）を行うため、特別な初期化手順は不要です。
   - monitoring は init_monitoring_db() で必要テーブルを作成します（自動実行されます）。

---

## 使い方（起動・実行例）

CLI は Python モジュールとして実行できます（パッケージとしてインストールされている・カレントディレクトリがパッケージを含む場合）:

- Monitoring を起動する
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 実行例:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  特記事項:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。
  - 起動時にプロセス優先度を "high" に変更しようとします（権限によっては失敗して警告が出ます）。

- ExecutionEngine を起動する
  - 実環境（live）では実際の BrokerClient を使用。
  - paper_trading モード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    → MockBrokerClient を使用し、デフォルトで data/paper_trading.db に保存します。
  - 実行時はプロセス優先度を "high" に設定しようとします。

- Streamlit ダッシュボード
  - 起動コマンド（Monitoring DB を読み取り専用で開く）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - 例: 期間指定でレポートを出力
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / Research のプログラム的利用
  - モジュール関数をインポートして使用できます（例）:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    from kabusys.research.factor_research import calc_momentum
  - OpenAI を使う関数は api_key 引数を受け取るか、OPENAI_API_KEY 環境変数を参照します。

---

## 注意点 / 運用上のポイント

- paper_trading:
  - KABUSYS_ENV=paper_trading の場合、本番 DB と分離され paper_sqlite_path（デフォルト data/paper_trading.db）を使います。
  - PAPER_FILL_MODE によりモックの約定挙動を制御できます。

- kill.flag:
  - KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止シグナルを送る仕組みです。
  - Execution 起動時に既存 kill.flag をクリアするには KILL_FLAG_CLEAR_ON_START=1 を設定してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブルとインデックスの作成、および既存テーブルへのカラム追加（簡易マイグレーション）を行います（冪等）。

- 権限:
  - psutil による優先度設定や CPU affinity の操作は権限が必要な場合があります。失敗するとログに警告が出ますが処理は継続します。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベースの主要なファイル／モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py                — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py               — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py                — 注文滞留・約定異常監視
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — KillSwitch（flag ファイル書込み）
    - alert_manager.py                — LINE Push 通知ラッパー
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード（読み取り専用）
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (broker_factory, execution_engine 等の実装が別ファイルに存在)
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数決定・丸め・aggregate cap
    - risk_adjustment.py              — セクター上限・レジーム乗数
  - research/
    - factor_research.py              — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI 呼出）
    - regime_detector.py              — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - monitoring/monitoring_db.py      — （上で示した通り）

（上記以外にも execution 側の多くのファイル／ユーティリティが含まれます。各モジュールの docstring に仕様や設計意図が書かれていますので参照してください。）

---

## サポート / 開発時メモ

- 単体テストや CI を追加する際は、.env の自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと良いです。
- OpenAI 呼び出し部分はネットワークに依存するため、ユニットテストでは _call_openai_api をパッチしてモック化してテストする設計になっています。
- DuckDB と SQLite を組み合わせた設計のため、分析処理（research / ai のデータ集約）は DuckDB 側で行い、監視や注文の永続化は SQLite 側で行います。

---

問題点や追加してほしい情報があれば教えてください。README をより詳細に（サンプル .env、起動スクリプトの systemd ユニット例、テスト手順など）拡張できます。