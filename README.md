# KabuSys — 日本株自動売買システム (README)

以下はこのコードベースの概要、機能、セットアップ手順、基本的な使い方、主要ディレクトリ構成の説明です。

注意: 実行前に .env を正しく作成し、必須の環境変数を設定してください（J-Quants / kabuステーション等）。本リポジトリは実行環境に応じて実際に発注を行うため、本番環境 (KABUSYS_ENV=live) での使用は十分に理解した上で行ってください。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買フレームワークです。  
主な役割は以下です。
- 戦略のリサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- Execution Engine による発注管理（本番 / ペーパートレード切替対応）
- 監視（システム状態・注文監視・リスク監視）と Kill Switch
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、DuckDB を分析用 DB、SQLite を運用・監視ログに利用し、外部 API 呼び出しは環境変数で制御します。ペーパートレード時は本番 DB と完全に分離します。

---

## 主な機能一覧
- Execution
  - ExecutionEngine（発注・注文管理・リスク制御・リコンシリエーション）
  - BrokerClientFactory により本番/モックブローカーを切替
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存チェック
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限チェック、KillSwitch 連携
  - MonitoringEngine：ポーリングループの実行とアラート通知連携
- Portfolio
  - 候補選定、等重・スコア重み付け、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース / 等比 / スコアベース）
- Research
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計要約
- AI
  - ニュース NLP（OpenAI を使ったセンチメントスコアリング）
  - レジーム判定（ETF MA とマクロセンチメントの融合）
- ツール
  - config_setup: .env を対話式に作成/更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から検証レポート出力
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - DB 初期化・マイグレーション（monitoring_db）

---

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（1/0、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

詳しいキー名・説明は src/kabusys/config.py および config_setup の ITEMS を参照してください。

---

## セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨 Python 3.10+（duckdb, psutil 等を想定）
2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存ライブラリインストール
   - pip install -U pip
   - 必須/推奨パッケージの例:
     - duckdb
     - psutil
     - openai (AI 機能使用時)
     - PyYAML (validate_config の YAML 検証を行う場合)
   - 例: pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動: リポジトリ直下に .env を作成し、必要項目を設定
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. DB 初期化
   - 実行時に monitoring DB（SQLite）と DuckDB のテーブルは自動作成されます（monitoring_db.init_monitoring_db 等）
   - data/ ディレクトリが必要な場合は作成されます（プロセスが自動作成することもありますが手動作成を推奨）

---

## 基本的な使い方（コマンド）
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine（トレード実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します
  - 停止: プロセスを止める、または data/stop_requested.flag を作成して安全に停止できます
  - Execution は起動時に data/execution.pid に PID を書きます
- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に変更可能（デフォルト 60）
  - 停止: data/stop_requested.flag を作成するとループが終了します
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パス指定可能
- AI 機能（例）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 上の raw_news 等から書き込み

---

## 運用上の注意
- KABUSYS_ENV=live に設定すると実際に発注が行われます。LINE 通知設定や Kill Switch の挙動を十分確認してください。
- Kill Switch はデータ/kill.flag（Settings.kill_flag_path）を使って ExecutionEngine に停止シグナルを送ります。KillSwitch はドローダウンやポジション上限超過で自動的に書き込みます。
- run_monitoring は常に「本番」用の sqlite_path を参照して監視ログを記録します（monitoring は環境にかかわらず production sqlite を使用する設計）。
- ペーパートレードは paper_sqlite_path (data/paper_trading.db) に書き込まれ、本番 DB と分離されます。
- OpenAI など外部 API キーは環境変数で管理してください（OPENAI_API_KEY）。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - (ExecutionEngine, OrderManager, BrokerClientFactory, OrderRepository, Reconciler, RiskManager など)
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化層
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限
    - kill_switch.py         — Kill Switch 実装
    - alert_manager.py       — （アラート通知管理）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・投資制限
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し & スコアリング）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                    — 実行時生成される DB / フラグファイル等を格納（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db, data/kill.flag, data/execution.pid）

- config/
  - system_config.yaml (例)
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （validate_config.py により存在確認 / YAML パース検証）

---

## よく使うファイル・フラグ
- data/stop_requested.flag — run_monitoring / run_execution が監視して停止に使うフラグ
- data/execution.pid       — ExecutionEngine が生存確認用に書く PID ファイル
- data/kill.flag           — KillSwitch が書き込む Execution 停止フラグ（Settings.kill_flag_path）
- data/monitoring.db       — 監視用 SQLite（monitoring_db 初期化で作成）
- data/paper_trading.db    — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- data/kabusys.duckdb      — 分析用 DuckDB ファイル（DuckDB_PATH）

---

## トラブルシューティング / 開発メモ
- validate_config を使って起動前に設定漏れを検出してください。
- OpenAI など外部 API 呼び出しはレート制限や一時エラーを考慮してリトライ実装がありますが、API キー管理は厳重にしてください。
- ログレベルは環境変数 LOG_LEVEL で調整できます。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動で .env を読み込まないようにできます。
- DuckDB のバージョンや executemany の挙動（空リストに対する制約）に依存する実装箇所があるため、DuckDB の互換性に注意してください（monitoring / ai の書き込み部分参照）。

---

この README はコードベースの主要な使用方法と構成をまとめたものです。各モジュールの詳細な仕様や追加手順は、ソース内の docstring およびコメントに記載されています。運用前には必ず validate_config を実行し、KABUSYS_ENV に応じた設定を確認してください。