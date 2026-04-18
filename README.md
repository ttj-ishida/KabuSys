# KabuSys

日本株向け自動売買システムのライブラリ・起動スクリプト群。戦略・ポートフォリオ構築、監視、実行エンジン、AI を用いたニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 要件（依存関係）
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数（主なもの）
- 運用メモ（停止フラグ・ログ等）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買システム向けに設計されたモジュール群です。価格データの集計・ファクター計算、ポートフォリオ構築、注文作成／管理、モニタリング、ペーパートレード検証、LLM を使ったニュースセンチメント計測などを含みます。実際の発注接続は `BrokerClientFactory` の実装で分離されており、`paper_trading` 環境ではモックブローカーで本番 DB と完全に分離して動作します。

---

## 主な機能

- データ解析／リサーチ
  - ファクター計算 (momentum / volatility / value 等)
  - 特徴量探索、IC 計算、将来リターン計算
- ポートフォリオ構築
  - 候補銘柄選定、等配分／スコア加重配分
  - ポジションサイズ算出（ロット丸め・コストバッファ・集約制限）
  - セクターキャップ適用・レジーム乗数
- 実行系
  - ExecutionEngine（実際の注文実行ロジック、リスク管理、リコンサイル）
  - ブローカーファクトリ（本番/モックの切替）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - Kill Switch（条件に応じて ExecutionEngine 停止フラグを書き込み）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）
- AI 関連
  - ニュース NLP（OpenAI を用いた銘柄別センチメント）
  - 市場レジーム判定（ETF + マクロニュースの LLM 判定の合成）

---

## 要件（依存関係）

- Python 3.10+
- 必要パッケージ（主に実行時に使用）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config 検証で YAML の検査を行う場合）
- その他: SQLite は標準ライブラリで利用

インストール例（venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 開発としてパッケージ化している場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 初期設定ファイル (.env) の作成
   - 対話式で作成する場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはリポジトリの `.env.example` を参考に `.env` を編集して配置

5. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ（デフォルト `data/`）とログディレクトリ（デフォルト `logs/`）は、自動的に作成されることが多いですが、権限等の理由で作成に失敗する場合があります。必要に応じて手動作成してください。

---

## 使い方（主要スクリプト・コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - 本番/開発/ペーパートレードは `KABUSYS_ENV` によって切り替わります。
  - ペーパートレードでは `paper_sqlite_path`（デフォルト: `data/paper_trading.db`）へ記録されるため本番 DB と分離されます。
  ```bash
  python -m kabusys.run_execution
  ```

- 監視プロセス（Monitoring）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- .env 対話式設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（ニューススコア／レジーム判定）はライブラリ関数として呼び出します（OpenAI APIキー必須）。
  - ニューススコアリング例（呼び出し側で duckdb 接続を渡す）:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect("data/kabusys.duckdb")
    n = score_news(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - 環境変数 `OPENAI_API_KEY` を設定すると api_key を省略できます。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリアする、0=クリアしない。production では 0 推奨）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）

.env の自動読み込み:
- デフォルトでプロジェクトルート（.git / pyproject.toml を基準）にある `.env` および `.env.local` を読み込みます。
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用メモ

- 停止フラグ
  - run_monitoring と run_execution は `data/stop_requested.flag`（ファイル存在）をチェックして安全に終了します。
  - Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（実際の監視ロジックにより書き込まれます）。`KILL_FLAG_CLEAR_ON_START=1` に設定すると起動時にこのフラグを自動クリアします（本番では注意）。
- ログ
  - 共通のログ設定ユーティリティにより stdout と日次ローテートファイル（logs/<app>.log）へ出力されます。ログディレクトリは `LOG_DIR` で上書き可能。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルと簡易マイグレーション（カラム追加）を行います。既存データに対して冪等に動作します。
- プロセス優先度
  - 起動時に `set_process_priority("high")` を呼び出してプロセス優先度を引き上げます（psutil を使用）。権限がない環境では警告を出して継続します。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要ファイル／ディレクトリ（`src/kabusys/`）の概観です。

```
src/kabusys/
├── __init__.py
├── config.py
├── config_setup.py
├── validate_config.py
├── run_execution.py
├── run_monitoring.py
├── utils/
│   ├── __init__.py
│   ├── logging_setup.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── monitoring_engine.py
│   ├── system_monitor.py
│   ├── risk_monitor.py
│   ├── trade_monitor.py        # （実装ファイルがある想定）
│   ├── alert_manager.py        # （実装ファイルがある想定）
│   └── kill_switch.py
├── execution/
│   ├── execution_engine.py     # 実行エンジン本体
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   ├── broker_factory.py
│   └── risk_manager.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── monitoring/                   # 監視関連（上記）
└── tools/
    ├── __init__.py
    └── paper_verification_report.py
```

（注）上記はリポジトリ内の一部ファイルを抜粋したものです。各モジュールの詳細な実装はファイルヘッダの docstring を参照してください。

---

## 開発者向け注意点・補足

- Python 型注釈・構文（例: `X | None`）を多用しているため Python 3.10+ を推奨します。
- OpenAI を用いる機能は API キーが必要で、API 呼び出し失敗時はフェイルセーフ挙動（スコア 0 やスキップ）で継続する設計になっていますが、運用上は API の安定性を確保してください。
- .env は秘密情報を含むため決して Git にコミットしないでください（config_setup も README に警告あり）。
- Monitoring / Execution 間の DB 分離:
  - Monitoring は常に `SQLITE_PATH`（監視 DB）を参照します。
  - Execution は `KABUSYS_ENV=paper_trading` の場合 `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と分離します。

---

必要であれば README に「起動フロー図」「設定ファイル例（.env.example）」「よくあるトラブルシューティング」を追加できます。どの情報を優先して追加しましょうか？