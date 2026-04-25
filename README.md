# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ペーパートレード検証ツール、ファクター計算・リサーチ、AI ベースのニュースセンチメント／レジーム判定などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援する一連のモジュール群です。主な目的は以下です。

- 発注エンジン（実取引 / ペーパートレード対応）
- 実行状況・システム状態の監視とアラート（Kill Switch を含む）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、リスク調整）
- ファクター計算や特徴量探索（DuckDB に保存された市場データを用いる）
- ニュースの NLP によるセンチメント解析（OpenAI API を利用）
- ペーパートレード検証レポート生成ツール

設計方針として、DB など外部状態とのやり取りは明示的に分離し、テスト可能な純粋関数群と I/O 層を分けています。

---

## 主な機能一覧

- Execution
  - 実際のブローカー（kabuステーション）／モックブローカーを切り替えて発注を実行
  - リスク管理（ポジション上限、ドローダウン等）
  - Order 管理・リコンシリエーション
- Monitoring
  - システム資源（CPU/メモリ/ディスク）・プロセス生存・データ鮮度の監視
  - 取引ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch: 条件到達時に停止フラグを書き込み、ExecutionEngine を安全に停止
- Portfolio
  - 銘柄選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム補正
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - ニュースセンチメント（OpenAI）を銘柄ごとにスコア化し ai_scores に格納
  - レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- Tools
  - Paper Trading 検証レポート生成（履歴 DB から指標を集計）

---

## セットアップ手順

想定 Python バージョン: 3.10 以上（PEP 604 の型表記を使用）

1. リポジトリをクローンする
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（少なくとも）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - pyyaml（config 検証で YAML を検証する場合は必須ではないが推奨）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください。）

4. .env の作成
   - 対話形式ウィザードを使う:
     - python -m kabusys.config_setup
   - ウィザードは .env を作成し、機密値（API トークンやパスワード）を入力できます。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

6. データ／ログディレクトリの作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。スクリプトが自動作成することもありますが、権限周りを事前に確認してください。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します。
- JQUANTS_REFRESH_TOKEN:（必須）J-Quants API トークン
- KABU_API_PASSWORD:（必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

（詳しいデフォルト値や追加の設定項目は `kabusys.config.Settings` および config_setup.py を参照してください。）

---

## 使い方

以下は主要な実行例です。いずれもプロジェクトルートから実行してください。

- 環境構築（.env 作成）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視はデフォルトで sqlite_path（monitoring DB）を使用します（環境に依らず本番 sqlite_path を参照する設計）。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 実行中は PID ファイル（data/execution.pid デフォルト）にプロセス ID を書き込みます。
  - 停止は data/stop_requested.flag を作成するとループが検知して終了します（同様に monitoring も stop flag を検知して終了）。

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定可能（指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db）

- AI 関連（ニューススコア / レジーム判定）
  - 必須: OPENAI_API_KEY を設定
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはライブラリ関数なので、DuckDB 接続を取得してスクリプトや定期ジョブから呼び出します。

- 設定検証（CLI）
  - python -m kabusys.validate_config [--strict]

注意:
- Kill Switch（データベースおよびファイルフラグを介した停止判定）について:
  - risk_monitor が閾値を超えた場合に KillSwitch が data/kill.flag を書き込むことがあります。ExecutionEngine はこの kill.flag を検知すると停止や安全措置を行います。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール（CLI）
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄センチメント付与
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       —（取引監視ロジック; ここでは参照元に実装あり）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信管理: LINE 等）
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション管理・発注フロー）
    - broker_factory.py      — ブローカークライアント生成（本番 / モック切替）
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
    - pipeline.py            — データパイプライン（prices_daily などの管理）
    - stats.py               — 正規化ユーティリティ等
  - utils/
    - logging_setup.py       — 統一的なログ初期化（コンソール + 日次ローテートファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ ディレクトリ（デフォルトの DB・PID・フラグファイルを格納）
- logs/ ディレクトリ（ログファイル、日次ローテーション）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では、設定と API キーの扱いに細心の注意を払ってください。validate_config は live の場合に追加警告を出します。
- kill.flag や stop_requested.flag の扱いに慣れておくこと（手動停止 / 自動停止の仕組み）。
- OpenAI の呼び出しには料金が発生します。AI 機能は必須ではありませんが利用時は API キーと課金を確認してください。
- ログディレクトリのパーミッションや DB ファイルのバックアップ方針を決めてください。
- DuckDB / SQLite はローカルファイル DB です。運用スケールや同時書き込み要件によっては運用方針を検討してください。

---

## よく使うコマンドまとめ

- .env 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 監視開始
  - python -m kabusys.run_monitoring
- エンジン起動
  - python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/db

---

必要であれば README に含めるコマンドの具体例（systemd ユニットや docker-compose サンプル、詳細な環境変数一覧、テスト方法、開発用の起動手順など）を追加できます。どの情報をさらに詳しく記載したいか教えてください。