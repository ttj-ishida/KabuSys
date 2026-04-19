# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）

この README はリポジトリ内の主要モジュールを元に作成した日本語ドキュメントです。開発用に整理された構成・ユーティリティや、監視・ペーパートレード・AI を組み合わせたワークフローを含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- 市場データ（DuckDB / prices_daily 等）を用いたファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイズ決定ロジック（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理、リスク管理（execution）
- システム/注文の監視と Kill Switch（monitoring）
- ニュースを使った NLP（OpenAI）ベースのセンチメント評価・レジーム判定（ai）
- 開発用ツール（環境ウィザード、設定検証、レポート生成）

設定は環境変数（またはリポジトリルートの `.env` / `.env.local`）で行います。ログは `logs/` に出力され、日次ローテーションされます。

---

## 主な機能一覧

- 環境設定ウィザード（対話式で `.env` を生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env や config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、データは `data/paper_trading.db` に記録（本番 DB と分離）
- 監視モード起動スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用
- Kill Switch: リスク条件（ドローダウン超過・ポジション上限等）で `data/kill.flag` を書き込み、ExecutionEngine を停止
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- AI ツール:
  - ニュースの銘柄別センチメントスコア -> DuckDB の `ai_scores` テーブルへ書き込み（OpenAI 必須）
  - 市場レジーム判定（ma200 + マクロセンチメントの合成）
- 研究モジュール（DuckDB を用いたファクター計算、将来リターン、IC 計算 等）
- ポートフォリオ構築モジュール（候補選定、重み計算、リスク制約、ポジションサイズ計算）

---

## 必要なライブラリ / 前提

主に次が必要になります（環境や利用機能により変わります）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（`validate_config` で YAML を検証したい場合に推奨）

インストール例:
pip install duckdb psutil openai PyYAML

（requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成してアクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数を準備
   - 対話式ウィザードを推奨: python -m kabusys.config_setup
   - 手動の場合はリポジトリルートに `.env` を作成（絶対に Git にコミットしないでください）
     - 例（最小）:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（任意）:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには --strict を付ける

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

注意: Settings モジュールはリポジトリルートを .git または pyproject.toml から自動検出して `.env` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（起動例）

- ExecutionEngine（デーモン/セッション実行）
  - 基本起動:
    python -m kabusys.run_execution
  - ペーパートレードで起動:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH` (デフォルト: data/paper_trading.db) が使用され、本番の `SQLITE_PATH` と分離されます。
  - 停止:
    - 実行中に `data/stop_requested.flag` を作成すると実行スレッドが検出して停止します（run_execution/run_monitoring 両方で使用）。
    - Kill Switch による停止は `data/kill.flag` を作成します（KillSwitch が自動的に書き込みます）。

- Monitoring（単体の監視プロセス）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒。1 未満や 0 を指定すると警告してデフォルトにフォールバックします。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず `Settings.sqlite_path`（本番監視 DB）を使用します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY もしくは関数引数で渡す）。
  - 例（モジュール関数呼び出し）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
  - 実行中のスクリプトは自動で LLM を呼び出すため、API 使用量に注意してください。
  - エラーや API の一時的な失敗は指数バックオフでリトライし、最終的にフォールバック動作（スコア=0 等）を取る設計です。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト `INFO`
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視用 SQLite（monitoring.db）デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading.db）デフォルト `data/paper_trading.db`
- PAPER_FILL_MODE: paper_trading 時の成行・約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）。デフォルト 60
- OPENAI_API_KEY: OpenAI を用いる AI 機能の API キー
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

重要: `.env` は機密情報を含むため絶対にリポジトリにコミットしないでください。

---

## ログとローテーション

- ログはデフォルト `logs/` に出力され、アプリ名ごとに `logs/<app_name>.log`（例: execution.log, monitoring.log）として日次ローテーション（30 日保持）されます。
- `kabusys.utils.logging_setup.setup_logging` を全起動スクリプトが利用して一貫したログ出力を行います。
- ログディレクトリ作成に失敗した場合はファイルハンドラを無効にして stdout のみで継続します。

---

## Kill Switch / 停止フラグ

- Kill Switch:
  - 設定されたリスク条件を満たすと `data/kill.flag` が作成され、ExecutionEngine の停止トリガーとなります（KillSwitch が書き込み）。
  - `KILL_FLAG_CLEAR_ON_START` が `1` の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では `0` 推奨）。
- stop_requested.flag:
  - `data/stop_requested.flag` は運用者が作成すると run_execution / run_monitoring が検知して優雅に終了します。
- PID ファイル:
  - 実行エンジンは `data/execution.pid`（Settings.pid_file_path）を使います。

---

## 開発用ユーティリティ

- config_setup.py: 対話式に `.env` を生成・更新するウィザード
  - python -m kabusys.config_setup
- validate_config.py: 起動前に設定やファイルの整合性をチェック
  - python -m kabusys.validate_config [--strict]
- tools/paper_verification_report.py: ペーパートレードの検証レポートを生成

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 相対の主要ファイル・モジュールと簡単な説明です。

- __init__.py
  - パッケージ定義、バージョン情報
- config.py
  - Settings クラス（環境変数読み込み、自動 .env ロード、バリデーション）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 対応）
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py: 監視用 SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （注文関連の監視：滞留・約定異常など）
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: Kill Switch 実装（kill.flag 書き込み）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （通知管理）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注ロジック、ブローカ抽象、リスク管理）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - （候補選定・重み計算・ポジションサイズ算出・セクター制限）
- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB 使用）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py: ニュースを LLM でスコア化して ai_scores に書込む
  - regime_detector.py: ma200 + マクロセンチメントで市場レジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

（上記は主要ファイルの抜粋です。完全なファイル一覧はリポジトリを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- .env に機密情報（API トークン / パスワード）を保存する場合は、必ず .gitignore に登録してリポジトリへコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。
- AI 機能を使う際は OpenAI の利用料に注意してください。開発・テストではモック（または少数のサンプル）で検証することを推奨します。
- run_monitoring は監視 DB（Settings.sqlite_path）を環境にかかわらず参照します。監視データの隔離が必要な場合は DB パス設定に注意してください。
- プロセス優先度設定（psutil 使用）は OS に依存し、権限がない場合は警告を出してスキップします。

---

## トラブルシュート（よくある事例）

- PyYAML がないために validate_config で YAML 検証がスキップされる:
  - pip install PyYAML
- DuckDB 接続エラー:
  - duckdb パッケージがインストールされているか、DUCKDB_PATH のディレクトリに書込権限があるか確認してください。
- OpenAI 呼び出しで失敗が多発する:
  - OPENAI_API_KEY が正しいか、API レート制限を超えていないか確認。ネットワークの安定性や SDK バージョンもチェックしてください。

---

必要であれば、この README をベースにさらに詳細な運用手順（systemd / Docker / Docker Compose によるデプロイ例、CI/CD 流れ、テスト手順、SQL スキーマの詳細など）も作成できます。どの情報を優先して追加したいか教えてください。