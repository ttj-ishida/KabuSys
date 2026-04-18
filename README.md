# KabuSys

日本株自動売買（バックテスト / ペーパートレード / 実行支援）用ライブラリ / 小規模プラットフォーム

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - ExecutionEngine（発注エンジン）起動
  - Monitoring（監視）起動
  - Paper Trading 検証レポート生成
  - 主要な実行時設定（環境変数）
- ディレクトリ構成（主要ファイル説明）
- 依存関係・補足

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するための小規模モジュール群です。  
以下のような責務を持つモジュール群を提供します。

- 実行エンジン（ExecutionEngine）: ブローカーとの発注、注文管理、リスク管理、再整合（reconcile）など（Engine の本体は別モジュールに実装）。
- 監視（Monitoring）: システムリソース・データ鮮度・注文状況・ドローダウン等を定期的に監視し、ログやアラート、Kill Switch を管理。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限など。
- リサーチ / ファクター計算: DuckDB 上の価格データからモメンタム・ボラティリティ・バリュー等のファクターを算出。
- AI 統合: OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価や市場レジーム推定（オプション）。
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定等。

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に行う」「DB 書き込みは冪等に」などの注意が払われています。

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話式で生成 / 更新）
- 設定検証 CLI（.env / config/*.yaml のチェック、--strict モード）
- ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 分離）
- Monitoring 起動スクリプト（ポーリング監視、停止フラグ対応）
- 監視 DB 層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard の管理
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / AlertManager（監視ロジック）
- Portfolio construction（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- Research モジュール（DuckDB を用いたファクター計算、IC 計算等）
- AI 関連モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を使用
- Paper Trading 検証レポート生成ツール

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成して有効化（推奨）
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows
     ```
3. 依存パッケージをインストール（最低限）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config YAML 検証を使う場合）
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. デフォルトのデータディレクトリとログディレクトリは起動時に自動作成されます（data/, logs/）。
5. 初回は環境変数を設定する（.env を作る）。簡単には次の「環境設定ウィザード」を使ってください。

注意:
- 自動的な .env 読み込みはプロジェクトルート（.git または pyproject.toml のある場所）を検出して行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

以下は主要な CLI モジュールの使い方例です。各コマンドはプロジェクトルートで実行してください。

### 環境設定ウィザード（.env を作成/更新）
対話式で .env を生成します。
```bash
python -m kabusys.config_setup
# または保存先を指定
python -m kabusys.config_setup --env-file /path/to/.env
```
ウィザードで入力した値は .env に書き込まれます（.env は Git にコミットしないでください）。

### 設定検証
.env や config/*.yaml の簡易チェックを実行できます。
```bash
python -m kabusys.validate_config
# 警告もエラー扱いにする（CI などで）
python -m kabusys.validate_config --strict
```

### ExecutionEngine（発注エンジン）起動
ExecutionEngine を起動します。`KABUSYS_ENV` が `paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します。
```bash
python -m kabusys.run_execution
```
起動時、プロセス優先度を "high" に設定し、停止用フラグ（data/stop_requested.flag）が検知されていれば起動を中止します。起動中に stop flag を書くとエンジンの停止シグナルになります。

- 実行 PID ファイル: `data/execution.pid`（デフォルト）
- Paper Trading DB: `data/paper_trading.db`（KABUSYS_ENV=paper_trading の場合）

### Monitoring（監視）起動
監視モジュールをポーリングで実行します。
```bash
python -m kabusys.run_monitoring
```
- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60秒）
- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境に依らず）
- 停止フラグ: `data/stop_requested.flag` を配置すると監視ループが終了します

### Paper Trading 検証レポート生成
ペーパートレード DB のデータから検証レポートを生成します。
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB を使う場合:
python -m kabusys.tools.paper_verification_report
# DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

### 主要な実行時設定（環境変数）
主な環境変数の一覧と挙動（一部）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
  - paper_trading: 発注はモッククライアント、DB は paper_trading_db を使用
  - live: 本番挙動（注意して設定してください）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading のモック約定挙動: instant|partial|never|reject, デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR（ログ保存先、デフォルト logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
- OPENAI_API_KEY（AI 機能を使用する場合に必要）
- KILL_FLAG_CLEAR_ON_START（実行時に kill.flag を自動クリアするか。0/1）

各値は .env や環境変数で指定できます。Settings クラスは自動で .env の読み込みを行います（ただし OS 環境変数は優先され .env.local が .env を上書きします）。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

以下は src/kabusys 以下の主要なファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）
- src/kabusys/config.py
  - Settings クラス（環境変数/.env の読み込み、値の検証、デフォルト値）
  - 自動 .env 読み込み（.env, .env.local）を実装
- src/kabusys/config_setup.py
  - 対話式ウィザードで .env を生成/更新
- src/kabusys/validate_config.py
  - 起動前チェック CLI（必須環境変数、ファイル存在、YAML パース検証等）
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 分離、PID/stop flag 管理）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- src/kabusys/monitoring/
  - monitoring_db.py: SQLite スキーマ作成・永続化ロジック（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システムリソース・データ鮮度・プロセス生存監視
  - risk_monitor.py: ドローダウン・ポジション上限監視（ダッシュボード参照、リスクログ記録）
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止する仕組み
  - monitoring_engine.py: 複数 Monitor を束ねる実行ループ / run_once
  - trade_monitor.py, alert_manager.py 等（注文関連監視・アラート管理：実装あり）
- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定、等重/スコア重み計算
  - position_sizing.py: 株数算出、単元丸め、aggregate cap のスケーリング
  - risk_adjustment.py: セクター上限適用、レジーム乗数
- src/kabusys/research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
  - feature_exploration.py: 将来リターン、IC 計算、統計サマリー
- src/kabusys/ai/
  - news_nlp.py: raw_news を LLM（OpenAI）でスコアリングして ai_scores に書き込む
  - regime_detector.py: ETF（1321）MA とマクロニュースの LLM スコアを合成して日次レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading DB から検証レポートを生成
- src/kabusys/utils/
  - logging_setup.py: ルートロガーの Stream + TimedRotatingFileHandler（logs/<app>.log）
  - process_priority.py: Windows/Linux を吸収するプロセス優先度 / CPU affinity 設定ユーティリティ
- data/
  - （実行時に生成される）monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid 等
- logs/
  - 日次ローテートされたログファイルが保存されます（既定: 30 日分保持）

（上に挙げたファイルは主要部分で、実際のリポジトリにはさらに細かいモジュールが含まれます）

---

## 依存関係・補足

- 必須 / 推奨ライブラリ（機能に応じて）:
  - duckdb — リサーチ / AI / データ処理で使用
  - psutil — システム監視・プロセス優先度操作
  - openai — ニュース NLP / レジーム判定（外部 API キーが必要）
  - PyYAML — config/*.yaml の検証（validate_config でオプション）
- データベース:
  - SQLite（監視・発注ログ）: デフォルト `data/monitoring.db`
  - Paper Trading 用 SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading の場合に使用）
  - DuckDB（分析用）: `data/kabusys.duckdb`
- ログ:
  - デフォルト `logs/` にアプリケーション毎のファイル（例: logs/execution.log, logs/monitoring.log）が日次ローテーションで保存されます（30 日保持）。
- 安全上の注意:
  - `.env` は機密情報（API トークン・パスワード）を含むため絶対にリポジトリにコミットしないでください。
  - 本番（KABUSYS_ENV=live）での起動時は設定とアラート先（LINE 等）を必ず確認してください。validate_config の警告は厳重に扱ってください。
- キルスイッチ / 停止:
  - 実行中のエンジン / 監視はプロジェクト内の flag ファイル（data/kill.flag, data/stop_requested.flag）で制御できます。kill.flag は ExecutionEngine 側で読み取られ停止を促す仕組みです。

---

問題や拡張、実運用向けの注意点があれば README に追記していくことを推奨します。必要であれば、各モジュールの API ドキュメントや実行例（docker-compose / systemd ユニット例）等も追加できます。