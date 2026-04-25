# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

この README はリポジトリ内のモジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース解析など）を要約し、セットアップ・実行手順、主要な環境変数、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供する Python ベースのシステムです。主な機能は次の通りです。

- ExecutionEngine（発注エンジン）：ブローカークライアント経由で注文を実行。`paper_trading` 環境ではモックブローカーで完全分離された DB に記録可能。
- Monitoring（監視）：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、Kill Switch を評価して必要時に ExecutionEngine を停止。
- Portfolio construction：候補選定、重み算出、ポジションサイズ計算、セクターキャップやレジーム乗数などの純粋関数群。
- Research：ファクター（モメンタム・ボラティリティ・バリュー）計算、特徴量探索、IC 計算などの分析機能（DuckDB を使用）。
- AI（ニュース NLP / レジーム検出）：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント集計と市場レジーム判定。
- ツール：Paper Trading の検証レポート生成スクリプト等。

設計上、データ永続化は DuckDB（分析用）と SQLite（監視・発注ログ）を用途に応じて使い分けます。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine（実取引/ペーパートレード対応）
  - ブローカークライアントの抽象化（環境に応じた実装選択）
  - 注文管理、リスク管理、照合（reconciler）

- 監視系
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス検出
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視 + ダッシュボード更新
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: これらを束ねるポーリングループ

- ポートフォリオ構築（純関数）
  - 候補選定（score/rank ベース）
  - 等金額・スコア加重配分
  - ポジションサイズ計算（リスクベース、上限・単元丸め）
  - セクターキャップ・レジーム乗数

- リサーチ
  - DuckDB 接続でファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI（外部 API）
  - ニュースを LLM でスコアリングして ai_scores テーブルへ保存
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定

- ツール
  - Paper Trading 検証レポート出力（期間指定可能）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - 任意の場所で git clone

2. Python と依存ライブラリのインストール（例）
   - Python 3.9+ を推奨
   - 必要なパッケージ（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証用、任意）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実運用では仮想環境 (venv / conda) を推奨

3. ディレクトリ作成
   - デフォルトで使用されるディレクトリ: `data/`, `logs/`
   - 例:
     ```
     mkdir -p data logs
     ```

4. 環境設定 (.env) を作成
   - 対話式ウィザードで .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - main にある `config_setup.py` は以下の設定項目を対話的に作成します（代表例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - LINE_CHANNEL_ACCESS_TOKEN (任意)
     - LINE_USER_ID (任意)
     - LOG_LEVEL (default: INFO)
     - KILL_FLAG_CLEAR_ON_START (0/1, default 0)

5. 設定検証
   - 作成後は検証スクリプトで確認:
     ```
     python -m kabusys.validate_config
     ```
   - `--strict` を付けると警告も失敗扱いになります。

補足:
- .env ファイルは Git にコミットしないでください（機密トークン含む）。
- 環境変数は OS 環境 > .env.local > .env の優先順位で自動読み込みされます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

---

## 主要な環境変数（抜粋とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意・デフォルト
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
  - LOG_LEVEL — デフォルト: INFO
  - OPENAI_API_KEY — AI 機能を使う場合に必要
  - PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（default: instant）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

（上記は `kabusys.config.Settings` と `config_setup.py` を参照した主要な項目です）

---

## 使い方（よく使うコマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番/ペーパートレードを自動選択）
  ```
  python -m kabusys.run_execution
  ```
  振る舞い:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に書き込む（本番 DB と分離）。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
  - 実行中に `data/stop_requested.flag` が作られるとエンジンに停止命令を出します。
  - 起動時の PID は `data/execution.pid` に記録されます。

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  振る舞い:
  - デフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。
  - 監視側は（コード中の注記通り）環境にかかわらず本番の `sqlite_path` を使用して監視テーブルを初期化します。
  - 停止は `data/stop_requested.flag` を作成することで行えます（監視ループは検知して終了します）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを直接指定可能。指定がなければ環境変数 `PAPER_TRADING_SQLITE_PATH` または既定値 `data/paper_trading.db`。

- AI 関連（ニュース NLP / レジーム）
  - 両機能とも `OPENAI_API_KEY` が必要。スクリプトや上位モジュールから関数を呼び出し、DuckDB 接続と対象日を渡して使用します。
  - 例:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止・Kill Switch 周り

- 手動停止（監視 / 実行エンジン共通）
  - `data/stop_requested.flag` を作成すると、run_monitoring や run_execution がそれを検知して安全停止します（run_execution は起動を抑止するチェックもあります）。
- Kill Switch（自動停止）
  - 監視側の条件（ドローダウン閾値超過やポジション上限超過）で `data/kill.flag` を書き込みます（`KillSwitch`）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill flag を自動クリアしますが、本番では 0 を推奨します。

---

## ログ設定

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を全スクリプトで使用して統一的にログを管理します。
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテーションファイル（logs/<app_name>.log、30 日保持）
- 環境変数で調整可能:
  - LOG_LEVEL, LOG_DIR

---

## データベース / スキーマ

- DuckDB: 分析用データベース（デフォルト `data/kabusys.duckdb`）
  - prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime などを想定
- SQLite: 監視・発注ログ（デフォルト `data/monitoring.db`）
  - monitoring 用スキーマは `kabusys.monitoring.monitoring_db.init_monitoring_db` で冪等に作成される
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - マイグレーション: スクリプトは実行時に欠損カラム（例: latency_ms, peak_value）を追加する処理を含みます

---

## 典型的な開発フロー（推奨）

1. .env を作成（`python -m kabusys.config_setup`）
2. 設定を検証（`python -m kabusys.validate_config`）
3. DuckDB に必要なデータを用意（prices_daily など）
4. まず Monitoring をローカルで起動して挙動確認（`python -m kabusys.run_monitoring`）
5. ペーパートレード環境で Execution を起動（`KABUSYS_ENV=paper_trading python -m kabusys.run_execution`）
6. Paper Trading の実行結果を `python -m kabusys.tools.paper_verification_report` で検証
7. AI 機能を使う場合は `OPENAI_API_KEY` を設定して DuckDB 接続で関数を実行

---

## 依存関係（主要）

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（設定ファイル検証に任意で使用）

※ 実際の requirements.txt がない場合はプロジェクト用に作成してください。

---

## ディレクトリ構成（主要ファイル抜粋）

以下はリポジトリの主要なソース配置（`src/kabusys` 以下の抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/
    - (BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等)
  - monitoring/
    - monitoring_db.py
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

（この README はリポジトリに含まれるモジュール実装を基に作成しています。実際のファイルツリーはリポジトリ全体を参照してください）

---

## 注意事項 / 運用上のヒント

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を設定し、`validate_config` の警告を必ず確認してください。
- Monitoring は本番の監視データを参照して Kill Switch を発動する可能性があるため、本番 DB の扱いには十分注意してください（paper_trading でも監視は本番 sqlite_path を使う設計の箇所に注意）。
- OpenAI を利用する機能は API コストとレイテンシ、安定性に依存します。API キーの管理とレート制限対策（バックオフ設定）は適切に行ってください。
- process priority / CPU affinity 設定は `psutil` の権限に依存します。実行環境の権限で設定できない場合は警告が出ますが継続します。

---

必要であれば、README に「デプロイ手順」「監視メトリクスの可視化」「CI / テスト」「ブローカークライアントの実装例」などの追加セクションを追記できます。どの内容を拡張したいか教えてください。