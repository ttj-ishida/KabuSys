# KabuSys

日本株自動売買システム — 軽量なトレード実行・監視・リサーチツール群のモノリポジトリ（抜粋）。

以下は本リポジトリ内の主要コンポーネントに対する概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。主な機能は次のとおりです。

- ExecutionEngine（発注／リスク管理／注文リコンシリエーション）
- Monitoring（システム状態、注文滞留、リスク監視、アラート）
- Portfolio construction（銘柄選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算、特徴量解析、IC計算）
- AI 支援（ニュースセンチメント、レジーム判定 via OpenAI）
- 開発用ツール（Paper Trading 検証レポート、Streamlit ダッシュボードなど）

設計方針の一部：
- DuckDB / SQLite をローカル DB として使用（履歴・監視ログ・研究データ保存）
- Paper Trading は本番 DB と完全分離（`KABUSYS_ENV=paper_trading`）
- LLM 呼び出し部はフェイルセーフを備え、APIキーは環境変数で供給

---

## 機能一覧（主なモジュール）

- `kabusys.run_execution` — ExecutionEngine 起動スクリプト。環境によって MockBroker を使い分け。
- `kabusys.run_monitoring` — SystemMonitor のポーリングループ起動スクリプト。ポーリング間隔は環境変数で上書き可能。
- `kabusys.monitoring` — 監視関連一式：
  - `monitoring_db`：SQLite スキーマ初期化 / 永続化 API
  - `system_monitor`：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - `trade_monitor`：注文滞留・約定価格異常監視
  - `risk_monitor`：ドローダウン・ポジション上限監視
  - `kill_switch`：ファイルによる実行停止シグナル（`data/kill.flag`）
  - `alert_manager`：LINE Messaging API による通知送信
  - `streamlit_dashboard`：監視ダッシュボード（Streamlit）
  - `monitoring_engine`：複数モニタを束ねて定期実行
- `kabusys.execution` — 注文管理・リコンシリエーション、ブローカ抽象
  - `order_manager`, `reconciler`, `order_repository` 等
- `kabusys.portfolio` — 候補選定・重み算出・リスク調整・ポジションサイズ計算
- `kabusys.research` — ファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量解析（IC 等）
- `kabusys.ai` — OpenAI を用いたニュース NLP / レジーム判定
- `kabusys.tools.paper_verification_report` — Paper Trading 用の検証レポート生成

---

## セットアップ手順

前提：Python 3.10+ を想定（型注釈に union types 等を使用）。OS は Linux/macOS/Windows いずれでも可。

1. リポジトリをクローン / 適切なパスで作業ディレクトリへ移動。

2. 仮想環境作成（推奨）：
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール（プロジェクトに requirements.txt がない場合は下記を手動でインストール）：
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   補足：
   - `duckdb`：リサーチ用データクエリ
   - `psutil`：プロセス優先度・システム情報
   - `requests`：LINE API 呼び出し
   - `openai`：LLM（ニュース・レジーム判定）
   - `streamlit`：監視ダッシュボード（任意）

