# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースNLP / レジーム判定）などを含む自動売買プラットフォームのコア実装を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な責務は以下の通りです。

- ExecutionEngine: ブローカークライアント経由で注文を実行（本番 / ペーパートレード対応）
- Monitoring: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視しアラート／Kill Switch を提供
- Portfolio construction: 候補選定、重み付け、株数決定（単元丸め・リスク制約）
- Research: ファクター計算、将来リターン、IC 計算等（DuckDB を利用）
- AI モジュール: ニュース記事のセンチメント評価（OpenAI）および市場レジーム判定
- CLI ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成 など

設計上の特徴:
- DuckDB / SQLite を利用したオンディスク DB（分析用 / 監視用 / ペーパー用に分離）
- .env ベースの環境設定、自動ロード機能（必要に応じて無効化可能）
- ペーパートレード時は実ブローカーと完全分離された DB を使用
- OpenAI を用いる NLP 部分は障害に強い（リトライ・フォールバック）

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパートレードの切替
  - リスク管理（ポジション上限、ドローダウン等）
  - 注文管理・リコンシリエーション

- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセスの存在監視（PID ファイル）
  - データ鮮度チェック（prices_daily 等）
  - trade_logs / risk_logs / dashboard の永続化
  - Kill Switch（条件で data/kill.flag を書き込み、ExecutionEngine を停止）

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等金額・スコア加重・リスクベース配分
  - セクターキャップ適用、レジーム乗数対応
  - 単元株（lot）丸め、aggregate cap のスケーリング

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリー

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント評価（gpt-4o-mini を想定）
  - マクロニュースを使った市場レジーム判定
  - API 呼び出しはバッチ化・リトライ・レスポンス検証を実装

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（typing 記法や一部ライブラリを想定）
- Git

1. レポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（最小セット）
   pip install duckdb psutil openai

   追加（検証用等）
   pip install PyYAML  # validate_config の YAML 検証を有効にする場合

   ※ 実運用では requirements.txt を用意している前提で pip install -r requirements.txt を推奨します。

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup

   - または手動でリポジトリ直下に `.env` を配置してください（.env は絶対に Git にコミットしない）。

   主要な環境変数（デフォルト値 / 備考）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
   - OPENAI_API_KEY (AI 機能を使う場合)

   自動読み込みを無効にする:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードをスキップします。

5. 設定検証（任意）
   python -m kabusys.validate_config
   警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict

---

## 使い方（起動・運用）

- 実行エンジン起動（本番 / ペーパー切替）
  - 本番（環境変数で切替）
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（Mock Broker を使用、専用 DB を利用）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実装上の注意:
  - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
  - 実行エンジンは内部で PID ファイル（デフォルト data/execution.pid）を扱います。

- 監視プロセス起動
  python -m kabusys.run_monitoring

  オプション的挙動:
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    デフォルトは 60 秒。1 秒未満や 0 を与えるとデフォルトへフォールバックします。
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存せず）。

- 停止方法 / Kill Switch
  - 実行者が明示的に ExecutionEngine を停止したい場合:
    - data/kill.flag に理由文字列を書き込むと、ExecutionEngine の起動中に監視側や起動スクリプトが検出して停止します（KillSwitch の仕組み）。
    - monitoring 側の stop は data/stop_requested.flag を置くことでも行えます（run_execution.py / run_monitoring.py でチェックしています）。
  - 実行スクリプトは KeyboardInterrupt による終了にも対応しています。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

---

## 設定・挙動に関する補足

- ロギング
  - setup_logging() によりコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）を設定します。
  - ログディレクトリは環境変数 LOG_DIR、もしくはデフォルト `logs/` を使用します。
  - 設定解決順は: 引数 > 環境変数 > デフォルト。

- プロセス優先度
  - 起動スクリプトは初期化時に set_process_priority("high") を呼び出します（psutil を使用）。OS により設定不可な場合は警告ログが出ます。

- DB マイグレーション（監視 DB）
  - monitoring_db.init_monitoring_db() はテーブル作成と簡易マイグレーション（新カラム追加）を行います。冪等設計です。

- OpenAI 関連
  - ニュース NLP / レジーム判定は OpenAI API（gpt-4o-mini 等）を利用する設計です。API キーは OPENAI_API_KEY を使用します。
  - レスポンスの検証、バッチ化、リトライ、スコアクリッピング等の安全策が組み込まれています。
  - API 未設定の場合は例外またはフォールバック（0.0）を使って安全に動作します（モジュールにより挙動は異なります）。

---

## 主要なディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み / Settings
- config_setup.py           — .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — マクロ + MA によるレジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — （注文周りの監視ロジック）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書込ユーティリティ
  - monitoring_engine.py    — 各モニタを束ねるエンジン
  - alert_manager.py        — （アラート送信ロジック）
- execution/
  - execution_engine.py     — 実行エンジン本体
  - broker_factory.py       — ブローカークライアント生成（Mock 本番分岐）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py             — prices_daily 等の取得ユーティリティ（DuckDB 参照）
  - stats.py                — zscore 等補助関数
- tools/
  - paper_verification_report.py

その他:
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

---

## よくある運用フロー（例）

1. .env を作成（ウィザード）
   python -m kabusys.config_setup

2. 設定検証
   python -m kabusys.validate_config

3. 監視を起動（長時間運用）
   python -m kabusys.run_monitoring

4. Execution を起動（同一マシン／別プロセス）
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution

5. 問題発生時は monitoring が kill.flag を書き込み、execution 側が停止する
   手動停止は data/stop_requested.flag または data/kill.flag を作成しても可

---

## 開発・テスト時のヒント

- validate_config は PyYAML が入っていれば config/*.yaml のパースも検証します。入れておくと安心です。
- 環境変数の自動ロードが邪魔なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部ネットワークを必要とするため、ユニットテストでは _call_openai_api をモックするか、API キーを使わない設定で行ってください。
- DuckDB / SQLite のファイルパスは .env で簡単に切り替え可能です（テスト用に tmp ディレクトリを指定すると便利）。

---

もし README に追記してほしい内容（例: 実行フロー図、API 仕様、設定項目の完全一覧、requirements.txt の内容、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env テンプレートも作成できます。