# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
本リポジトリは以下の主要機能を持ち、ローカル開発／ペーパートレード／本番の各モードで動作します。

- システム監視（監視ログ・アラート・Kill Switch）
- 注文実行エンジン（本番／ペーパートレードの切替）
- ポートフォリオ構築（シグナル選定、重み付け、ポジションサイズ）
- リサーチ機能（ファクター計算・IC計算など）
- ニュース NLP（OpenAI を使ったセンチメント評価）
- 各種ユーティリティ（設定ウィザード・設定検証・ログ設定など）
- ペーパートレードの検証レポート生成ツール

---

## 主な機能（抜粋）

- Settings（環境変数/.env の読み込み・検証）
- config_setup: 対話式 `.env` 作成ウィザード
- validate_config: `.env` と `config/*.yaml` の起動前検証 CLI
- run_execution: ExecutionEngine を起動（KABUSYS_ENV により Paper/Live 切替）
  - paper_trading では MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- run_monitoring: SystemMonitor のポーリングループを起動（監視ログを保存）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- monitoring モジュール: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニューススコアリング・市場レジーム判定
- portfolio モジュール: 候補選定、重み計算、ポジションサイジング、セクター制限
- tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 前提（Prerequisites）

- Python 3.10+
- 必要な Python パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（`validate_config` の YAML 検証を有効にする場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- （Windows/Linux いずれも対応。プロセス優先度設定には psutil が使用されます）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動します。

2. Python 仮想環境を作成・有効化して依存をインストールします（上記参照）。

3. .env の作成 — 対話式ウィザードを推奨:
```
python -m kabusys.config_setup
```
ウィザードで入力した内容はプロジェクトルートの `.env` に保存されます。`.env` は決して Git にコミットしないでください。

4. 設定検証（起動前チェック）:
```
python -m kabusys.validate_config
# 警告も厳密にチェックする場合:
python -m kabusys.validate_config --strict
```

5. 必要に応じて `data/` ディレクトリや `logs/` ディレクトリの権限や配置を確認してください。`setup_logging` は起動時にログディレクトリを作成しますが、権限によって失敗することがあります。

---

## 環境変数（重要項目）

主な必須・重要な環境変数（.env で設定）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- KABUSYS_ENV — 実行モード: development / paper_trading / live （デフォルト: development）
- OPENAI_API_KEY — OpenAI を使用する機能で必要
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading.db、paper_trading モード時に使用）
- LOG_LEVEL — ログレベル（例: INFO）

監視・動作に関する挙動を変える環境変数例:

- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0。production では 0 を推奨）

設定ウィザードが生成する `.env` の例（抜粋）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動コマンド例）

- 設定ウィザード:
```
python -m kabusys.config_setup
```

- 設定検証:
```
python -m kabusys.validate_config
```

- ExecutionEngine 起動（注文エンジン）:
```
python -m kabusys.run_execution
```
注意:
- KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録します（本番 DB と完全分離）。
- 起動時にプロセス優先度を「high」に変更します（可能な範囲で）。

- Monitoring 起動:
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。

- ペーパートレード検証レポート:
```
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 関連（ニュース NLP / レジーム判定）:
  - 関数経由で呼び出す:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - いずれも OPENAI_API_KEY の設定が必要（api_key 引数でも可）。

---

## 停止・Kill Switch の取り扱い

- 優雅な停止:
  - プロジェクトルートの data/stop_requested.flag ファイルが存在すると、run_monitoring / run_execution のループは検知して終了します。手動で停止させたい場合はこのファイルを作成します。
  - 例: touch data/stop_requested.flag

- Kill Switch:
  - リスク条件（ドローダウン超過やポジション上限超過）を満たすと monitoring 側の KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で kill.flag をクリアします（本番では 0 推奨）。

---

## ロギング

- setup_logging により stdout への StreamHandler と日次ローテートされたファイルハンドラ（logs/<app_name>.log）を設定します。
- デフォルトログディレクトリ: logs/
- ログレベルは `LOG_LEVEL` 環境変数か、setup_logging の引数で制御可能。

---

## 主要なディレクトリ構成（src/kabusys の概観）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、.env 自動ロード
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — ログの統一設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （発注関連の監視・検出）※コードベースに存在
    - kill_switch.py — kill.flag の作成 / 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （アラート送信管理）※コードベースに存在
  - execution/ (発注エンジン関連: BrokerFactory, ExecutionEngine, OrderManager, RiskManager 等)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 株数決定・スケールダウンロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py — ニュース集合を OpenAI に送り銘柄ごとのセンチメントを生成
    - regime_detector.py — ma200 とマクロセンチメントを合成してレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - data/ — 実行時生成されるファイル群（DB、pid、flag など）を想定（リポジトリに含めない）

（補足）実際のリポジトリではさらに細かい実装ファイルやマスタなどが存在する想定です。ここには主要なファイル群を抜粋しています。

---

## 開発・運用上の注意

- .env は機密情報を含むため Git 管理しないでください（config_setup でも明言）。
- KABUSYS_ENV は live にすると実際の発注が行われます。本番環境では設定・権限を慎重に確認してください（validate_config は live 時に幾つかの警告を出します）。
- openai を用いる機能は API コストがかかります。API キー管理とコール頻度に注意してください。
- DuckDB・SQLite のファイルパスは設定で指定できます。特にペーパートレード用 DB は本番 DB と分離してください。
- Logging・PID ファイル・stop/kill フラグなどは OS のサービス管理（systemd や supervisor など）と組み合わせることを推奨します。

---

もし README に追記して欲しい内容（例: systemd ユニットのサンプル、具体的な .env.example、運用手順など）があれば教えてください。必要に応じてサンプルやテンプレートを作成します。