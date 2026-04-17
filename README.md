# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。  
本リポジトリには、設定管理・起動スクリプト・監視・発注エンジン周りのユーティリティ、ポートフォリオ構成、リサーチ/ファクター計算、AI（ニュースセンチメント / レジーム判定）連携などの実装が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買を支援する内部ライブラリ群および実行スクリプト群です。主要な機能として：

- 発注エンジン（ExecutionEngine）起動スクリプト（本番 / ペーパートレード対応）
- 監視デーモン（System / Trade / Risk の監視、Kill Switch）
- 環境設定ウィザード（.env の対話的作成）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- Paper Trading の検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み計算・株数計算）
- リサーチ（ファクター計算、特徴量解析、将来リターン・IC 計算）
- AI 連携モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- 監視ログの永続化（SQLite）と分析向け DuckDB

設計方針としては「本番口座や発注 API に不必要にアクセスしない」「ルックアヘッドバイアスを避ける」「フェイルセーフで継続できる」ことを重視しています。

---

## 機能一覧（抜粋）

- 設定関連
  - 環境変数の自動読み込み（.env / .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モードを分離）
  - run_monitoring.py: SystemMonitor ポーリングループ
  - Kill Switch: 条件を満たすと data/kill.flag を作成して ExecutionEngine に停止シグナル送付
- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor
  - AlertManager: LINE Messaging API による通知（必要なトークンが設定されている場合）
  - MonitoringDB: SQLite に監視ログを保存（system_status / trade_logs / risk_logs / positions / dashboard）
- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、セクターキャップ、レジーム乗数、ポジションサイズ算出（単元丸め含む）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー
- AI
  - news_nlp.score_news: OpenAI を用いたニュースの銘柄別センチメントスコア生成（ai_scores テーブルへ）
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定のレポートを生成

---

## 前提・依存パッケージ（例）

最低限必要な外部依存（プロジェクトの requirements.txt がない場合の一例）:

- duckdb
- psutil
- openai
- requests
- PyYAML（validate_config で YAML 検証を行う場合に必要）

インストール例:

pip install duckdb psutil openai requests PyYAML

（実際のプロジェクトでは requirements.txt / poetry / pipenv 等を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 環境を用意（推奨: 仮想環境）

3. 必要パッケージをインストール（上記参照）

4. .env の作成（対話式ウィザード推奨）  
   python -m kabusys.config_setup  
   - 主要な必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD  
   - OpenAI を使う機能を利用するなら OPENAI_API_KEY を設定  
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - .env は絶対に Git にコミットしないでください（機密情報を含むため）

5. 設定検証（推奨）  
   python -m kabusys.validate_config  
   --strict を付けると警告も失敗扱いになります。

6. data ディレクトリ等の作成（必要なら）  
   実行時に自動作成されますが、先に作っておくと権限問題を防げます。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
    - 起動前に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中は data/execution.pid に PID を書きます。Graceful stop は stop フラグを作ることで行います（下記を参照）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings の sqlite_path（監視 DB）を使用して初期化。
    - ポーリング間隔はデフォルト 60 秒。環境変数 MONITOR_POLL_INTERVAL によって上書き可能（例: MONITOR_POLL_INTERVAL=30）。
    - run_monitoring は常に「本番の sqlite_path」を参照します（環境によらず本番 DB を監視する仕様）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います。

- 停止 / Kill
  - 監視/実行両プロセスの即時停止: プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring/run_execution は検知して終了します（run_execution は検知次第 engine.stop() を呼びます）。
  - Kill Switch（リスク条件による ExecutionEngine 停止）:
    - リスク条件を満たすと監視側が data/kill.flag を作成します。ExecutionEngine はこの kill.flag を検出し、起動時や実行中に停止します。
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力内容: 稼働率、注文成功率、送信率、レイテンシなど。基準未達は FAIL として報告。

- AI 関連（プログラムからの呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日のニュースをスコアリングして ai_scores テーブルに書き込む。
    - api_key 未指定時は環境変数 OPENAI_API_KEY を参照。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA200 とマクロニュースの LLM 評価を合成して market_regime テーブルへ書き込み。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境 / 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

- DB/ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: execution.pid のパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）

- Paper Trading 設定
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

- 監視
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## ディレクトリ構成（主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数読み込み・Settings
  - config_setup.py          -- .env 対話型ウィザード
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py    -- プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       -- SQLite 永続化層（テーブル作成 / DB 操作）
    - monitoring_engine.py   -- 各 Monitor を束ねる Engine
    - system_monitor.py      -- システム状態・データ鮮度監視
    - trade_monitor.py       -- 注文滞留・約定異常監視
    - risk_monitor.py        -- ドローダウン・ポジション上限監視
    - kill_switch.py         -- kill.flag の管理
    - alert_manager.py       -- LINE 通知（push）
  - execution/                -- 発注・Order 関連（抜粋参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            -- ニュースNLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     -- 市場レジーム判定（OpenAI 呼び出し）
  - tools/
    - paper_verification_report.py -- Paper Trading レポート生成

data/ ディレクトリ（プロジェクトルート）:
- data/kabusys.duckdb (デフォルト)
- data/monitoring.db (デフォルト)
- data/paper_trading.db (paper_trading 用)
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 注意事項 / 運用メモ

- 本番稼働時は KABUSYS_ENV=live を設定。validate_config で本番に適した警告を表示します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨しません（誤動作時に自動的にクリアされるため危険）。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を用いた外部停止に対応しています。運用中にプロセスを安全に停止するにはこのフラグを作成してください。
- OpenAI API 利用部分は API キーが必須です。API リクエストはレート制限や一時エラーへのリトライロジックを持ちますが、API 利用にはコストが発生します。
- SQLite / DuckDB のパスや権限を確認してください。監視スクリプトは sqlite_path を常に監視 DB として使用します（run_monitoring は環境にかかわらず本番 sqlite_path を参照する実装になっています）。
- ログや重要ファイル (.env, data/*.db, pid/flag) のバックアップと適切なアクセス権管理を推奨します。

---

## よくある操作例

- .env を新規作成（ウィザード）
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config

- 監視をデバッグ実行（短い間隔で）
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

- ExecutionEngine を起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポートを 2026-04-01 〜 2026-04-11 で生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

ドキュメントや実運用に関する補足が必要であれば、README に追加する内容（例: 完全な依存関係ファイル、システム構成図、DB スキーマ詳細、起動/監視の運用手順書テンプレート）を教えてください。必要に応じて追記・整形します。