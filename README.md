# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース説明書です。本 README はプロジェクトの概要、主要機能、セットアップ手順、実行方法、およびディレクトリ構成を日本語でまとめたものです。

※ 本プロジェクトは各種外部 API（kabuステーション、J-Quants、OpenAI 等）やローカル DB（DuckDB / SQLite）を利用します。実運用前に .env の設定と検証を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したモジュール群です。主要な機能は以下の通りです。

- 発注エンジン（ExecutionEngine） — ブローカークライアントを通じて注文を出す。`KABUSYS_ENV=paper_trading` の場合は MockBroker を用いペーパートレード用 DB（data/paper_trading.db）に記録して本番 DB と分離。
- 監視（Monitoring） — システム状態、注文ログ、リスク（ドローダウン・ポジション上限等）を定期ポーリングして監視・アラート・Kill Switch を評価。
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ算出、セクター制約、レジーム乗数などの純粋関数群。
- リサーチ（Research） — DuckDB 上の価格・財務データからファクター（モメンタム、ボラティリティ、バリュー等）計算と特徴量解析。
- AI ツール（AI） — OpenAI を用いたニュースセンチメント評価（銘柄毎のスコア付与）や市場レジーム判定。
- ユーティリティ — ログ設定、プロセス優先度設定、設定ウィザード、設定検証、Paper Trading 検証レポート生成など。

パッケージは `kabusys` 以下にモジュールとして構成されています。

---

## 機能一覧（抜粋）

- 実行（run_execution.py）
  - ExecutionEngine の起動・監視・停止制御
  - Paper Trading 用の DB 分離
  - ブローカークライアント抽象化（BrokerClientFactory）
- 監視（run_monitoring.py / monitoring/*）
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度を監視
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 危険時に `data/kill.flag` を書き込み ExecutionEngine を止める
  - AlertManager（アラート発行機構。実装に依存）
- 環境設定
  - 対話式 `.env` 作成ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
- AI（OpenAI）
  - ニュース NLP で銘柄別スコアを ai_scores テーブルに書込（`kabusys.ai.news_nlp`）
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
- リサーチ
  - ファクター計算（`kabusys.research.factor_research`）
  - 将来リターン・IC 計算など（`kabusys.research.feature_exploration`）
- ユーティリティ
  - ログ設定（`kabusys.utils.logging_setup`）
  - プロセス優先度・CPU affinity（`kabusys.utils.process_priority`）
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）

---

## 必要な依存パッケージ（主要なもの）

最低限インストールが推奨されるパッケージ（環境に合わせてバージョン指定してください）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML （config/*.yaml の検証に必要。必須ではない）
- （標準ライブラリ）sqlite3, logging, threading, datetime 等

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. レポジトリをクローンし、仮想環境を作成して依存をインストールする。
2. プロジェクトルートに `.env` を作成する（対話式ウィザード推奨）。
   - 対話式で作成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI 使用時に必要
     - LOG_LEVEL, LOG_DIR など
3. 設定検証を行う:
   ```
   python -m kabusys.validate_config
   ```
   - 警告も厳密にチェックしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```
4. 必要に応じてデータディレクトリ作成（スクリプト実行時に自動作成されることもありますが、念のため確認してください）:
   - data/
   - logs/

---

## 使い方（実行例）

基本的な起動はモジュールとして実行します。どちらも `setup_logging` により logs/<app_name>.log に出力されます。

- ExecutionEngine 起動
  - 本番（設定に応じて動作）
    ```
    python -m kabusys.run_execution
    ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker が使われ `data/paper_trading.db` に記録されます。

- Monitoring（監視）起動
  - デフォルトでは 60 秒間隔（環境変数 `MONITOR_POLL_INTERVAL` で上書き可能）
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path を参照します（環境にかかわらず monitoring 用 DB は設定の sqlite_path を使用）。

- 設定ウィザード（.env を作る）
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
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI / リサーチ関数呼び出し（ライブラリ利用）
  - Python からモジュールを import して関数を利用可能（例）:
    ```python
    from kabusys.research import calc_momentum
    # DuckDB 接続を渡して使用
    ```

- 停止フラグ / Kill Switch
  - 監視側は `data/stop_requested.flag` の存在を見てループを終了します（開発用の停止フラグ）。
  - ExecutionEngine を即時停止・強制停止したい場合は `data/kill.flag` を検出して停止します。KillSwitch は `data/kill.flag` を書き込むことで発動します。
  - `KILL_FLAG_CLEAR_ON_START=1` を set すると起動時に kill.flag を自動クリアしますが、本番では `0` を推奨します。

- 環境変数でのカスタマイズ（例）
  - 監視ポーリング間隔:
    ```
    export MONITOR_POLL_INTERVAL=30  # 30秒間隔
    ```
  - ログレベル:
    ```
    export LOG_LEVEL=DEBUG
    ```

---

## 重要な設定・環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (監視のポーリング秒数, デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1, 本番では 0 を推奨)

.env は絶対にリポジトリにコミットしないでください（機密情報を含むため）。

---

## ディレクトリ構成（主なファイル・モジュール）

src 以下の主要ファイル / モジュールを説明します（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン定義等）
  - config.py — 環境変数読み込み・Settings クラス（.env の自動読み込み機能含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/  (発注関連の実装群)
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py 等
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（システム状態 / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート実装)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング・lot 単位丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - data/ (ランタイムで作成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid などの制御ファイル
  - logs/
    - execution.log, monitoring.log 等（setup_logging により作成）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定ミスや kill flag の誤クリアが重大な損失に繋がります。`validate_config` と `.env` の確認を必ず行ってください。
- OpenAI の利用は API キーとコストに注意してください。AI モジュールは失敗時にフェイルセーフ（0 やスキップ）するよう設計されていますが、挙動を理解した上で運用してください。
- process priority / nice の設定はプラットフォーム依存・権限依存です。`psutil` の権限エラーは警告でスキップされます。
- DuckDB / SQLite ファイルのパスは `.env` / Settings で制御されます。paper_trading では DB を分離しておくことを強く推奨します。
- ログは標準出力（stdout）と日次ローテートされたファイル（logs/<app>.log）へ出力されます。ログディレクトリの作成に失敗した場合はコンソールのみになります。

---

## よく使うコマンド一覧（まとめ）

- 環境ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要点を簡潔にまとめたものです。各モジュールの詳細な仕様・アルゴリズムや設計文書（例: PortfolioConstruction.md, StrategyModel.md）が同梱されている場合はそれらを併せて参照してください。質問や追加のドキュメント化が必要であればお知らせください。