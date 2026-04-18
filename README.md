# KabuSys

日本株自動売買システムのコアライブラリ群・起動スクリプト集です。  
このリポジトリには、マーケットデータ解析用のリサーチモジュール、ポートフォリオ構築ロジック、Execution / Monitoring の起動スクリプト、AI（ニュースセンチメント・レジーム判定）連携などが含まれます。

---

## 主な特徴（機能一覧）

- Execution エンジン起動スクリプト（run_execution）
  - 本番/ペーパートレード切替（KABUSYS_ENV=paper_trading の場合は MockBroker を使用）
  - Paper Trading は専用 SQLite DB（デフォルト `data/paper_trading.db`）に記録し、本番 DB と分離
  - リスク管理（RiskManager）、注文管理（OrderManager）、整合性機能（Reconciler）等の組み立て

- Monitoring
  - run_monitoring によるポーリングベースの監視ループ
  - System / Trade / Risk の各モニタと Kill Switch、アラート連携
  - SQLite に監視ログ永続化（`monitoring_db.py`）

- Portfolio 構築モジュール
  - 候補選定・重み計算（等重／スコア重み）
  - セクター上限ルール、レジーム乗数、ポジションサイズ計算（lot 単位丸め等）

- Research / ファクター計算
  - Momentum, Volatility, Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC 計算、統計サマリー

- AI 連携
  - ニュース記事のセンチメント解析（OpenAI）
  - マクロニュースを用いた市場レジーム判定（LLM と ETF MA の合成）

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - 統一的なログ設定（utils/logging_setup）とプロセス優先度設定（utils/process_priority）

---

## 要件（依存）

- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - PyYAML（config ファイル検証を行う場合）
- （推奨）環境変数管理のため .env をルートに配置する

インストール例（仮）:
```bash
pip install -r requirements.txt
# requirements.txt が無い場合、上記ライブラリを個別にインストール
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動。

2. 仮想環境の作成（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai
   # 必要に応じて PyYAML などを追加
   ```

3. .env ファイルを対話式ウィザードで作成:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を生成または更新します。`.env` は絶対に Git にコミットしないでください。

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. デフォルトのデータディレクトリ作成（必要に応じて手動で）:
   - data/
   - logs/

   ログディレクトリは環境変数 `LOG_DIR` で上書きできます（デフォルト: `logs/`）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト `development`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
- LOG_DIR — ログファイル保存ディレクトリ（デフォルト `logs/`）
- OPENAI_API_KEY — OpenAI を使う機能向け API キー
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定振る舞い（`instant` / `partial` / `never` / `reject`）

Kill / Stop フラグ:
- ExecutionEngine 停止用のファイル:
  - Kill Switch: `data/kill.flag`（KillSwitch が書き込む）
  - 起動・外部停止要求: `data/stop_requested.flag`（run_* スクリプトが検知する停止フラグ）
- PID ファイル: `data/execution.pid`（Execution エンジンの PID を記録）

---

## 実行方法（使い方）

基本的にパッケージモードで実行します。

- 環境変数（例）
  ```bash
  export KABUSYS_ENV=paper_trading
  export OPENAI_API_KEY=sk-...
  export MONITOR_POLL_INTERVAL=30
  ```

- .env がある場合は自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

1. Execution エンジンを起動
   ```bash
   python -m kabusys.run_execution
   ```
   - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、`data/paper_trading.db` に記録します。
   - 起動時に `data/stop_requested.flag` が存在する場合は起動をスキップします。
   - 停止は `data/stop_requested.flag` を作成するか、PID 経由でプロセスを停止します。

2. Monitoring を起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（デフォルト 60 秒）。
   - Monitoring は常に本番用の sqlite_path を使用して監視ログを永続化します。
   - `data/stop_requested.flag` を置くとループを終了します。

3. 設定検証（前述）
   ```bash
   python -m kabusys.validate_config [--strict]
   ```

4. .env 設定ウィザード（前述）
   ```bash
   python -m kabusys.config_setup
   ```

5. Paper Trading 検証レポート生成
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を明示する場合:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

6. AI 機能（ライブラリ関数として利用）
   - ニューススコア付与:
     - 呼び出し: `kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)`
   - レジーム判定:
     - 呼び出し: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)`
   - これらは OpenAI API キー（`OPENAI_API_KEY`）が必要になります。

---

## ファイル・ディレクトリ構成（抜粋）

プロジェクトルート（`src/kabusys` をパッケージとして扱う）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定読み込みロジック
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                    — ニュース NLP（OpenAI）集約と書き込み
    - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み付け
    - position_sizing.py             — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py             — セクター上限・レジーム乗数
  - research/
    - factor_research.py             — Momentum/Volatility/Value 計算（DuckDB）
    - feature_exploration.py         — 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ + DB 操作用ラッパー
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — （発注ログ監視・未実装箇所あり）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - monitoring_engine.py           — モニタ群を束ねるループ
  - execution/
    - (Execution 関連モジュール群: BrokerFactory, Engine, OrderManager, Reconciler, RiskManager 等)
  - monitoring/、execution/、data/ などの DB / ログ操作がある

その他:
- data/ (デフォルトの DB / flag ファイル保存先)
  - monitoring.db (default SQLITE_PATH)
  - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (default DUCKDB_PATH)
  - execution.pid, kill.flag, stop_requested.flag
- logs/ (ログファイル格納, LOG_DIR で上書き可能)

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では特に環境変数（LINE 通知設定等）と Kill Switch 設定を慎重に確認してください。validate_config は live 用の追加チェック・警告を行います。
- `.env` は機密情報（API トークン・パスワード）を含むため、必ず .gitignore に追加し、リポジトリにコミットしないでください。
- Monitoring は常に（本番設定にかかわらず）監視用の sqlite_path を使用します。Execution の paper_trading モードでは専用の paper_sqlite_path を使用して DB を分離します。
- OpenAI を利用する機能は API 利用料が発生します。実行前に `OPENAI_API_KEY` を設定してください。
- ログ出力は `kabusys.utils.logging_setup.setup_logging` によって統制されます。`LOG_LEVEL`, `LOG_DIR` で挙動を調整できます。
- 停止・終了は `data/stop_requested.flag` を作成することで run_monitoring / run_execution が検知して安全停止を試みます。Kill Switch は `data/kill.flag` を用いて Execution を強制停止させる目的で使用します（運用上の運用ルールを定めてください）。

---

## 開発・拡張のヒント

- DuckDB を使ったリサーチ系は外部 API を呼ばずに高速に集計できます。prices_daily / raw_financials などのテーブルを準備しておくと即座に動作検証できます。
- AI 呼び出し部分（news_nlp._call_openai_api, regime_detector._call_openai_api）はテストでモックしやすいように分離されています。ユニットテストではこれらを差し替えて deterministic なテストを実装してください。
- position_sizing / risk_adjustment は純粋関数（副作用なし）として設計されているため、単体で検証しやすいです。

---

以上が本リポジトリの概要と基本的な使い方です。その他、個別モジュールの詳細はソース内ドキュメント（docstring）を参照してください。必要であれば README を特定の実行例（systemd サービス化、Docker 化、CI 設定）向けに拡張できます。