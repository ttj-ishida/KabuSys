# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ＋起動スクリプト群）。  
このリポジトリはシステム監視、注文実行、ポートフォリオ構築、研究・ファクター計算、AI（ニュースセンチメント／レジーム判定）など複数コンポーネントで構成されています。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネントから構成される自動売買フレームワークです。

- 注文実行エンジン（ExecutionEngine、ブローカークライアントを抽象化）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor + Kill Switch）
- ポートフォリオ構築・ポジションサイズ計算（純関数群）
- 研究用ファクター計算（DuckDB を用いた prices_daily / raw_financials 参照）
- AI モジュール（ニュースセンチメント・市場レジーム判定、OpenAI を利用）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主要な起動スクリプト:
- run_execution.py — 実行エンジンの起動（本番 / ペーパートレード切替あり）
- run_monitoring.py — SystemMonitor のポーリングループ起動
- validate_config.py — 環境変数 / config/*.yaml の事前検証
- config_setup.py — .env を対話式に作成・更新するウィザード
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 機能一覧

- 環境別動作モード（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使い、本番 DB と切り離した SQLite（デフォルト `data/paper_trading.db`）に記録
- ExecutionEngine：発注ロジック、OrderManager、RiskManager、Reconciler などを組み合わせて注文実行を管理
- Monitoring：CPU / メモリ / ディスク / プロセス生存の監視、データ鮮度チェック、滞留注文や約定異常、ドローダウン監視
- Kill Switch：閾値超過時に `data/kill.flag` を書き込み ExecutionEngine を安全に停止させる仕組み
- Portfolio：候補選定、等金額／スコア重み、リスクベースの数値化、セクター上限適用、レジーム乗数
- Research：モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC 計算など（DuckDB 接続）
- AI：ニュースを LLM（OpenAI）で評価して ai_scores に格納、マクロニュースから市場レジーム判定
- 運用支援：.env 作成ウィザード、設定検証 CLI、ペーパートレード検証レポート

---

## 前提条件（開発・運用環境）

- Python 3.9 以上（型記法や一部ライブラリ要件を満たすこと）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行う場合）
- SQLite（標準ライブラリで利用）
- （任意）kabuステーション のローカルモック or 実運用接続

パッケージはプロジェクトに requirements.txt がない場合、venv を作成して手動インストールしてください（例）:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数（.env）を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（プロジェクトルート）  
     主要なキー（必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 専用
     - LOG_LEVEL (default: INFO)
     - OPENAI_API_KEY (AI 機能を使う場合必須)

   - .env の自動読み込み:
     - `kabusys.config` モジュールはプロジェクトルートを自動検知し `.env` / `.env.local` をロードします。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（実行前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリを作成（ログ・DB・フラグ用）
   - data/ と logs/ をプロジェクトルートに作成しておくと権限エラーを回避しやすいです。

---

## 使い方（主要コマンド）

- ExecutionEngine（注文実行）
  - 本番/ペーパートレードは KABUSYS_ENV により切替
  - 起動:
    - python -m kabusys.run_execution
  - ペーパートレードは `KABUSYS_ENV=paper_trading` にし、`PAPER_TRADING_SQLITE_PATH` に保存されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンが停止します。
  - デフォルトでプロセス優先度を "high" に設定します（管理者権限により制限される場合があります）。

- Monitoring（SystemMonitor のループ）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` を監視しており、存在するとループを終了します。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず監視 DB は本番パスを使う設計）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を生成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - .env や config/*.yaml の存在・基本整合性をチェックします（--strict で警告をエラー扱い）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可（デフォルト: data/paper_trading.db）

---

## 重要な環境変数・ファイル（抜粋）

- KABUSYS_ENV: 実行モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を用いる AI 機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- PID/フラグファイル:
  - data/execution.pid — ExecutionEngine 用 PID ファイル（run_execution 内で使用）
  - data/stop_requested.flag — 起動/ループ停止用フラグ（run_execution/run_monitoring が監視）
  - data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine 停止トリガー）

ログ:
- デフォルトログディレクトリ: logs/
- ログファイルは app_name に基づき `logs/<app_name>.log`（例: logs/execution.log, logs/monitoring.log）
- LOG_DIR で変更可能。ログのローテーションは日次で 30 日保持。

---

## 実装上の注意点（運用メモ）

- run_execution は KABUSYS_ENV=paper_trading の場合、本番 DB とは別に paper_trading 用 DB を使用し MockBrokerClient を利用する設計です。実運用では `KABUSYS_ENV=live` を正しく設定してください。
- config モジュールはプロジェクトルートを .git または pyproject.toml で自動検出して `.env` / `.env.local` を読み込みます。CWD に依存しない実装です。
- AI モジュールは OpenAI API を呼び出します。API 呼び出しはリトライ・バックオフなどの耐久性処理（429 / ネットワーク断 / 5xx）を含みますが、API キー未設定時は例外を投げます。
- Monitoring は監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を SQLite に格納します。init_monitoring_db が必要なテーブル作成・マイグレーションを行います。
- KillSwitch は閾値に達した際に `data/kill.flag` を書き込み ExecutionEngine に停止を促します。既存の flag がある場合は上書きしません（冪等）。

---

## ディレクトリ構成

（プロジェクトルート /src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の読み込み、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — 共通ロギング初期化
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ — 実行エンジン関連（EngineConfig, ExecutionEngine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文関連監視（滞留注文等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — Kill Switch（フラグファイル書き込み）
    - alert_manager.py — （通知周りの実装）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・上限・スケールダウン
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — マクロ＋MA200 を合成したレジーム判定（OpenAI optional）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

その他:
- data/ — デフォルトの DB / フラグ / PID 保存先（手動作成推奨）
- logs/ — デフォルトのログ出力先

---

## よくある質問（FAQ）

- Q: ペーパートレードと本番 DB は分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading のときは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用され、本番の `SQLITE_PATH` とは分離されます。

- Q: Monitoring のポーリング間隔を変えたいです。  
  A: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（最小値 1 秒未満は無効でデフォルトにフォールバックします）。

- Q: Kill Switch が発動したらどうすればよいですか？  
  A: `data/kill.flag` に理由が書き込まれます。原因を調査の上、問題を解決したら flag を手動で削除して再起動してください（KillSwitch.clear() を呼ぶ機能もあります）。

---

必要に応じて README に補足したい項目（例: API 仕様、ExecutionEngine の設定例、運用 runbook、ユニットテストの書き方など）を教えてください。README を追加で拡張します。