4. 環境変数設定：
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると、自動的に読み込まれます（OS 環境変数より低優先）。
   - 自動読み込みを無効化する場合：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主な環境変数（例）：
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (LLM 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH (監視 DB path、デフォルト: data/monitoring.db)
     - DUCKDB_PATH (DuckDB path、デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB、デフォルト: data/paper_trading.db)
     - PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid, data/kill.flag）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）

   サンプル `.env`（最低限の例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成：
   ```
   mkdir -p data
   ```

---

## 使い方

以下は主要な実行方法の例です。パッケージが開発中の場合は、プロジェクトルート（`src` にパッケージがある想定）から実行してください。

- ExecutionEngine（本番/ペーパートレードの実行）
  - ペーパートレード（環境変数で切り替え）：
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - `paper_trading` の場合、MockBrokerClient が使用され、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。本番 DB と分離されます。

  - 本番モード：
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

  - 仕組み：
    - 起動時にプロセス優先度を「high」に設定（成功すれば）。`PID_FILE_PATH` に PID を書くなどの動作が関連箇所にあります。
    - `OrderRepository`, `OrderManager`, `RiskManager`, `Reconciler`, `ExecutionEngine` を組み立てて `engine.run_session()` を呼びます。

- Monitoring（SystemMonitor のポーリング）
  - デフォルトポーリング（60秒）：
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔の上書き：
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    - 環境変数 `MONITOR_POLL_INTERVAL` に正の整数を与えて秒数を変更できます（1 未満や不正値は無視されてデフォルトにフォールバック）。

  - 監視は常に「本番 sqlite_path」を参照する設計（KABUSYS_ENV に関係なく production の sqlite_path を使用）。

- Streamlit ダッシュボード（監視）
  - 起動コマンド（例）：
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
    - `--db` に読み取り専用で開きたい SQLite パスを渡せます（Dash は read-only URI を使用します）。

- Paper Trading 検証レポート
  - 単体スクリプト実行：
    ```
    python -m kabusys.tools.paper_verification_report
    ```
  - 期間指定：
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定：
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```
  - 検証内容：
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 等の集計と PASS/FAIL 判定を標準出力へ出力します。

- AI 機能（ニュースセンチメント / レジーム判定）
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` — DuckDB 接続と日付を渡して実行
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — 同様
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数、または関数引数 `api_key` で提供する必要があります。未設定だと ValueError。

---

## 環境変数 / 設定（主なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必須）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

Settings クラスで各値の検証やデフォルトが実装されており、不正な値は起動時に例外を投げます。

---

## 重要な設計 / 運用メモ

- Monitoring の DB 初期化: `init_monitoring_db()` がテーブル作成とマイグレーション（スキーマ追加）を冪等に実行します。
- Kill Switch: `data/kill.flag` を書くことで ExecutionEngine に停止シグナルを送ります（KillSwitch モジュール）。既にフラグが存在する場合は再書き込みを行いません。`kill.flag` のクリーンアップは起動時オプションで行われる箇所があるため、必要に応じて削除してください。
- PID ファイル: SystemMonitor は PID ファイルの存在・生存確認（stale PID の検出と削除）を行います。PID ファイルの不整合時にアラートを上げます。
- Paper Trading: `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録します。本番データベースと完全に分離されています。
- OpenAI 呼び出しはネットワーク障害やレート制限に対して指数バックオフでリトライする実装が組み込まれていますが、API キー未設定時は ValueError を投げます。AI 関連機能を運用する場合は API キー管理に注意してください。

---

## ディレクトリ構成（抜粋）

以下は src 以下の主なファイル・モジュール構成（本ドキュメント作成時点での抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ & MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record, ...)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py

補足：`kabusys.data` などのパッケージが参照されていますが、本抜粋に含まれていない補助モジュール（データ取り込みパイプラインや統計ユーティリティ等）が別途存在する想定です。

---

## トラブルシューティング

- DB が見つからない / 読み込みエラー:
  - Streamlit ダッシュボードは読み取り専用 URI で DB を開こうとするため、ファイルのパスが正しいか確認してください。
- OpenAI 呼び出しが失敗する:
  - `OPENAI_API_KEY` を設定しているか確認。接続エラーや 429 の場合はログにリトライ情報が出力されます。
- 環境変数が反映されない:
  - `.env` の自動読み込みはプロジェクトルートを `.git` または `pyproject.toml` の親ディレクトリから探索して行います。CI/環境によっては `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットされていないか確認してください。
- MONITOR_POLL_INTERVAL が反映されない / 不正値:
  - 0 以下や非整数が設定されるとデフォルト（60 秒）にフォールバックし、警告ログが出ます。

---

## コントリビュート / 開発メモ

- コードはモジュール単位でテスト可能な純粋関数（特に portfolio / research）と、DB/外部 API に依存する部分が混在します。ユニットテストを書く際は依存関係をモックすることをお勧めします。
- LLM 呼び出し系（news_nlp / regime_detector）は外部 API を直接呼ぶため、テスト時は `_call_openai_api` を patch すると簡単です（実装中で想定済み）。

---

必要であれば、README に含めるサンプル `.env.example`、systemd/NSSM 用の起動ユニット例、またはデプロイ手順（Dockerfile など）も作成できます。どれを追加しますか？