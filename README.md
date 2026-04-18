# KabuSys

日本株向け自動売買システムのコードベース（README）。  
この README はリポジトリ内の主要機能・セットアップ方法・使い方・ディレクトリ構成を日本語でまとめたものです。

> 注: 実行スクリプトは `src/kabusys` 下に配置されています。ここではモジュールを直接実行する前提でコマンド例を示します（例: `python -m kabusys.run_execution`）。

---

## プロジェクト概要

KabuSys は日本株の自動売買（ExecutionEngine）とそれを支える監視（Monitoring）・リサーチ・ポートフォリオ構築・AI（ニュースセンチメント）モジュール群を備えたシステムです。  
主な設計思想は以下の通りです。

- 本番/ペーパー/開発の複数実行モードをサポート（`KABUSYS_ENV`）。
- モジュールは DB（SQLite / DuckDB）や外部 API（kabuステーション、J-Quants、OpenAI）と分離して設計。
- 監視機能（プロセス死活、データ鮮度、リスク監視）で自動停止（Kill Switch）を提供。
- ペーパートレードは本番データベースと分離（専用 SQLite）し、安全に検証可能。
- DuckDB を用いたリサーチ用ファクター計算・探索機能を提供。

---

## 機能一覧

- Execution
  - ExecutionEngine（実際の発注ロジックを含む／BrokerClient を介して実市場または MockBroker を利用）
  - OrderManager / RiskManager / Reconciler / OrderRepository 等の発注関連コンポーネント
  - ペーパートレードモード（`KABUSYS_ENV=paper_trading`）は MockBrokerClient を使用、書き込み先は `data/paper_trading.db`

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視して `system_status` に記録
  - TradeMonitor: 発注ログを監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウンやポジション上限の監視・ログ化
  - KillSwitch: 条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止させる
  - MonitoringEngine / run_monitoring 起動ループ（ポーリング間隔調整可）

- Config / ユーティリティ
  - .env 対話式ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - ログ設定ユーティリティ（共通の Stream + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

- Research / Portfolio
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（IC 計算、統計サマリー）
  - ポートフォリオ構築（候補選定、等配分・スコア配分）
  - ポジションサイジング（リスクベース、上限・ロット丸め、資金スケール）

- AI
  - ニュースセンチメント (news_nlp.score_news)：OpenAI（gpt-4o-mini 等）を用いて記事を銘柄別にスコア化し `ai_scores` に保存
  - レジーム検出 (regime_detector.score_regime)：ETF の MA 乖離 + マクロニュースを LLM で評価して市場レジーム（bull/neutral/bear）を決定

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）：稼働率、注文成功率、レイテンシ等の集計と PASS/FAIL 判定

---

## 必要要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- ネイティブ依存や環境によっては OS パーミッション（プロセス優先度設定等）が必要

※リポジトリに requirements.txt がない場合は上記を pip でインストールしてください。例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成。必要最小環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
4. 設定検証（起動前に推奨）:
   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱いたい場合:
   python -m kabusys.validate_config --strict
   ```
5. ログディレクトリ作成（必要なら）: デフォルトは `logs/`。`LOG_DIR` で変更可。
6. DB 初期化は実行スクリプトが行います（`init_monitoring_db` が呼ばれるため、手動で作成する必要は通常ありません）。

---

## 使い方（主要なコマンド）

- 実行エンジン（ExecutionEngine）起動
  - 本番/ペーパーの違いは `KABUSYS_ENV` による（paper_trading は専用 SQLite を使用）
  ```
  # 実行モードを環境変数で指定（例）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  - 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine が Kill Switch により検出した場合に停止します。
  - 実行時に `data/execution.pid` が記録される仕組み（PID ファイルは Settings でパス変更可）。

- 監視ループ（Monitoring）起動
  ```
  # ポーリング間隔を変更したい場合:
  export MONITOR_POLL_INTERVAL=30  # 秒
  python -m kabusys.run_monitoring
  ```
  - 停止は `data/stop_requested.flag` を作成することでループを抜けます。
  - 監視は常に「本番 sqlite_path」を使う設計（Settings に従う）。

- .env ウィザード（上で説明）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  # デフォルト DB パスを使う場合:
  python -m kabusys.tools.paper_verification_report

  # 期間・DB 指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI / レジーム判定・ニューススコア（ライブラリ関数として利用）
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - どちらも `OPENAI_API_KEY` の設定が必要（引数で API キーを渡すことも可能）

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード時に使用）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / LOG_DIR / LOG_LEVEL など（Settings 参照）

自動 `.env` 読み込み:
- プロジェクトルートに `.env` または `.env.local` がある場合、自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 制御フラグ / ファイル

- data/stop_requested.flag
  - `run_execution.py` / `run_monitoring.py` がこのファイルを検知すると安全に停止します（外部からの停止要求用）。
- data/kill.flag
  - KillSwitch が書き込む「強制停止フラグ」。ExecutionEngine は起動時にこれを検出すると起動しない／停止します。
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル（デフォルトパスは Settings で指定可）。

---

## ロギング

- 共通のロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を全スクリプトが利用します。
- 出力:
  - コンソール（stdout）
  - ファイル: `<LOG_DIR>/<app_name>.log` を日次ローテーション（デフォルト `logs/<app_name>.log` を 30 世代保持）

---

## ディレクトリ構成（主要ファイル）

（リポジトリ直下に `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化・永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（該当ファイル参照）
    - risk_monitor.py — ドローダウン等の監視
    - kill_switch.py — Kill Switch 実装（kill.flag）
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — アラート送信（LINE 等）※実装参照
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注ループ）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
    - broker_factory.py — BrokerClient の生成（環境依存）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 株数決定・スケールダウン
  - research/
    - factor_research.py — ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - data/ （実行時に使用されるファイル群）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用）
    - kill.flag, stop_requested.flag, execution.pid など
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

---

## 開発者向けメモ / 注意点

- DB マイグレーションは簡易的に `monitoring_db.init_monitoring_db` で行われます。既存 DB のスキーマ差分に対応するため ALTER を実行する処理が含まれます。
- AI 機能（news_nlp / regime_detector）は OpenAI API への依存があり、API エラーに対してはリトライ・フェイルセーフ（デフォルトスコア化）を行う設計です。
- `KABUSYS_ENV=paper_trading` にすると発注は MockBroker を使い、本番 DB と完全分離されます（安全な検証が可能）。
- `MONITOR_POLL_INTERVAL` は監視ループのポーリング間隔（秒）。`run_monitoring.py` からオーバーライドできます（デフォルト 60 秒）。
- `KILL_FLAG_CLEAR_ON_START`（.env）を `1` にする設定は本番では危険です（Kill Switch を自動でクリアしてしまいます）。`live` 環境では `0` を推奨します。
- 自動 `.env` 読み込みはプロジェクトルートの判定に `.git` または `pyproject.toml` を用います。CI/テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## よくある操作例

- モジュールを直接実行する（例: Execution）
  ```
  python -m kabusys.run_execution
  ```

- 監視をデバッグ的に 1 回だけ実行（テスト用）
  - MonitoringEngine や SystemMonitor を Python REPL/テストからインポートして `run_once()` / `check_once()` を呼ぶことで単発実行が可能です。

---

## 最後に

本 README はリポジトリに含まれるコード（主に `src/kabusys`）の構造と使い方をまとめた参照です。各モジュール内の docstring にも挙動やエッジケースの注記がありますので、実装の詳細を確認したい場合は個別ファイルを参照してください。質問や追加で README に記載したい内容があれば教えてください。