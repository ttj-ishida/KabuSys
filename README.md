# KabuSys

日本株向け自動売買システムのコアライブラリ・起動スクリプト群です。  
本リポジトリは、システム監視、実行エンジン、ポートフォリオ構築、リサーチ（ファクター計算）、AIを使ったニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 実トレード / ペーパートレードの実行エンジン（ExecutionEngine）
- システム健全性・発注状況を定期的にチェックする監視（Monitoring）
- ポートフォリオ構築（銘柄選定、重み計算、株数算出）
- ファクター計算・特徴量探索（DuckDB を使った分析）
- OpenAI を使ったニュース NLP（センチメント集約）
- 設定ウィザード・設定検証ツールと各種ユーティリティ

設計上のポイント:
- 環境変数（.env）で設定を管理。プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可）。
- Paper Trading は本番 DB とは分離され、専用 SQLite を使用。
- DuckDB を分析用に使用（prices_daily / raw_financials 等を想定）。
- 監視ログは SQLite（data/monitoring.db）へ永続化。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパー切替）
  - run_monitoring: SystemMonitor のポーリングループを起動

- 設定関連
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の設定検証（PyYAML が有れば YAML 内容も検証）

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/Disk・データ鮮度・実行プロセス監視
  - TradeMonitor: 発注ログ監視（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - MonitoringEngine: 上記を束ねた定期ポーリング、Kill Switch 評価、Alert 管理
  - MonitoringDB: 監視用 SQLite スキーマ初期化 / CRUD

- 実行（execution）
  - BrokerClientFactory（本番/モック切替）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（注文件数上限など）

- ポートフォリオ（portfolio）
  - 銘柄選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクター制限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ

- AI（ai）
  - news_nlp.score_news: OpenAI を使いニュースを銘柄ごとにセンチメントスコア化し ai_scores に書込
  - regime_detector.score_regime: ETF の MA とマクロニュースを組合せて市場レジームを判定・保存

- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率、成功率、レイテンシ等）

- ユーティリティ
  - ロギング設定（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - .env 自動ロードロジック

---

## セットアップ手順

前提:
- Python 3.10+（typing の `X | Y` を使用しているため）
- Git 等でソースをクローン済み

1. 仮想環境作成（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 依存パッケージをインストール
   - 最低限の推奨パッケージ:
     - duckdb, psutil, openai
   - validate_config の YAML 検証を使う場合は PyYAML を追加
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を作成
   - 生成ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参照して手動で `.env` を作成
   - 自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` があれば Settings が起動時に読み込みます。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. データディレクトリ（logs / data）を作成（通常は自動作成される）
   - mkdir -p data logs

5. 必要な DB ファイル
   - DuckDB、SQLite ファイルは default で `data/kabusys.duckdb`、`data/monitoring.db`、`data/paper_trading.db`（ペーパー時）を使用します。
   - DuckDB / SQLite のテーブルは実行コンポーネントが起動時に作成する仕組みです（一部はスクリプトで初期化）。

注意:
- OpenAI を使用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡してください。
- 実行時、プロセス優先度変更などは psutil 経由で行うため十分な権限が必要な場合があります。

---

## 使い方

CLI 例・主要コマンド:

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を FAIL にしたい場合:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 環境切替:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合、MockBrokerClient を使用しデータは `data/paper_trading.db` に記録されます。

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を秒で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ライブラリ API 例（簡単な利用例）:

- リサーチモジュール（DuckDB 接続を渡して呼ぶ）
  - from kabusys.research import calc_momentum
  - result = calc_momentum(duckdb_conn, date(2026, 4, 1))

- AI ニューススコア付与
  - from kabusys.ai import score_news
  - n = score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")

その他の挙動・フラグ:
- 実行停止フラグ:
  - プロジェクトの data ディレクトリに `stop_requested.flag` を置くと、run_monitoring / run_execution のループが検知して順次停止します（スクリプト内の停止フラグ検出に従います）。
- Kill Switch:
  - リスク閾値を超えると `data/kill.flag` に理由を書き込み、ExecutionEngine 側で停止シグナルとして利用します。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアをオフにする）。

---

## 主要環境変数

（全て `.env` で管理可能）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） - 上書き可（スクリプト内で参照）
- PAPER_FILL_MODE: ペーパートレードの約定挙動 ("instant" | "partial" | "never" | "reject")

自動 .env 読み込み:
- 既定でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数は上書きされません）。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

以下は src/kabusys 配下の主要ファイル・パッケージ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (※ソース参照)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         (※ソース参照)
  - execution/
    - execution_engine.py     (※実行ロジック)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - ... (前述)
  - data/                      — データファイル（デフォルト: data/*.db, pid/flag ファイルを格納）
  - logs/                      — ログ出力先（デフォルト）

（※）上記は主要ファイルのみ抜粋しています。実際のリポジトリで細かいファイルを確認してください。

---

## 注意点 / トラブルシューティング

- Python バージョン: 3.10+ を推奨（| 型ヒントを使用）
- 依存関係:
  - duckdb：分析クエリに必須
  - psutil：プロセス優先度設定 / メトリクス取得
  - openai：AI 機能（news_nlp / regime_detector）
  - PyYAML（任意）：validate_config の YAML 検証に使用
- OpenAI API を使う場合は API キーが必須。未設定だと該当機能で例外が発生します（関数呼び出しでキーを渡すことも可能）。
- ログディレクトリの作成に失敗するとファイルログは無効化され、コンソール出力のみになります（setup_logging の挙動）。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）をチェックします。外部から安全に停止させたい場合は該当ファイルを作成してください。
- validate_config は config/*.yaml の存在チェックを行います。YAML パースには PyYAML が必要です。

---

必要であれば、README に「動作フロー図」「API リファレンス（関数一覧）」「サンプル .env テンプレート」などを追加可能です。どの情報を拡張したいか教えてください。