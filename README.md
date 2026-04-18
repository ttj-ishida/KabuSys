# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群です。  
この README はリポジトリ内の主要モジュール（設定管理 / 起動スクリプト / 監視 / ポートフォリオ構築 / 研究用関数 / AI 統合など）を中心に、セットアップと基本的な使い方を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 実行エンジン (ExecutionEngine) — 発注・注文管理・リスク管理を担う（run_execution.py）
- 監視コンポーネント — システム状態・注文状況・リスクを定期監視してアラートや Kill Switch を操作（run_monitoring.py と monitoring/*）
- ポートフォリオ構築ライブラリ — 候補選定、重み計算、ポジションサイジング等（portfolio/*）
- 研究・特徴量計算 — DuckDB を使ったファクター計算・IC 等の分析（research/*）
- AI 統合（OpenAI） — ニュース NLP による銘柄スコアリング、レジーム判定（ai/*）
- ユーティリティ類 — ログ設定、プロセス優先度設定、設定読み込み等（utils/*）
- CLI ツール — .env ウィザード、設定検証、ペーパートレード検証レポート等（config_setup.py / validate_config.py / tools/*）

設計上の特徴：
- 環境変数 / .env で設定を管理（`kabusys.config.Settings`）
- Paper trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（`data/paper_trading.db`）
- DuckDB を研究・集計用途に利用
- OpenAI 統合はオプション（`OPENAI_API_KEY` が必要）

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード対応）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定管理
  - .env 自動読み込み（プロジェクトルートから .env / .env.local）
  - `python -m kabusys.config_setup` による対話式 .env ウィザード
  - `python -m kabusys.validate_config` による設定検証（--strict モードあり）
- 監視
  - system_monitor: CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - trade_monitor: 注文滞留/約定異常検出（trade_logs）
  - risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - kill_switch: 条件で `data/kill.flag` を書き込むことで ExecutionEngine を停止可能
  - MonitoringDB: SQLite に監視ログ永続化（自動マイグレーション含む）
- ポートフォリオ / 発注ロジック（純粋関数群）
  - 候補選定・重み計算・ポジションサイジング・セクター制限・レジーム乗数
- 研究用関数
  - ファクター計算（Momentum / Volatility / Value）
  - Forward returns / IC / 統計サマリ
- AI
  - news_nlp: raw_news を OpenAI でスコア化して ai_scores に保存
  - regime_detector: MA + マクロニュースで市場レジーム判定・保存
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

---

## 必要条件 / 依存関係

主な Python ライブラリ（少なくとも以下を想定）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML の検証を有効にしたい場合。無ければ警告のみ）

インストール例（venv を作った上で）:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # requirements.txt がある場合
   ```
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   もしくは .env を手動で作成（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```
4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告を fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて DB ディレクトリ作成（起動時に自動作成されることもあります）
   ```bash
   mkdir -p data logs
   ```

注意:
- Paper trading を使う際は `KABUSYS_ENV=paper_trading` に設定すると、専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）が使用されます。
- OpenAI を利用する機能を使う場合は `OPENAI_API_KEY` を環境変数に設定してください。

---

## 使い方（起動 / 実行例）

- ExecutionEngine の起動（通常は本番/ペーパーに応じて挙動が変わる）
  ```bash
  python -m kabusys.run_execution
  ```
  動作の特徴:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper DB（デフォルト: data/paper_trading.db）へ記録します。
  - 起動時に `data/stop_requested.flag` が存在すれば起動を中止します。
  - 実行中に `data/stop_requested.flag` が作成されるとエンジンに停止シグナルを送ります。
  - 実行中の PID は `data/execution.pid` に書き込まれます（設定で変更可能）。

- Monitoring の起動（システム監視）
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション / 挙動:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は `KABUSYS_ENV` に関係なく本番 sqlite path（`SQLITE_PATH`）を使用します（監視 DB は共通で使われる想定）。
  - 停止は `data/stop_requested.flag` を作ることで可能。
  - ログは `kabusys.utils.logging_setup.setup_logging` によって `logs/monitoring.log` 等へ出力されます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 主要な環境変数（抜粋）

必須（アプリの本体を動かす際）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/...
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の MockBroker の fill 挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1。production では 0 推奨）

詳細は `kabusys.config.Settings` のプロパティを参照してください。

---

## Kill Switch / 停止フラグ

- kill.switch: `KillSwitch` はリスク条件等で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを与えます。
- 管理者が明示的に停止する場合は `data/stop_requested.flag` を置くことで run_* スクリプトを終了させる仕組みがあります。
- ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の挙動に従い `kill.flag` をクリアする設定が可能です（本番では自動クリアをオフにすることを推奨）。

---

## ロギング

- 共通の設定関数: `kabusys.utils.logging_setup.setup_logging(app_name=...)`
  - コンソール出力は stdout
  - ファイル出力は日次ローテーション（デフォルト logs/<app_name>.log、バックアップ 30 日）
  - LOG_DIR 環境変数や引数でログディレクトリを変更可能
  - 起動スクリプトは最初にロギングを設定してから他処理を行う設計

---

## AI 機能について（注意）

- news_nlp / regime_detector は OpenAI を利用します。使用するには `OPENAI_API_KEY` を設定してください。
- API エラーや 5xx・429 はリトライ実装がありますが、失敗時は安全なフォールバック（例: macro_sentiment=0.0）を行い処理継続します。
- AI 機能は必須ではありません。OpenAI 未設定時は該当機能は実行できません（エラー防止のため呼び出し側でキーの存在をチェックします）。

---

## ディレクトリ構成

（リポジトリの `src/kabusys` 相対パスを中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動ロード / Settings
  - config_setup.py         — .env 対話ウィザード CLI
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装想定)
  - execution/              — Execution に関する実装群（broker, engine, order 管理等）
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
  - data/                   — デフォルトのデータディレクトリ（DB, flags 等）
  - config/                 — YAML 設定テンプレート（system_config.yaml 等）

---

## 開発者向けメモ / 実装上の注意

- Settings は .env をプロジェクトルートから自動読み込みします。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト用途）。
- MonitoringDB は起動時に必要なテーブルやカラムが無ければ作成 / マイグレーションを実施します。
- プロセス優先度・CPU affinity 設定は `psutil` を利用します。権限不足時は警告を出してスキップします。
- Paper trading を利用する場合は、本番の SQLite DB と混ざらないよう `PAPER_TRADING_SQLITE_PATH` を確実に分離してください。
- `MONITOR_POLL_INTERVAL` などの数値系環境変数は妥当性チェックが入っています。不正値はデフォルトにフォールバックします。

---

## 例: 典型的な起動フロー（ローカル開発）

1. .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
2. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```
3. 監視を別プロセスで起動
   ```bash
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   ```
4. Execution を起動（別ターミナル）
   ```bash
   python -m kabusys.run_execution
   ```
5. 停止
   - 管理者が停止する場合:
     ```bash
     touch data/stop_requested.flag
     ```
   - Kill Switch（ドローダウン等）がトリガーされると `data/kill.flag` が書かれ、ExecutionEngine を停止させることができます。

---

必要であれば、README に入れる具体的な .env のテンプレート、データベーススキーマの説明、各モジュールの API ドキュメント（関数引数や戻り値の詳細）なども追加できます。どの部分を詳述したいか教えてください。