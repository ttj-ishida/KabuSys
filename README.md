# KabuSys

注意: これはリポジトリ内のソースコードに基づく README です。プロジェクト全体の概要・セットアップ・使用方法・ディレクトリ構成を日本語でまとめています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / 研究基盤を目的とした Python パッケージです。主な目的は以下です。

- 自動発注エンジン（ExecutionEngine）
- 実行・監視基盤（Monitoring）
- ポートフォリオ構築（選定・配分・ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB ベース）
- AI を用いたニュースセンチメント評価（OpenAI API）
- ペーパートレード用検証ツールおよびレポート生成

設計方針としては「本番とペーパートレードの分離」「ルックアヘッドバイアスへの配慮」「フェイルセーフ（API失敗時のフォールバック）」などが盛り込まれています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じてペーパートレード／本番切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup.py: 対話式で .env を作成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
  - Settings クラス: 環境変数経由で構成値を取得
- 監視
  - monitoring/monitoring_db.py: SQLite に対する永続化レイヤ
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py: 個別監視ロジック
  - monitoring/monitoring_engine.py: 各モニタを束ねたポーリング実行
  - monitoring/kill_switch.py: 条件に応じた kill.flag 書き込み（Execution 停止シグナル）
- 発注・実行（概要）
  - execution/*.py: Broker クライアントの抽象化、OrderManager、RiskManager、ExecutionEngine 等（本 README は実行部分の詳細実装を含みません）
  - paper_trading 環境では MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）に記録
- ポートフォリオ構築（pure functions）
  - portfolio/: 候補選定、重み計算、セクター制限、ポジションサイズ計算（単元丸め、利用可能現金のスケーリング等）
- 研究・ファクター
  - research/: momentum/volatility/value 等のファクター計算、IC 計算、特徴量統計
  - DuckDB 接続を受け取り SQL / Python で完結
- AI
  - ai/news_nlp.py: raw_news を OpenAI でスコアリングして ai_scores に保存（バッチ・リトライ・検証ロジックあり）
  - ai/regime_detector.py: ETF の MA200 と LLM によるマクロセンチメントを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 前提要件（例）

- Python 3.9+
- SQLite（標準ライブラリ）
- 外部ライブラリ（主に; 実際は requirements.txt を参照してください）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）

例（手早く必要パッケージをインストールする）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開

2. Python 環境の準備（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt  # もし requirements.txt がある場合
   ```

3. 必要なパッケージがない場合は個別にインストール（上記参照）。

4. 対話式ウィザードで .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   - このウィザードは `.env`（デフォルトはプロジェクトルート）を対話形式で生成します。
   - 生成された `.env` は絶対に Git にコミットしないでください（トークン・パスワードを含む）。

5. 設定検証（必須環境変数や config/*.yaml をチェック）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリやログディレクトリの準備
   - ログはデフォルトで `logs/` に書き込まれます（LOG_DIR 環境変数で上書き可）。
   - データベースはデフォルトで `data/kabusys.duckdb`（DuckDB） と `data/monitoring.db`（SQLite）を使用します。必要に応じて parent ディレクトリを作成するか、環境変数で別パスを設定してください。

---

## 環境変数（主なもの）

必須（アプリケーション起動前に設定するか .env に記載）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意／上書き可能な値:
- KABUSYS_ENV — 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（ai 関連で必要）
- PAPER_FILL_MODE — ペーパートレード時の注文執行モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring.py のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 本番環境での kill.flag 自動クリア（0 が推奨）

設定自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先されます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要コマンド）

1. ExecutionEngine（発注エンジン）起動
   - 本番／開発／ペーパーは KABUSYS_ENV に依存します。
   - ペーパートレード時は MockBrokerClient を使用し `data/paper_trading.db` に記録されます。
   ```bash
   # 環境変数で切替例
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   - 停止: プロセスに Ctrl+C、またはプロジェクトルートの `data/stop_requested.flag` を作成すると実行スレッドは安全に停止します。
   - 実行時は PID ファイル（デフォルト `data/execution.pid`）が設定されます。

2. Monitoring 起動
   ```bash
   # ポーリング間隔を環境変数で上書き（秒）
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```
   - 監視ループは `MONITOR_POLL_INTERVAL` の秒数で SystemMonitor を実行します（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を常に使用してログを残します（環境にかかわらず）。
   - 停止: `data/stop_requested.flag` を作成するとループを抜けます。

3. 設定ウィザード・検証
   ```bash
   python -m kabusys.config_setup
   python -m kabusys.validate_config
   ```

4. Paper Trading 検証レポート（ツール）
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パスを指定する場合:
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

5. AI 関連（ライブラリ関数）
   - news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、内部で OpenAI を呼び出します。API キーは引数または環境変数 OPENAI_API_KEY で指定してください。

---

## 停止・Kill Switch に関して

- 強制停止の指示（ExecutionEngine に停止を指示する監視側のスイッチ）は 2 種類あります。
  - stop_requested.flag (data/stop_requested.flag): 実行プロセス（run_execution/run_monitoring）がこのファイルを検出すると優雅に停止します。運用者が直接作成して手動停止できます。
  - kill.flag (data/kill.flag): Monitoring の KillSwitch（risk 条件など）が書き込むことで ExecutionEngine に停止指示を出します。KillSwitch はリスクイベント（ドローダウン超過等）が発生した際に書き込みます。
- kill.flag は既に存在する場合は書き直さない（冪等）。必要であれば手動で削除してください。

---

## ロギング

- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます（30 日分保持）。
- `setup_logging(app_name="...")` がアプリケーション開始時に呼ばれ、コンソール（stdout）とファイルハンドラを統一的に設定します。
- 環境変数 LOG_DIR でログディレクトリ変更、LOG_LEVEL でログレベル変更が可能です。

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）で主要なファイル・ディレクトリの一覧と役割の簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数の読み取り・自動ロード）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — 共通ロギング設定
    - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注・約定ログの監視（実装参照）
    - risk_monitor.py — ドローダウン監視等
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — 通知管理（LINE 連携等。実装参照）
  - execution/  — 発注エンジンの実装（BrokerFactory, ExecutionEngine 等）
  - portfolio/  — ポートフォリオ構築ロジック（builder, position_sizing, risk_adjustment）
  - research/   — ファクター計算・特徴量探索（DuckDB を利用）
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール

（実際のリポジトリにある全ファイルは上記よりさらに多数存在します。ここでは主要なものを抜粋しています。）

---

## 開発・運用上の注意点

- .env に認証情報（トークン・パスワード）を保存する場合は厳重に管理し、Git にコミットしないこと。
- KABUSYS_ENV が `live` のときは設定ミスが重大な損失に繋がるため、validate_config の警告を必ず確認してください。
- AI 関連処理は OpenAI の利用料金が発生します。バッチサイズや記事文字数制限などのハードリミットがコード内に設定されていますが、運用前にコスト試算を行ってください。
- DuckDB / SQLite のパスは環境変数で変更可能です。ペーパートレードは本番 DB と分離するように設計されています（PAPER_TRADING_SQLITE_PATH）。
- システム監視は psutil を使用しています。権限や OS によって優先度設定や CPU affinity の適用が失敗することがあります（ログに警告が出力されます）。

---

## 付録: よく使うコマンドまとめ

- 環境ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含めるサンプル .env のテンプレートや、実際の ExecutionEngine / Broker 接続方法の詳細、各モジュールの API ドキュメント（関数引数・返り値の詳細）を追加で作成します。どの部分を重点的に拡充するか教えてください。