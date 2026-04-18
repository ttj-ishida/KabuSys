# KabuSys — 日本株自動売買システム

このリポジトリは、ルールベース／リサーチ／ペーパートレード対応の日本株自動売買システムのコア部分です。  
README ではプロジェクト概要、主な機能、セットアップ手順、使い方（起動・ユーティリティ）、およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の要素を持つ自動売買プラットフォームのコアライブラリです。

- 戦略研究（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（ExecutionEngine）とブローカークライアント抽象化（実口座／ペーパー分離）
- モニタリング（システム・注文・リスク監視）と Kill Switch（フラグファイルによる停止）
- AI 補助機能（ニュース NLP による銘柄センチメント、レジーム判定）
- 分析用データベース（DuckDB）および運用ログ（SQLite）

設計方針として、ルックアヘッド（未来情報参照）を避ける、フェイルセーフ（API失敗時の安全なフォールバック）などに配慮しています。

---

## 機能一覧（主要コンポーネント）

- config: 環境変数・`.env` 読み込み、Settings クラス（既定値やバリデーション）
- config_setup: 対話式に `.env` を生成・更新するウィザード
- validate_config: `.env` / config/*.yaml の起動前検証 CLI（`--strict` あり）
- run_execution: ExecutionEngine 起動スクリプト（本番 / paper_trading を分離）
- run_monitoring: SystemMonitor をポーリングする起動スクリプト（停止フラグ対応、MONITOR_POLL_INTERVAL）
- monitoring: system_status / trade_logs / risk_logs / dashboard の永続化と各種モニタ
  - MonitoringDB: SQLite のテーブル初期化・CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: `data/kill.flag` によるエンジン停止シグナルの発行
  - alert_manager（通知発行のハブ、実装はコードベース参照）
- portfolio: 銘柄選定・重み計算・ポジションサイズ決定・セクター制限・レジーム乗数
- research: ファクター計算（momentum/value/volatility）および特徴量解析（forward returns, IC, summary）
- ai:
  - news_nlp: OpenAI を用いた記事ベースの銘柄センチメント算出と ai_scores への書き込み
  - regime_detector: ETF（1321）MA とマクロ記事の LLM センチメントを合成して日次レジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定の検証レポートを生成
- utils:
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化します（例: venv / poetry / pipenv 等）。
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
   - ※requirements.txt がある想定です。DuckDB, psutil, openai, PyYAML（任意）などが必要です。

2. 初期 `.env` を作成（推奨: 対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 対話ウィザードで J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV（development / paper_trading / live）などを設定します。
   - 生成された `.env` は絶対に Git にコミットしないでください。

3. 設定検証を実行
   ```
   python -m kabusys.validate_config
   ```
   - 警告も失敗扱いにする場合は `--strict` を付けて実行します:
     ```
     python -m kabusys.validate_config --strict
     ```

4. 必要に応じてデータディレクトリを作成
   - 既定では `data/` に SQLite / PID / flag 等を格納します。`.env` で上書き可能です。

5. OpenAI 機能を使う場合
   - 環境変数 `OPENAI_API_KEY` を設定してください（ai.news_nlp / regime_detector が必要）。
   - また `PAPER_FILL_MODE`（instant|partial|never|reject）などペーパートレード挙動の設定があります。

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite のパス）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番で危険なのでデフォルト 0 推奨）

---

## 使い方（起動・ユーティリティ）

### 実行エンジン（発注処理）を起動する
- 本番 / 開発 / ペーパートレードを `.env` の `KABUSYS_ENV` で切り替えます。
- 起動:
  ```
  python -m kabusys.run_execution
  ```
  - プロセス優先度を high に設定して起動します。
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db`（または環境変数で指定した専用 DB）に記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動を行いません。

- 停止:
  - `data/stop_requested.flag` を作成すると、実行中のエンジンは検出して終了します（監視・起動スクリプトはこのフラグを監視）。
  - Kill Switch（監視コンポーネントが危険状態を検出して `data/kill.flag` を書き込む）により ExecutionEngine を停止させることもあります。

### 監視ループを起動する
- SystemMonitor をポーリングして各種ログを SQLite に保存します。
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に（KABUSYS_ENV によらず）本番の `sqlite_path` を使用します（監視データは環境に関係なく同一 DB に蓄積されます）。

### 設定ウィザード / 検証
- 対話式で `.env` を生成:
  ```
  python -m kabusys.config_setup
  ```
- 設定チェック:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

### ペーパートレード検証レポート
- ペーパートレード DB を読み取り、検証レポートを標準出力に出力します。
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  - 期間指定:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを直接指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

### AI 機能（ニューススコアリング / レジーム判定）
- news_nlp.score_news と regime_detector.score_regime は DuckDB 接続オブジェクトと日付、必要に応じて API キーを受け取り処理を行います。
- 実行例（スクリプト API 呼び出しの一例）:
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数か、関数引数で渡します。
- 失敗時はフェイルセーフでスコアを 0 相当にフォールバックするなどの実装になっています。

---

## 停止・フラグについて

- stop_requested.flag（data/stop_requested.flag）:
  - 実行スクリプト（run_execution, run_monitoring 等）がポーリングして検出すると安全にシャットダウンします。
- kill.flag（Settings.kill_flag_path, デフォルト: data/kill.flag）:
  - Monitoring の KillSwitch がリスク条件を満たした場合に書き込まれます。ExecutionEngine 起動時にこのフラグが存在する場合は開始しない、または書き込みを検出してエンジンを停止します。
- PID ファイル:
  - Execution 用に `data/execution.pid` を使用します（Settings.pid_file_path で上書き可能）。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリのソースは `src/kabusys` 以下に配置されています。主要なファイル／フォルダを抜粋します。

- src/kabusys/
  - __init__.py                         — パッケージ初期化（バージョン等）
  - config.py                           — Settings / .env 自動読み込みロジック
  - config_setup.py                     — 対話式 .env ウィザード
  - validate_config.py                  — 設定検証 CLI
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py                  — 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py               — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py                  — SQLite テーブル定義・MonitoringDB クラス
    - system_monitor.py                 — システム状態・データ鮮度チェック
    - trade_monitor.py                  — 注文滞留・約定異常監視（コードベース参照）
    - risk_monitor.py                   — ドローダウン・ポジション上限監視
    - kill_switch.py                    — kill.flag の管理
    - monitoring_engine.py              — 各 Monitor をまとめる
    - alert_manager.py                  — アラート通知ハブ（実装参照）
  - execution/
    - execution_engine.py               — ExecutionEngine 実行ロジック（スレッド管理等）
    - broker_factory.py                 — BrokerClient のファクトリ（本番 / mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py              — 候補選出・重み計算
    - position_sizing.py                — 株数決定・上限・丸めロジック
    - risk_adjustment.py                — セクター上限・レジーム乗数
  - research/
    - factor_research.py                — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py            — forward returns, IC, summary
  - ai/
    - news_nlp.py                       — ニュースの LLM による銘柄センチメント算出
    - regime_detector.py                — マーケットレジーム判定（MA + macro sentiment）
  - tools/
    - paper_verification_report.py      — ペーパートレード検証レポート生成ツール

---

## 注意事項 / 運用上のヒント

- 本番での Kill Switch や `KILL_FLAG_CLEAR_ON_START` 設定は慎重に扱ってください（本番では自動クリアを無効推奨）。
- `.env` は秘匿情報を含むため、絶対にリポジトリにコミットしないでください。
- AI 機能（OpenAI）を使う際は API レート制限や費用に注意してください。実装はリトライ・バックオフを行いますが、安全側のデフォルト（失敗時はスコア 0）になっています。
- DuckDB / SQLite のパスは `.env` で上書き可能です。ペーパートレードは DB を分離して記録されます（paper_trading 向け DB）。

---

README はここまでです。必要であれば以下の追加を作成します:
- 開発者向けのローカルテスト手順（ユニットテスト、モックの説明）
- 各モジュール（ExecutionEngine、OrderManager など）の API ドキュメント抜粋
- .env.example のテンプレート（自動生成または明示）