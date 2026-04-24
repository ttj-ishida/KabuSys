# KabuSys

日本株向け自動売買システムのコアライブラリ群および運用用スクリプト群。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を使ったニュース解析・調査用ユーティリティなどを含むモジュール群で構成されています。

---

## 概要

- 目的: 日本株向けの自動売買パイプライン（研究 → シグナル → 発注 → 監視 → リスク制御）を提供する。
- 設計方針:
  - DuckDB / SQLite を用いたオンディスクデータと分析処理
  - 発注周りは実稼働（live）・ペーパー（paper_trading）を環境変数で切替可能
  - 監視コンポーネントは ExecutionEngine と独立して動作し、Kill Switch により発注停止を実施
  - OpenAI を用いたニュース NLP / レジーム判定機能を提供（APIキー必須）
  - CLI ツールで .env 作成支援・設定検証・レポート出力が可能

---

## 主な機能一覧

- Execution（発注エンジン）
  - 実口座・ペーパートレードの切替（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler による注文管理
  - PID ファイル / stop flag によるプロセス管理

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス存否を監視
  - TradeMonitor: 注文滞留や約定異常などを検出（コード内に実装）
  - RiskMonitor: ドローダウン・ポジション上限などを監視し、risk_logs / dashboard を管理
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア / ランク）
  - 等重・スコア重み・リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数

- Research（調査）
  - Momentum / Volatility / Value などのファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、ファクター統計

- AI（OpenAI 統合）
  - ニュース記事の銘柄別センチメントスコアリング（ai_scores）
  - マクロニュース + ETF MA で市場レジーム判定（market_regime）

- ユーティリティ
  - 環境設定ウィザード（.env 生成支援）
  - 設定検証 CLI（必須環境変数・config YAML のチェック）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要な主要依存（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を完全に行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください）

4. 環境変数の初期化
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（以下「主要な環境変数」を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

6. データディレクトリ等
   - デフォルトで使用されるファイル / ディレクトリ:
     - data/kabusys.duckdb （DuckDB、環境変数 DUCKDB_PATH）
     - data/monitoring.db （SQLite 監視 DB、環境変数 SQLITE_PATH）
     - data/paper_trading.db （ペーパートレード時の専用 SQLite、PAPER_TRADING_SQLITE_PATH）
     - logs/ (ログ保存先、環境変数 LOG_DIR)
     - data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 主要な環境変数（抜粋）

必須（運用する機能に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要（デフォルト有り）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能で必須
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）

監視・制御用
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

その他は .env ウィザードで項目や説明が表示されます。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- Execution（発注エンジン）を起動
  - 本番/開発/ペーパーを切替:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を数値（秒）で設定するとポーリング間隔を上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します

- Paper Trading の検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 系（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - プログラム的に呼び出す:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date)

---

## 運用上の注意

- Kill Switch:
  - risk_monitor の判定で KillSwitch が動作すると data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検出して発注を停止します。デフォルトパスは Settings.kill_flag_path（data/kill.flag）。

- PID / stop フラグ:
  - run_execution は data/execution.pid を使用し、data/stop_requested.flag によって起動拒否 / 停止を行います（stop フラグは手動運用用）。

- ログ:
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。コンソールは stdout に出力されます。

- paper_trading の完全分離:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使い、paper 用 SQLite に記録するため本番 DB へ影響を与えません。

- OpenAI 呼び出し:
  - レート制限や一時エラーに対して指数バックオフでリトライする実装がありますが、API キーの管理や費用には注意してください。

---

## ディレクトリ構成（主要ファイル）

例: src/kabusys 以下の主要ファイル・ディレクトリ

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env 対話式ウィザード CLI
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — 優先度 / CPU affinity 設定
  - execution/                 — 発注エンジン関連（OrderManager 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/                — 監視関連
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/                 — ポートフォリオ構築（純粋関数群）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/                  — 研究用ファクター計算
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py
  - data/                      — 実行時に使用する PID / flag / DB の既定位置（リポジトリルートに data/ を作成）

---

## 開発 / 拡張のヒント

- DuckDB を使う分析関数は conn（DuckDB 接続）を受け取り SQL と Python を併用しているため、テストで Mock しやすい設計です。
- OpenAI の呼び出しはモジュール内でラップしてあり、テスト時は該当関数をモックできます（例: unittest.mock.patch）。
- settings（kabusys.config.Settings）はプロパティベースで必要な env を遅延評価するため、単体テストで環境を差し替えやすくなっています。
- .env 自動読み込みはプロジェクトルート（.git or pyproject.toml）を探索して行われます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README の補足（依存関係一覧やデプロイ・systemd のユニット例など）を追加できます。欲しい情報（例: systemd ユニットテンプレート、Docker 化手順、CI 設定例）があれば教えてください。