# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群のリポジトリ。  
取引ロジック（ポートフォリオ構築・ポジションサイズ計算）、監視・リスク判定、AI を使ったニュース解析などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要コンポーネントを持ちます。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況、注文状況、リスク指標をポーリングしてログ・アラートを出す監視系
- Portfolio：銘柄選定 / ウェイト計算 / ポジションサイズ決定などの純粋関数群
- Research：DuckDB を使ったファクター計算・特徴量解析ユーティリティ
- AI モジュール：ニュースの NLP スコアリングや市場レジーム判定（OpenAI API を利用）
- Utilities：ログ設定、プロセス優先度設定、設定読み込み等

設計方針の一部：
- 環境変数（.env）ベースで設定管理。`config_setup.py` で対話的に .env を生成可能。
- `paper_trading` 環境では本番 DB と分離し、Mock ブローカで動作する。
- DuckDB はリサーチ向けの分析 DB、SQLite は監視・トレードログ用に使う。
- 起動時にログは `logs/<app>.log` に日次ローテートで出力される。

---

## 主な機能一覧

- 設定ウィザード（.env 生成）: `python -m kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml のチェック）: `python -m kabusys.validate_config`
- Execution 起動スクリプト: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` でペーパートレード（専用 SQLite を使用）
- Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール: `python -m kabusys.tools.paper_verification_report`
- Portfolio モジュール:
  - 候補選定（score / rank）
  - 等金額・スコア加重のウェイト計算
  - ポジションサイズ計算（ロット丸め、利用可能現金によるスケーリング）
  - セクター上限・レジーム乗数処理
- Research モジュール:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算、統計サマリー
- AI モジュール（OpenAI）:
  - ニュースのセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ma200 とマクロニュースを合成）
- 監視（Monitoring）:
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（`data/kill.flag`）による ExecutionEngine 停止シグナル発行

---

## セットアップ（ローカル開発向け）

推奨 Python バージョン: 3.10+

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール（最低限）
   - pip install duckdb psutil openai PyYAML
   - 追加でロギング・その他ユーティリティが必要な場合は適宜インストールしてください。

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example をコピーして編集（リポジトリに例ファイルがあれば）

5. 設定を検証
   - python -m kabusys.validate_config
   - 必要なら厳格モード: python -m kabusys.validate_config --strict

6. データディレクトリ、ログディレクトリの確認
   - デフォルトの SQLite / DuckDB / logs はそれぞれ `data/` と `logs/` に置かれます。必要に応じて作成されます。

環境変数の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動的に読み込まれます（ただし OS 環境変数が優先）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（詳細は `kabusys.config.Settings` / `validate_config.py` を参照）

OpenAI を使う機能を利用する場合:
- OPENAI_API_KEY を設定してください（ai/news_nlp.py, ai/regime_detector.py で使用）

---

## 使い方（実行例）

1. Execution 起動（本番 / ペーパー）
   - 本番（KABUSYS_ENV=live）:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパートレード（DB を分離して Mock ブローカを使用）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   実行時の挙動:
   - `run_execution` は設定から SQLite パスを選び、ExecutionEngine を起動します。
   - 起動時に `data/execution.pid`（既定）へ PID を書き出します。
   - `data/stop_requested.flag` や `data/kill.flag` によって外部から停止命令を出せます。

2. Monitoring 起動
   - ポーリングループを開始:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を指定:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   注意:
   - Monitoring は環境に関係なく本番の sqlite_path を使用して監視ログを記録します（設定設計上の挙動）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを明示する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. 設定検証 / ウィザード
   - ウィザード: python -m kabusys.config_setup
   - 検証: python -m kabusys.validate_config [--strict]

ログ出力:
- デフォルトログディレクトリ: logs/
- 各アプリは `logs/<app>.log` に日次ローテートで出力（例: logs/execution.log, logs/monitoring.log）
- ログレベル: 環境変数 `LOG_LEVEL` または `setup_logging` の引数で制御

停止フラグ / Kill Switch:
- Monitoring/RiskMonitor が条件を満たすと `data/kill.flag` を書き込み、Execution 側がそれを検出して停止する仕組みがあります。
- 手動で停止指示を出すには `data/kill.flag` を作成してください（または `data/stop_requested.flag` を使用してプロセス停止を依頼）。

---

## ディレクトリ構成（主要ファイルの概要）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定読み込みロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化（テーブル作成・マイグレーション・CRUD）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （注文監視ロジック: 滞留注文や約定異常など - 実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねてポーリング・アラート発行
    - alert_manager.py — （アラート送信管理: LINE 等 - 実装ファイルあり）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注ループ）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連・リスク管理
  - portfolio/
    - portfolio_builder.py — 候補選定・ウェイト計算
    - position_sizing.py — 株数決定・スケーリング・ロット丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/
    - pipeline.py — DuckDB / prices データ取得補助（参照あり）
    - stats.py — 正規化ユーティリティなど
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度 / CPU affinity の設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  （テンプレート / 例がある場合はここに置く）

- data/
  - monitoring.db (デフォルト) — SQLite（監視・トレードログ）
  - paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）
  - kabusys.duckdb — DuckDB（リサーチ用）
  - kill.flag / stop_requested.flag / execution.pid — 制御・PID ファイル

- logs/
  - execution.log, monitoring.log, ... — 日次ローテートで保存

---

## 注意事項 / 補足

- 環境変数保護:
  - 自動 .env 読み込みは OS 環境変数を上書きしない仕様（.env.local は override 可能だが OS 環境は protected）。
- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離されます。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続する設計です。
- OpenAI API を利用する箇所は API 呼び出しの失敗に対してバックオフ・フォールバック（安全側のデフォルト値）を組み込んでいますが、API キーが無い場合は該当 API 呼び出し前にエラーになることがあります。
- Python の型注釈で `X | Y`（PEP 604）を使用しているため Python 3.10+ を推奨します。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

必要なら README をプロジェクトの README.md 形式で整形して配置します。追加で「インストール用 requirements.txt を作る」「docker-compose 定義」「起動スクリプト (systemd / service) のサンプル」などが必要であれば教えてください。