# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）のリポジトリです。  
この README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

重要: README はコードベースの主要点に基づいて作成しています。実行前に `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は次のような機能を持つ自動売買システムの骨格実装です。

- 取引エンジン（ExecutionEngine）を起動して発注・リスク管理を行う（実行スクリプト: run_execution.py）。
- システム監視 / アラート / Kill Switch を行う監視プロセス（run_monitoring.py）とそれを束ねる MonitoringEngine。
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）。
- ファクター計算・研究用モジュール（DuckDB を使ったファクター/リターン計算、IC 計算等）。
- AI を利用したニュースセンチメント評価（OpenAI を使ったニュース NLP）と市場レジーム判定。
- Paper Trading 用ログ出力・検証レポート生成ツール。

設計方針の一部：
- 本番用 DB（監視 DB）は環境に関わらず監視プロセスで同一 sqlite_path を使用します（監視の整合性確保のため）。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離し、`data/paper_trading.db` 等に記録します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行いますが、無効化も可能です。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード切替）。
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを収集。
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成/更新。
  - validate_config.py: .env と config/*.yaml の検証（CLI）。
- モニタリング
  - monitoring_db.py: SQLite による監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）。
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py。
- 取引・実行周り（execution パッケージ）
  - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注・リスク制御）。
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment。
- リサーチ / ファクター
  - research パッケージ: momentum/value/volatility の計算、forward returns、IC、統計サマリー等（DuckDB を利用）。
- AI（OpenAI）連携
  - news_nlp.py: ニュース記事を集約して LLM に送信、銘柄ごとのセンチメントを ai_scores テーブルへ保存。
  - regime_detector.py: ETF (1321) MA200 とマクロニュースで日次レジーム判定。
- ツール
  - tools/paper_verification_report.py: Paper Trading の振る舞い（稼働率・成功率・レイテンシ等）を集計してレポート出力。

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.9+（コードは型ヒント・最近のパッケージを利用）
   - 仮想環境を作成してアクティベートしてください。

2. 必要なパッケージをインストール
   - 例:
     pip install duckdb psutil openai
   - 追加（オプション）:
     - PyYAML（`validate_config.py` の YAML 検証を有効にする場合）
     - その他、実行時に使う Broker API クライアント等（プロジェクト固有）

3. .env ファイルの作成（推奨ワークフロー）
   - 対話型ウィザードで作成:
     python -m kabusys.config_setup
   - 生成後、設定を検証:
     python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. 主要な環境変数（必須／重要）
   - JQUANTS_REFRESH_TOKEN （必須: J-Quants API）
   - KABU_API_PASSWORD （必須: kabuステーション API）
   - OPENAI_API_KEY （AI 機能を使う際に必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒単位でオーバーライド可能、デフォルト: 60）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
   - KILL_FLAG_CLEAR_ON_START（本番で Kill Switch を自動クリアするか、0 推奨）

   .env の自動読み込みはプロジェクトルートを検出して行いますが、テスト時等に無効化するには:
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ログディレクトリ
   - デフォルトでは `logs/` 配下にアプリ名ごとの日次ローテートログが作成されます（TimedRotatingFileHandler）。
   - 環境変数 LOG_DIR で変更可能。

---

## 使い方（起動例）

- 設定ウィザード（対話式 .env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に `settings.sqlite_path`（監視用の sqlite）を用います（環境に依らず本番パスを使用する仕様）。

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - プロセス優先度設定・PID ファイル書き出し等の処理を行います。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - オプション: --db PATH で DB を指定可能

- AI 機能を使う（ニューススコアリング / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定してください。
  - 関数レベルで API キーを渡せる設計（テスト向けにモック可能）。

- 停止 / Kill Switch
  - 監視/実行はフラグファイル（data/stop_requested.flag および data/kill.flag）で終了・停止判定を行います。
  - KillSwitch（監視モジュール）は drawdown やポジション上限超過時に data/kill.flag を書き込み ExecutionEngine 停止を促します。

---

## 主要スクリプトと CLI の要約

- python -m kabusys.config_setup
  - .env を対話式に生成/更新するウィザード

- python -m kabusys.validate_config [--strict]
  - 設定検証 CLI

- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを開始

- python -m kabusys.run_execution
  - ExecutionEngine を起動して発注セッションを実行

- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - Paper Trading の検証レポートを生成

---

## 実行上の注意点 / 運用メモ

- 監視（Monitoring）は sqlite のパスを本番設定で参照するため、運用時は .env の SQLITE_PATH を適切に設定してください。
- Paper Trading は本番 DB と区別して動作するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI など外部 API 呼び出しはリトライ・フォールバック処理を備えていますが、API キーが未設定だと例外になる箇所があります（事前に環境変数をセットしてください）。
- ログは標準出力（stdout）およびファイルに出ます。ログディレクトリの作成に失敗した場合はコンソールのみで動作します。
- process priority / CPU affinity の設定は psutil を使用し、権限がない環境では警告を出してスキップします。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml）を基準に探索します。ルートが見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - __version__ (package version)
  - config.py              — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py     — logging 設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（schema／Migration）
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — 発注/約定監視（参照のみ、詳細実装あり）
    - risk_monitor.py      — ドローダウン・ポジション数監視
    - kill_switch.py       — Kill Switch（flag ファイル）
    - alert_manager.py     — （アラート送信管理）
  - execution/
    - execution_engine.py  — ExecutionEngine（起動/セッション管理）
    - broker_factory.py    — Broker クライアントファクトリ（Mock/実ブローカ切替）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py   — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py
  - ai/
    - news_nlp.py          — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py

（上記に掲載していない補助モジュール、データパイプライン、ストラテジー実装、データマスタ等のファイルも存在します）

---

## サンプル .env（最小例）

以下は .env に書く主要項目の一例です（機密値はプレースホルダを置き換えてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-xxxx...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0

---

## トラブルシューティング

- .env の自動ロードが期待通り動作しない場合:
  - リポジトリがプロジェクトルート（.git または pyproject.toml）を検出できているかを確認
  - 自動ロードを無効化して手動で環境変数を設定するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI API 呼び出しで失敗が多い場合:
  - OPENAI_API_KEY の有効性を確認、レート制限やネットワーク問題の可能性を確認
  - ニュース NLP / レジーム判定はリトライとフォールバック（0.0）を行いますが、ログで詳細を確認してください

- ログファイルが生成されない:
  - logs/ ディレクトリに書き込み権限があるか確認
  - LOG_DIR 環境変数で別ディレクトリを指定可能

---

必要があれば、README をさらに拡張して以下の内容を追加できます：
- systemd / Supervisor 用のサービスユニット例
- CI / テスト実行手順（ユニットテストの例）
- データベーススキーマ詳細（テーブル設計）
- 実行フロー図（Monitoring ↔ Execution ↔ Kill Switch）

追加で反映したい項目があれば教えてください。