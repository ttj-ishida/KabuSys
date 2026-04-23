# KabuSys

日本株向け自動売買プラットフォームのリポジトリ（モジュール群のみを抜粋）。  
この README はリポジトリ内スクリプト・モジュールの使い方、セットアップ、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買/リサーチ基盤のコアモジュール群です：

- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード対応）
- 監視（Monitoring）機能：システム状態・注文の監視、Kill Switch（停止フラグ）
- ポートフォリオ構築（候補抽出、重み付け、株数算出）
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証等）
- ペーパートレード検証レポート生成ツール

設計上、実行コンポーネントは本番 DB とペーパートレード DB を明確に分離できます。AI 連携は OpenAI API（例: gpt-4o-mini）を用います。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番/ペーパートレード切替）
- run_monitoring.py: SystemMonitor をポーリング起動（システム状態・データ鮮度監視）
- monitoring_engine: 各種 Monitor（System / Trade / Risk）統合のポーリング実装
- monitoring_db: 監視用 SQLite スキーマ・永続化層
- portfolio: 候補選定、重み計算、ポジションサイズ算出（純粋関数）
- research: DuckDB を用いたファクター計算・特徴量探索
- ai: ニュース NLP スコアリング（OpenAI）・市場レジーム判定
- tools/paper_verification_report.py: ペーパートレードの検証レポート生成
- config_setup.py: .env 対話式ウィザード（初期化・更新）
- validate_config.py: 環境・設定ファイルの起動前チェック
- utils: ロギング設定、プロセス優先度設定等のユーティリティ

---

## 前提 / 推奨環境

- Python 3.10+
- 必須（実行する機能に応じて）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意:
  - PyYAML（validate_config.py が config/*.yaml を検証する場合に必要）

仮想環境を作成して依存パッケージをインストールすることを推奨します。

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# PyYAML が必要なら
pip install pyyaml
```

（requirements.txt がある場合はそれを使用して下さい）

---

## 環境変数（代表例・デフォルト）

主な環境変数とデフォルト値／必須性：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV (任意, デフォルト: development) — 有効値: development / paper_trading / live
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (任意, デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に使用
- LOG_LEVEL (任意, デフォルト: INFO)
- LOG_DIR (任意, デフォルト: logs/)
- PAPER_FILL_MODE (任意, デフォルト: instant) — 有効値: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START (任意, デフォルト: 0)
- MONITOR_POLL_INTERVAL (任意, run_monitoring 用、秒、デフォルト: 60)

設定は .env ファイルにまとめることを想定しています（自動読み込み機能あり）。

---

## セットアップ手順（初期）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（任意）
3. 依存パッケージをインストール（上記参照）
4. 対話式ウィザードで .env を生成:
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須トークン等（J-Quants、kabu API パスワードなど）を入力します。

5. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   ```
   必要に応じて `--strict` オプションを付けて警告もエラー扱いにできます。

6. 必要なディレクトリ（data, logs など）はスクリプトが自動生成しますが、権限などの問題がある場合は手動で作成してください。

---

## 使い方（起動・ツール）

基本的にはパッケージモジュールとして起動します。

- ExecutionEngine 起動（本番または paper_trading に応じて DB を切り替え）:
  ```bash
  python -m kabusys.run_execution
  ```
  停止制御:
  - ExecutionEngine は `data/stop_requested.flag` を監視します。停止したい場合はこのファイルを作成してください。
  - Kill Switch (監視コンポーネント) は `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - 実行時 PID は `data/execution.pid` に書き出されます。

- Monitoring 起動（SystemMonitor のポーリング）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番の sqlite_path を使用して監視テーブルを記録します。

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で SQLite パスを指定可能。デフォルトは `data/paper_trading.db` または環境変数 `PAPER_TRADING_SQLITE_PATH`。

- AI 関連（ニュース NLP、レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してください。
  - news_nlp.score_news / regime_detector.score_regime を呼び出してデータベースを更新します（通常は上位のジョブから呼び出す設計）。

- 設定ウィザード / 検証:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

ログ:
- ログはデフォルト `logs/<app_name>.log` に日次ローテーションで保存されます（utils.logging_setup.setup_logging を使用）。
- コンソールは stdout に出力されます。

注意:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（default: data/paper_trading.db）に記録されます。本番 DB と分離されます。
- AI 機能は API 呼び出しに失敗した場合フォールバック動作（0.0 等）をとる設計です。必ずしも全ての外部呼び出しが成功することを前提にしていません。

---

## 停止・強制停止フラグ

- data/stop_requested.flag: run_monitoring / run_execution の両方でチェックされる停止フラグ（手動で作成すると各プロセスが検知して終了します）
- data/kill.flag: KillSwitch によって書き込まれる停止フラグ（監視コンポーネントが条件を満たしたときに作成）
- 起動時に Kill Flag を自動でクリアしたい場合は環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定できます（本番では推奨されません）。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（OpenAI 併用）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / ラッパー
    - system_monitor.py
    - trade_monitor.py        — （存在する想定のモジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （存在する想定のモジュール）
  - execution/
    - execution_engine.py     — ExecutionEngine（存在する想定のモジュール）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     — 生成されるデータディレクトリ（DB 等）
  - logs/                     — ログ出力先

（実際のファイルはリポジトリに依存します。上記は現在のコードベースの要点を抜粋したものです）

---

## 開発者向けメモ / 注意点

- Settings クラス（config.py）は自動で .env をプロジェクトルートから読み込みます（.env.local を優先上書き）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は常に本番用 sqlite_path を使って監視テーブルを初期化します（監視データは環境に関係なく production sqlite を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB を使用して本番 DB とは完全に分離します。
- ロギングは utils.logging_setup.setup_logging を通じて統一的に設定されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- AI モジュールは OpenAI SDK のエラー（RateLimit, Timeout, 5xx 等）に対してリトライやフォールバック処理を実装していますが、API キーは必ず適切に管理してください。

---

## よく使うコマンド例

- .env 作成ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、README に追加する詳細（API 仕様、DB スキーマ説明、ExecutionEngine の起動オプション、ユニットテストの実行手順など）を提供できます。どの部分を詳述したいか教えてください。