# KabuSys

軽量な日本株自動売買システムのコアライブラリ群です。本リポジトリは取引ロジック（ポートフォリオ構築、ポジションサイジング、リスク調整）、監視 / モニタリング、AI を使ったニュース解析、研究用ファクター計算などの主要コンポーネントを含みます。

> 現在のバージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド・環境変数）
- ディレクトリ構成（主要ファイルの説明）
- 運用に関するポイント

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買システムのコア部分を提供する Python パッケージです。以下を念頭に設計されています。

- 本番（live）・ペーパートレード（paper_trading）・開発（development）環境を切り替えて運用可能
- DuckDB（分析用） / SQLite（監視・履歴）を使用したデータ格納
- モニタリング（System / Trade / Risk）と Kill Switch による自動停止機構
- ポートフォリオ構築・ポジションサイジング・リスク制約の純粋関数群（テストしやすい）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP とレジーム判定（任意）
- 研究用ファクター計算（DuckDB ベース）

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートを基準に .env / .env.local を読み込み）
  - Settings クラスで環境変数アクセスを型安全に提供

- 起動スクリプト / CLI
  - 実行エンジン起動: run_execution（ExecutionEngine を起動）
  - 監視ループ起動: run_monitoring（SystemMonitor をポーリング）
  - 設定ウィザード: config_setup（対話式で .env を作成）
  - 設定検証: validate_config（環境変数 / config/*.yaml の基本チェック）
  - Paper Trading 検証レポート: tools.paper_verification_report（ペーパートレード DB を解析してレポート出力）

- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度のチェック
  - TradeMonitor: 注文・約定の異常検出（滞留注文、約定価格異常等）
  - RiskMonitor: ドローダウンやポジション上限の監視とリスクログ
  - KillSwitch: 指定条件で data/kill.flag を書き込み、ExecutionEngine に停止シグナル送信
  - MonitoringDB: SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ構築（portfolio）
  - 銘柄候補選定、重み計算（等金額・スコア加重）
  - セクター制限適用、レジーム乗数
  - ポジションサイズ決定（単元株丸め、リスクベース・等分配）

- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）

- AI（任意）
  - news_nlp: raw_news → OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ETF ma200 とマクロニュースの LLM スコアを合成し市場レジーム判定

- ユーティリティ
  - ロギングセットアップ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発・動作確認用）

1. Python（推奨: 3.10+）を用意します。

2. 依存パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - その他、運用環境に応じて PyYAML 等

   例:
   ```
   pip install duckdb psutil openai
   ```

   （プロジェクトの requirements.txt がある場合はそれを使用してください。）

3. プロジェクトルートに移動して .env を用意します。
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）:
   - デフォルトの SQLite / DuckDB の格納先は `data/`、ログは `logs/`。
   - .env の `DUCKDB_PATH` / `SQLITE_PATH` / `LOG_DIR` を確認してください。

---

## 使い方（主要コマンド・環境変数）

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）に書き込みます。
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成すると実行エンジンが停止処理を行います。
  - 実行時にプロセス優先度を "high" に設定します。
  - PID ファイル: `data/execution.pid`（Settings.pid_file_path から参照）

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は設定にかかわらず本番 sqlite_path を使用して監視ログを永続化します。
  - 停止制御: 同じく `data/stop_requested.flag` を検知して監視ループを終了します。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB: `data/paper_trading.db`。`--db` で別パス指定可。
  - 出力: システム稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定。

- AI 関連（OpenAI API）
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数で指定するか、関数呼び出し時に渡します。
  - news_nlp の `score_news`、regime_detector の `score_regime` はプログラム的に呼び出します（CLI ラッパーは提供されていません）。
  - 大量の API 呼び出しはレート制限に留意してください（内部でリトライ・バックオフ実装あり）。

環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 重要
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR、デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能利用時）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）
  - MONITOR_POLL_INTERVAL（run_monitoring でのポーリング秒数上書き）

停止・Kill Switch
- ExecutionEngine の強制停止は kill.flag（デフォルト `data/kill.flag`）を作成することで実行できます。KillSwitch は監視の結果（ドローダウン超過など）で自動的に kill.flag を書き込みます。
- ExecutionEngine 内で kill.flag の存在により起動を中止・停止処理を行います。
- `KILL_FLAG_CLEAR_ON_START=1` を設定するとエンジン起動時に kill.flag を自動で消去します（本番では危険な設定のため注意）。

ログ
- logging setup は `kabusys.utils.logging_setup.setup_logging` を介して統一して設定されます。
- デフォルト: stdout と `logs/<app_name>.log`（日次ローテート、30日保持）
- 環境変数 `LOG_DIR` でログ出力ディレクトリを指定可能

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主なモジュールと役割です。

- __init__.py
  - パッケージのエントリポイント（version 等）

- config.py
  - Settings クラス: 環境変数の読み取り・バリデーション、自動 .env ロード

- config_setup.py
  - .env 生成の対話式ウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数・ファイル存在チェック等）

- run_execution.py
  - ExecutionEngine 起動スクリプト（実トレード / ペーパートレード両対応）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可能）

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定（psutil を利用）

- monitoring/
  - monitoring_db.py: SQLite のテーブル初期化 / 永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: （注文関連監視ロジック）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みロジック
  - monitoring_engine.py: 監視コンポーネントをまとめたポーリングエンジン
  - alert_manager.py:（アラート送信管理、LINE 等）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 実際の発注・注文管理・リスクチェック関連（ExecutionEngine のコア）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数決定（単元丸め・キャップ適用）
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等

- ai/
  - news_nlp.py: ニュースの LLM ベースセンチメント解析 & ai_scores 書き込み
  - regime_detector.py: ETF MA + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py: Paper Trading DB を使った検証レポート生成

---

## 運用に関するポイント・注意事項

- 本番環境（KABUSYS_ENV=live）では設定を慎重に扱ってください。validate_config は live 時に追加警告を出します（LINE 通知設定等）。
- .env は決して Git にコミットしないでください（config_setup でもその旨の注意を出しています）。
- OpenAI を利用する機能は API キー・コスト・レート制限に留意してください。モジュール内でリトライ・バックオフ実装がありますが、頻繁な呼び出しは控えてください。
- Paper Trading は実口座と分離されます（デフォルトで `data/paper_trading.db` を使用）。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみになります。起動ログで警告が出ますので確認してください。
- プロセス優先度の設定や CPU affinity の変更は OS 権限に依存します。権限不足時は警告を出してスキップします。

---

以上が README の概要です。必要であれば以下も追加できます：
- 具体的な .env のテンプレート（.env.example）
- CI / テスト実行手順（ユニットテストのコマンド）
- ExecutionEngine / API のさらに詳細な仕様書（エンドポイント・DB スキーマの説明）

追加で載せたい情報があれば教えてください。