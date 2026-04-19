# KabuSys

日本株自動売買システムのリポジトリ（パッケージ名: `kabusys`）の README。  
ここではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたパッケージです。主な要素は以下です。

- ExecutionEngine: 発注・リスク管理・注文管理を行う実行エンジン（本番 / ペーパートレード対応）。
- Monitoring: システム稼働・注文状況・リスクを監視し、必要時に Kill Switch を書き込むことで ExecutionEngine を停止可能。
- Research: DuckDB 上の価格・財務データを用いたファクター計算・特徴量解析。
- AI モジュール: OpenAI を用いたニュースの NLP 評価（センチメント）・市場レジーム判定。
- ユーティリティ群: 設定管理、ログ設定、プロセス優先度設定、ツールスクリプト等。

設計方針としては「テスト容易性」「ルックアヘッドバイアスの回避」「フェイルセーフ（API失敗時の健全なフォールバック）」を重視しています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（.env の対話的生成）: `kabusys.config_setup`
- 設定検証 CLI（.env + config/*.yaml の検証）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し paper_trading 専用 DB に保存
- Monitoring 起動スクリプト: `kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き（デフォルト 60 秒）
- MonitoringEngine: System / Trade / Risk のモニターを束ね、アラートや Kill Switch を発動
- RiskMonitor: ドローダウンやポジション上限の監視とログ化
- KillSwitch: 条件に応じて `data/kill.flag` を作成し ExecutionEngine 停止を指示
- Research: momentum / volatility / value などのファクター計算、forward returns、IC 計算、統計サマリ
- AI:
  - `news_nlp.score_news`: ニュース記事を OpenAI でセンチメント評価して `ai_scores` に保存
  - `regime_detector.score_regime`: マクロニュース + ETF MA で日次レジーム判定し `market_regime` に保存
- ツール:
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`
- データ永続化:
  - DuckDB（分析用）
  - SQLite（監視・発注ログ等）

---

## セットアップ手順（ローカル）

※ Python のバージョンや依存はプロジェクトに合わせて調整してください。以下は一般的な手順例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージのインストール
   - 本プロジェクトで利用される主なパッケージ（参考）:
     - duckdb, psutil, openai, PyYAML（任意）, sqlite3 は標準ライブラリ
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - ※実際の requirements.txt がある場合はそれを使ってください:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数の作成（.env）
   - 対話式ウィザードで `.env` を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、必須変数を確認:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 重要: `.env` は Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

6. データディレクトリ確認
   - デフォルトの DB / PID / フラグパス:
     - DuckDB: `data/kabusys.duckdb`（環境変数 `DUCKDB_PATH` で変更可）
     - SQLite (monitoring): `data/monitoring.db`（`SQLITE_PATH`）
     - Paper trading SQLite: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）
     - PID ファイル・kill flag: `data/execution.pid`, `data/kill.flag`
   - 起動時にディレクトリが自動作成される箇所もありますが、権限などに注意してください。

---

## 使い方（主なコマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（フォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときはペーパートレード（MockBroker）で動作し、`PAPER_TRADING_SQLITE_PATH` に書き込む
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します
  - 実行中は `data/execution.pid` を作成します

- Monitoring を起動（フォアグラウンド）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔はデフォルト 60 秒、`MONITOR_POLL_INTERVAL` で上書き可（秒）
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず）
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # データベースパスを明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ログ設定
  - ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定され、デフォルトは `logs/<app_name>.log`（日次ローテーション、30 日保持）
  - 環境変数 `LOG_DIR` / `LOG_LEVEL` で調整可

---

## 主要な環境変数（まとめ）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — 実行モード（"development" / "paper_trading" / "live"）（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading 時の約定モード（"instant" / "partial" / "never" / "reject"）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- ログ / 起動
  - LOG_DIR — ログディレクトリ（デフォルト: logs）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill_flag を自動クリアする（"1"=有効、デフォルト: "0"）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合に必要）

---

## 実装上のポイント（簡単な説明）

- Settings クラス（`kabusys.config.Settings`）が環境変数をラップ。`.env` の自動ロード機能あり（プロジェクトルートの検出に基づく）。
- `config_setup` は .env の対話式作成ツール。
- `validate_config` は起動前に設定やファイルパス等の健全性をチェック。
- Monitoring 系は SQLite に監視ログを永続化（`monitoring_db.init_monitoring_db` がスキーマ作成・マイグレーションを行う）。
- AI モジュールは OpenAI の Chat Completions（JSON モード）を用いて厳密な JSON レスポンスを期待して処理する。失敗時は基本的に安全側（スコア 0.0 など）でフォールバックする設計。
- プロセス優先度 / CPU affinity 設定ユーティリティを提供（`kabusys.utils.process_priority`）。`psutil` を使用。

---

## ディレクトリ構成（src/kabusys の主なファイルと説明）

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — マクロニュース + MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 層（初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （発注周りの整合性チェック等）※詳細はソース参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 判定
    - monitoring_engine.py — Monitor を束ねてループ駆動するエンジン
    - alert_manager.py —（アラート送信の責務）
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（発注・リスク関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 発注株数決定（単元丸め、リスクベース等）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - data/（データパイプライン・DuckDB 関連：prices_daily などを取得・加工するモジュール）
  - utils/
    - logging_setup.py — ロギング共通設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（上記は主要ファイルの一覧と概要。細かい実装は各ソースをご確認ください。）

---

## よくある運用上の注意

- 本番モード（KABUSYS_ENV=live）では設定ミスにより実注文が発生するため、`validate_config` と `.env` の確認を必ず行ってください。
- Kill Switch（`data/kill.flag`）は本番で重要な安全装置です。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは推奨されません。
- OpenAI を利用する機能は API 料金が発生します。キーの管理と利用頻度に注意してください。
- ログディレクトリや DB の書き込み権限に注意してください（サービス起動ユーザーの権限設定）。

---

必要に応じて README を拡張します。特定項目（例: ExecutionEngine の設定詳細、Broker の実装やモック、DB スキーマ、CI / デプロイ手順）の追記を希望される場合は教えてください。