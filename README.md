# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動用スクリプト群）。  
このリポジトリは、戦略・ポートフォリオ構築、発注実行（ExecutionEngine）、監視（Monitoring）、調査用ユーティリティ、AI を使ったニュース評価などのモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は「安全かつ再現性のある日本株自動売買基盤」を提供することです。以下の責務を持つコンポーネントを含みます。

- 発注実行（ExecutionEngine）
  - 本番 / ペーパートレード（完全に分離した SQLite DB）をサポート
  - ブローカークライアント抽象（実際の kabuAPI / モック）
  - リスク制御、オーダー管理、リコンシリエーション
- 監視（Monitoring）
  - システム状態（CPU/MEM/DISK）、プロセス生存、データ鮮度をポーリング
  - 取引ログ / リスクログを永続化（SQLite）
  - Kill Switch（しきい値超過で停止フラグを書き込み）
- 研究 / ファクター計算（DuckDB を利用）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC 計算などの探索ユーティリティ
- AI ユーティリティ
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価
  - 市場レジーム判定（MA + マクロセンチメントの合成）
- 各種ツール
  - 環境設定ウィザード（.env 生成）
  - 設定検証 CLI
  - Paper Trading 検証レポート生成

---

## 機能一覧（抜粋）

- 環境設定の対話ウィザード（kabusys.config_setup）
- 設定ファイル・環境変数の起動前検証（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading.db に記録
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
- monitoring_db: SQLite を使った監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / AlertManager（監視スタック）
- portfolio モジュール
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数
- research モジュール
  - DuckDB を使ったファクター計算・特徴量解析（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等）
- AI モジュール
  - ニュース NLP による銘柄別スコア付与（kabusys.ai.news_nlp）
  - レジーム判定（kabusys.ai.regime_detector）
- ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install --upgrade pip
   ```

2. 必要な依存をインストールします（プロジェクトの requirements / pyproject があればそちらを利用してください）。代表的な依存:

   - duckdb
   - psutil
   - openai
   - (任意) PyYAML — config/*.yaml 検証に使用

   例:

   ```bash
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（対話式ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   もしくは .env を手動で作成してください（下にサンプルを示します）。

4. 初回起動前に設定検証を行います:

   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

注意:
- デフォルトではプロジェクトルートの `.env` と `.env.local` が自動で読み込まれます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- SQLite / DuckDB のデフォルトファイルは `data/monitoring.db` と `data/kabusys.duckdb` です。必要に応じて `.env` でパスを上書きしてください。

---

## 主要環境変数（代表）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意（主なもの）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant / partial / never / reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — monitoring 起動時のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

サンプル .env（抜粋）

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主要コマンド）

- 設定ウィザード（.env を対話式で作成）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（別プロセスで実行。KABUSYS_ENV に応じて本番/ペーパートレードを自動判定）

  ```bash
  python -m kabusys.run_execution
  ```

  補足:
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中に `data/stop_requested.flag` を作るとエンジンに停止シグナルを送ります（または OS による PID 操作）。
  - ExecutionEngine の PID は `.pid` ファイルに書き込まれます（Settings.pid_file_path）。

- Monitoring を起動（ポーリングループ）

  ```bash
  python -m kabusys.run_monitoring
  ```

  環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔変更可（秒）。デフォルト 60 秒。

- Paper Trading 検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI ニューススコアリング（プログラム呼び出し）
  - k as a library: `from kabusys.ai.news_nlp import score_news` を利用します。OpenAI キーが必要。

---

## 監視 / 停止フラグの取り扱い

- 停止リクエスト（外部から実行停止する簡易手段）
  - data/stop_requested.flag: run_execution / run_monitoring スクリプトはこのファイルの存在をチェックし、検出時に安全に停止します。
- Kill Switch（リスク条件による自動停止）
  - 条件に合致した場合、KillSwitch が `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこの flag を検出し動作を停止または起動を拒否できます。
  - .env の KILL_FLAG_CLEAR_ON_START を `1` にすると起動時に kill.flag を自動で削除します（本番では推奨しません）。

---

## ロギング

- ログは標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます（kabusys.utils.logging_setup.setup_logging）。
- ログディレクトリは環境変数 `LOG_DIR` または引数で指定可能。デフォルトは `logs/`。
- デフォルト保持期間は 30 日（TimedRotatingFileHandler）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの構成イメージ（src/kabusys/ 以下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager, Reconciler, etc.)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（全ファイルは README の目的上抜粋しています。実際のツリーはリポジトリ内の src/kabusys を参照してください。）

---

## 開発者向けメモ

- DuckDB 接続（分析用）と SQLite（監視 / 注文履歴）は明確に分離されています。
- ペーパートレードは本番 DB と完全に分離する設計（PAPER_TRADING_SQLITE_PATH）。
- 時間や日付の扱いはルックアヘッドバイアス回避の観点から厳格にされています（target_date を明示的に渡す実装）。
- OpenAI 呼び出しはリトライ・バックオフを実装しており、 API 失敗時はフェイルセーフとして処理を続行する設計です。
- 自動で .env を読み込む挙動はプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効にできます。

---

## よくあるトラブルシュート

- .env を用意していない / 必須環境変数が未設定:
  - `python -m kabusys.validate_config` を実行して警告・エラー内容を確認してください。
- OpenAI 呼び出し関連のエラー:
  - 環境変数 OPENAI_API_KEY の設定を確認してください。
  - ネットワーク/レート制限による一時失敗はログに記録され再試行されます。
- ログファイルが生成されない:
  - デフォルトでは `logs/` に出力します。パーミッションやディスク容量を確認してください。
  - ログディレクトリが作れない場合は stdout のみで継続します（警告が出ます）。

---

必要であれば、README に追加する内容（例: 各モジュールの API リファレンス、起動時の推奨プロセス管理（systemd / supervisor 用のサンプル unit）、テスト方法、CI 設定例など）を作成します。どの情報が欲しいか教えてください。