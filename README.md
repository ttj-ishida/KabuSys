# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリ。  
この README はプロジェクトの概要、機能一覧、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア部分（データ処理・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI 補助）を提供します。  
主要コンポーネントは純粋関数によるポートフォリオ構築、DuckDB を用いたリサーチ/ファクター計算、SQLite による監視ログ永続化、発注エンジン（本番 / ペーパートレード分離）、および OpenAI を用いたニュース NLP / レジーム判定です。

---

## 機能一覧

- 環境設定管理とウィザード
  - `.env` の対話的作成 / 更新（config_setup）
  - 起動前チェック（validate_config）
- 発注実行エンジン
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker 対応）
  - リスク管理（RiskManager）と約定管理（OrderManager）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - SQLite へ監視ログ永続化（monitoring_db）
  - Kill Switch（閾値超過で `data/kill.flag` を書き込み ExecutionEngine を安全停止）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター（DuckDB 経由）
  - 将来リターン、IC（Spearman rank）、要約統計量
- AI サポート
  - ニュースのセンチメント評価（OpenAI を利用、結果を `ai_scores` に保存）
  - マクロニュース + ETF（1321）の MA200 を組み合わせたレジーム判定
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定
  - Paper Trading 向け検証レポート生成スクリプト

---

## 必要条件

- Python 3.10+
- 以下の主な依存ライブラリ（プロジェクトで必要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML のパースをしたい場合）
- SQLite は Python 標準の sqlite3 を使用
- 実行環境に応じた追加のブローカークライアントやライブラリ（本番接続時）

必要なパッケージは通常 `pip install -r requirements.txt` を用意しておくと便利です（本リポジトリに requirements.txt がない場合は上記をインストールしてください）。

---

## セットアップ手順（推奨クイックスタート）

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil openai PyYAML

3. 環境変数ファイル `.env` を作成します（対話ウィザード推奨）。
   - python -m kabusys.config_setup
     - ウィザードは J-Quants トークンや KABU_API_PASSWORD、DB パス、KABUSYS_ENV 等を設定します。
   - 生成された `.env` は絶対に Git にコミットしないでください。

4. 設定検証を実行します。
   - python -m kabusys.validate_config
   - 重大な問題がなければ OK と表示されます。警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリを必要に応じて作成します（多くは自動作成されますが、権限に注意）。

---

## 環境変数（主なもの）

以下は主な環境変数とデフォルト値 / 説明です（詳細は `kabusys/config.py`、`config_setup.py` を参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を用い、専用 DB（data/paper_trading.db）を使用
  - live: 本番動作
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に `data/kill.flag` を自動クリアするか（0/1、デフォルト 0）

---

## 使い方（主要スクリプト）

起動スクリプトはパッケージモジュールとして提供されています。プロジェクトルートで以下を実行します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH` に書き込まれます（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - PID は `data/execution.pid` に作成されます。
    - 停止は `data/stop_requested.flag` または `data/kill.flag` による仕組みが使われます。

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可（デフォルト 60）。
    - Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path を使用して監視ログを書きます（監視は全環境の本番 DB を参照する設計）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を参照

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）。
  - プログラムから直接呼ぶ例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## 監視 / 停止フラグについて

- 停止フラグ（run_execution / run_monitoring が監視する）
  - data/stop_requested.flag — これが存在すると起動せず、実行中は検知して安全に停止します。
- Kill Switch
  - `KillSwitch`（監視ロジック）が条件を満たした場合 `data/kill.flag` を書き込み、ExecutionEngine に停止信号を送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると Execution 起動時に自動で kill.flag をクリアします（本番では危険なので通常 0 推奨）。

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。ログファイルは日次ローテーションで 30 日分保持されます。
- ログ関連設定:
  - LOG_LEVEL（環境変数）
  - LOG_DIR（ログファイルの保存ディレクトリ）

---

## 開発者向け API（抜粋）

- ポートフォリオ関連（純粋関数）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ / ファクター
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- AI
  - from kabusys.ai import score_news

これらは DuckDB 接続や引数（target_date など）を受け取り、純粋に計算／DB 書き込みを行う設計です。

---

## ディレクトリ構成

（src 下をパッケージルートとした主要ファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照: トレード監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック等)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - research, data, etc. (データパイプライン・統計ユーティリティは別モジュールとして存在)

プロジェクトルートには通常 `data/`（DB・フラグ・PID 等）や `logs/` が生成されます。

---

## トラブルシューティング（よくある注意点）

- Python バージョン: 型注釈に `X | Y` を使用しているため Python 3.10 以上が必要です。
- DB ファイルやログディレクトリのパーミッションに注意してください。ディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールログのみになります。
- OpenAI 関連:
  - API キーが未設定だと例外になります（AI 機能を呼ぶ前に OPENAI_API_KEY を設定）。
  - レート制限や一時的なネットワーク障害に対しては内部でリトライを行いますが、最終的に失敗した場合はフェイルセーフで処理をスキップします。
- ペーパートレード:
  - `KABUSYS_ENV=paper_trading` を設定するとペーパートレード専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB に影響しないよう分離されます。

---

以上がこのコードベースの README です。実行や開発で追加の説明が必要でしたら、どの機能・モジュールについて詳しく知りたいか教えてください。yaml の例や実行時の具体的な .env テンプレートも作成できます。