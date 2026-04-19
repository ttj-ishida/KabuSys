# KabuSys

日本株向けの自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）。  
バックテスト/リサーチ用の DuckDB 統合、発注・モニタリング・キルスイッチ、LLM を用いたニュース評価などの機能を含みます。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）と発注処理（BrokerClient の抽象化）
- 監視 (Monitoring)：システム稼働、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（OpenAI を用いたニュース感情スコア / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード・検証）
- 開発用ツール（Paper Trading 検証レポート生成）

設計方針の一部：
- 環境依存設定は .env または環境変数で管理
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全分離（`data/paper_trading.db`）
- 監視は本番の sqlite_path を参照（環境に依存せず本番の監視を行う）
- OpenAI 呼び出しはフェイルセーフ（失敗時はスキップ／デフォルト値で継続）

---

## 主な機能一覧

- Execution:
  - 実取引またはペーパー取引（MockBroker）で注文を送信
  - リスクマネージャ、オーダー管理、レコンシリエーション
- Monitoring:
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor：発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み、ExecutionEngine を停止
  - MonitoringDB：SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio:
  - 候補選定（スコア降順等）、等金額/スコア重み、リスクベースの株数算出
  - セクターキャップ、レジーム乗数
- Research:
  - ファクター計算（Momentum/Value/Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- AI:
  - news_nlp: raw_news を LLM でセンチメント評価し ai_scores に保存
  - regime_detector: ma200 と LLM マクロセンチメントを合成してレジーム判定
- ユーティリティ:
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（TimedRotatingFileHandler + stdout）
  - プロセス優先度・CPU affinity 設定

---

## 必要条件（推奨）

- Python 3.10 以上（型ヒントに `X | Y` を使用しているため）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite は標準ライブラリで不要（組み込み）

install 例（venv を作成してから）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境を作成して依存パッケージをインストール（上記参照）

3. .env を作成（対話式ウィザード推奨）

```bash
python -m kabusys.config_setup
```

ウィザードで J-Quants、kabuAPI パスワード、KABUSYS_ENV（development / paper_trading / live）などを設定します。

4. 設定検証（必須項目やファイル存在を確認）

```bash
python -m kabusys.validate_config
# 警告をエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリ／ログディレクトリの確認
- デフォルト DB / ファイル:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid
  - Kill flag: data/kill.flag
  - Stop flag (shutdown for scripts): data/stop_requested.flag
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存

---

## 実行方法（使い方）

各モジュールはパッケージのモジュールとして起動できます。代表的なスクリプト:

- ExecutionEngine を起動（本番またはペーパー環境の設定で切り替え）:

```bash
python -m kabusys.run_execution
```

- Monitoring ポーリングループを起動:

```bash
# デフォルト 60 秒間隔。環境変数で上書き可能:
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- .env を再作成・更新（対話ウィザード）:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
```

- Paper Trading 検証レポート生成（ローカル DB を参照）:

```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示的に指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

注意点:
- `KABUSYS_ENV=paper_trading` の場合、ペーパー用 MockBrokerClient が使用され、発注ログは `data/paper_trading.db` に記録されます（本番 DB と完全分離）。
- `run_monitoring.py` は監視データの永続化に本番 `sqlite_path` を使用します（環境に依存せず監視を行う設計）。

---

## 主要な環境変数

- 必須（最低限セットするもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- データベース / パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（data/paper_trading.db）
- ログ
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）
- AI / 外部 API
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で利用）
- その他
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default 60）
  - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）
  - PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパスの上書き

詳細は `kabusys.config.Settings` の各プロパティの docstring を参照してください。

---

## 停止・Kill Switch の扱い

- ExecutionEngine / Monitoring の停止トリガー:
  - `data/stop_requested.flag` が存在すると run_* スクリプトは安全に終了します（run_monitoring/run_execution がチェック）。
  - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine 停止を意図します（本番保護のため .env の KILL_FLAG_CLEAR_ON_START に注意）。
- Kill flag の操作は監視モジュール（KillSwitch）経由で行われ、冪等に処理されます。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（ファイルは抜粋に含まれないが存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — 通知（LINE など、抜粋に詳細なし）
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・重み計算
    - position_sizing.py     — 株数決定・単元丸め
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility 等のファクター算出
    - feature_exploration.py — IC/統計サマリー等
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（完全なファイル一覧はリポジトリを参照してください）

---

## 開発・デバッグヒント

- ログは stdout と logs/<app_name>.log（デフォルト）に出力されます。ログレベルは LOG_LEVEL にて調整してください。
- OpenAI 呼び出し部分は個別にモック可能（テストで _call_openai_api を patch する設計）。
- DuckDB 接続を渡して関数単体でリサーチ処理を実行できるため、リサーチ機能の単体テストが容易です。
- settings の自動ロードはプロジェクトルート（.git か pyproject.toml）から .env を探します。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 注意事項 / 運用上の留意点

- KABUSYS_ENV=live の場合は本番環境となるため、LINE 通知や kill flag の設定などを慎重に行ってください（validate_config でも警告あり）。
- .env は決してソース管理にコミットしないこと（ウィザードの冒頭説明にも記載）。
- Paper Trading を本番 DB と混同しないよう、PATH を確認してください（`PAPER_TRADING_SQLITE_PATH` を利用）。
- process_priority の設定は OS 権限に依存します。失敗した場合、警告ログのみ出ます。

---

README はここまでです。追加で以下が必要であれば教えてください：
- 具体的な requirements.txt の候補（pip freeze 等）
- systemd や Supervisor 用の起動ユニットサンプル
- さらに詳細な運用手順（デプロイ、バックアップ、ローテーション）