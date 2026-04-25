# KabuSys

日本株向け自動売買プラットフォーム（読み取り専用のリサーチ / ポートフォリオ構築、発注エンジン、監視、AI ニューススコアリングなどを含むモジュール群）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール化された自動売買システムです。

- 発注実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視サブシステム（Monitoring） — システム状態・取引ロギング・Kill Switch 等
- ポートフォリオ構築（候補選定、重み付け、株数計算、セクター制約など）
- リサーチ（ファクター計算、特徴量探索、IC 計測など） — DuckDB を利用した分析
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を活用
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- 運用ツール（Paper Trading 検証レポート生成など）

設計方針として、DB（SQLite / DuckDB）を用いた永続化、環境変数駆動の設定、モジュールごとの責務分離（ビジネスロジックと永続化層の分離）を採用しています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレードモード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し、paper_trading.db に記録（本番 DB と分離）
  - Risk Manager（ポジション上限・ドローダウン等）

- Monitoring
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化
  - SystemMonitor: CPU / メモリ / ディスク / プロセス死活 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常等の検知（monitoring モジュール内）
  - RiskMonitor: ドローダウン・ポジション数監視、KillSwitch トリガー
  - MonitoringEngine: 各モニタを束ねたポーリングループ
  - Kill Switch (data/kill.flag) によるエンジン停止

- Portfolio
  - 候補選定（スコア順）・等ウェイト/スコア重み計算
  - セクターキャップ適用、レジーム判定に基づく投入資金調整
  - 株数計算（リスクベース / equal / score）、単元丸め、aggregate cap 適用

- Research
  - Momentum / Volatility / Value などのファクター計算（DuckDB 経由）
  - Forward returns, IC（Spearman ランク相関）計算、統計サマリ

- AI
  - ニュースセンチメント (news_nlp) — OpenAI（gpt-4o-mini）で記事群を評価し ai_scores に書き込み
  - レジーム判定 (regime_detector) — ETF MA200 乖離 + マクロニュースセンチメントを合成して 'bull'/'neutral'/'bear' を決定

- ツール
  - .env 対話式ウィザード (config_setup.py)
  - 設定検証 CLI (validate_config.py)
  - Paper Trading 検証レポート生成 (tools/paper_verification_report.py)

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型注釈、新しい typing 機能を使用）
- Git でのソース管理が推奨

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と有効化

   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate.bat   # Windows
   ```

3. 必要パッケージをインストール

   依存例（プロジェクト側で requirements.txt を用意している場合はそちらを使用してください）。本コードで使用される主な外部パッケージ:

   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - （必要に応じて broker クライアント等）

   例:

   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードの出力を確認し `.env` を保存してください。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

5. 設定検証（任意）

   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになる
   python -m kabusys.validate_config --strict
   ```

6. DB の初期化
   - SQLite と DuckDB は起動時に必要テーブルを作成します（`data/` ディレクトリが親でなければ自動生成されます）。
   - Paper Trading を使う場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）が別に指定されます。

---

## 環境変数（主に使用されるもの）

- KABUSYS_ENV: 実行環境
  - 値: `development` | `paper_trading` | `live`（デフォルト: `development`）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/... デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト `logs/`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: SQLite 監視 DB（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）
- PAPER_FILL_MODE: ペーパートレード時の約定モデル（`instant|partial|never|reject`、デフォルト `instant`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

自動 .env 読み込み:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（OS 環境変数が優先）。
- 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要コマンド）

- Execution Engine を起動

  - 通常起動（設定に基づく本番/ペーパー判定）:

    ```bash
    python -m kabusys.run_execution
    ```

  - ペーパートレードで明示的に起動する場合:

    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

  実行時の挙動:
  - `KABUSYS_ENV=paper_trading` なら MockBrokerClient を使用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書きます。

- Monitoring を起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  オプション:
  - ポーリング間隔を上書き: `MONITOR_POLL_INTERVAL=30`（秒）
  - 監視は常に本番用 sqlite_path（`SQLITE_PATH`）を使います（環境に依らず）。

  停止方法:
  - `data/stop_requested.flag` ファイルが検出されると監視ループは終了します。

- 設定ウィザード（.env 作成）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- AI 機能（プログラム内利用）
  - ニューススコアリング: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - どちらも OpenAI API キーが必要（引数で渡すか `OPENAI_API_KEY` 環境変数を使用）。

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - 監視・エンジンを外部から停止させたいときに使用（run_monitoring.py / run_execution.py がこれをチェックします）。

- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込む停止フラグ（主に本番での強制停止トリガー）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では推奨されません）。

- data/execution.pid
  - Execution エンジンが書き込む PID ファイル（デフォルト名）。run_execution.py で使用。

- logs/<app_name>.log
  - 各アプリケーション（execution / monitoring 等）ごとに日次ローテーションで保存されます（デフォルト: logs/）。

---

## ディレクトリ構成

主要なソースツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py         — SQLite 永続層（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                      — ランタイムで生成されるファイル（DB, flags, pid など）
  - logs/                      — ログファイル保存先（デフォルト）

（注: 実際のリポジトリにはさらに細かいファイルや submodules が存在します。上は主要ファイルの抜粋です。）

---

## 重要な注意点 / 運用ガイド

- KABUSYS_ENV を `live` に設定すると本番運用になります。LINE 通知設定や Kill Switch の扱い等を十分に確認してください（validate_config にて本番向けの警告が出ます）。
- Paper Trading は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI や外部 API を利用する機能は API キーや利用上のコストが発生します。実行時のエラーはフェイルセーフで扱われる設計ですが、実運用前に十分なテストを行ってください。
- ログは stdout とファイル（logs/<app>.log）に出力されます。ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみとなります。
- プロセス優先度設定（set_process_priority）や CPU affinity（set_cpu_affinity）を使用していますが、権限や OS によっては設定できない場合があるため、失敗時はログに警告が出るのみで継続します。
- .env は機密情報を含むため、絶対に VCS にコミットしないでください。

---

## 開発者向け情報

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml 基準）を探索して行われます。CWD に依存せずにパッケージ配布後も動作するよう設計されています。
- DuckDB 接続を渡して分析モジュール（research / ai）が動作する設計のため、テスト時はインメモリの DuckDB 接続やモックを渡して単体テストがしやすくなっています。
- OpenAI API 呼び出しはモジュール内で小さなラッパー関数に分離しているため、ユニットテストでは patch / mock で差し替え可能です。

---

必要があれば、README に追加で以下の内容を追記できます:
- 依存関係の exact list（requirements.txt から）
- デプロイ / systemd / Docker の起動例
- よくあるトラブルシューティング（ログパス/権限/DB マイグレーション等）
- API 使用例（簡単なコードスニペット）

追記希望があれば教えてください。