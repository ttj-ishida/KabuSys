# KabuSys README

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）

概要、機能、セットアップ手順、使い方、主要ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買のためのフレームワークです。  
モジュールは主に以下の目的で構成されています。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視（System / Trade / Risk）および Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- リサーチ（ファクター計算・特徴量解析）
- AI ベースのニュースセンチメント評価（OpenAI API）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証）

設計方針の例:
- 本番 DB とペーパートレード DB の分離
- ルックアヘッド（未来情報）を防ぐ実装
- API 呼び出し失敗時はフェイルセーフで継続（例: AI 呼び出しで 0 にフォールバック）
- 設定を .env から読み込み、対話ウィザードや検証 CLI を提供

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による本番 / paper_trading 切替
  - Paper trading 時は MockBrokerClient を利用し、`data/paper_trading.db` に記録
  - プロセス優先度設定、PID ファイル、停止フラグ対応

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor、TradeMonitor、RiskMonitor を定期ポーリング
  - Kill Switch（一定条件で execution を停止するための flag ファイル生成）
  - 監視用 SQLite DB（`monitoring_db.py`）への永続化

- Portfolio（portfolio パッケージ）
  - 候補選定、等金額 / スコア重み、ポジションサイズ計算、セクター制約、レジーム乗数

- Research（research パッケージ）
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility など）
  - 将来リターン、IC（情報係数）、統計サマリ

- AI（ai パッケージ）
  - ニュースから銘柄ごとのセンチメントを算出し ai_scores に保存（OpenAI 必須）
  - 市場レジーム判定（ETF の MA とマクロ記事センチメントの合成）

- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的生成
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）

---

## 動作環境・前提

- Python 3.10 以上（ソースに `X | None` 型記法を使用）
- 必要パッケージ（主なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を使う場合）
- デフォルトの DB / ファイルパス（変更可、環境変数で上書き）
  - DuckDB: data/kabusys.duckdb (`DUCKDB_PATH`)
  - SQLite (monitoring): data/monitoring.db (`SQLITE_PATH`)
  - Paper trading SQLite: data/paper_trading.db (`PAPER_TRADING_SQLITE_PATH`)
  - PID / Kill flag / Stop flag: data フォルダ内のファイル

推奨: 仮想環境を使用し、依存を pip でインストールしてください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注はモック・専用 DB に記録される
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR（ログファイル保存先、デフォルト logs/）
- OPENAI_API_KEY（AI 機能利用時に必要）
- PAPER_FILL_MODE（paper_trading の約定モード: instant / partial / never / reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）

設定ファイル例はプロジェクトルートの `.env.example` を参照してください（リポジトリに含めることが想定されています）。

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml のある場所）を探索して `.env` / `.env.local` を自動的に読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（基本）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があればそれを使ってください）

3. 初期設定 (.env) を用意
   - 対話式ウィザード: python -m kabusys.config_setup
     - これによりプロジェクトルートに `.env` が生成されます（既存値の更新も可）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要なら）
   - mkdir -p data logs

---

## 使い方（起動・実行例）

基本的にモジュールを直接実行します。

- ExecutionEngine を実行（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - プロセス優先度を "high" に設定し、PID ファイル（デフォルト data/execution.pid）を管理します。

- Monitoring を実行（監視ループ）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。上書きするには環境変数 `MONITOR_POLL_INTERVAL` を設定。
  - Monitoring は "環境にかかわらず" 本番用の `SQLITE_PATH` を使用します（監視データは一元で管理されます）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（DB ファイル指定、環境変数 PAPER_TRADING_SQLITE_PATH が優先される）

- AI スコアリング（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None) など
  - OPENAI_API_KEY が必要（引数で指定することも可能）

注意:
- Stop / Kill フラグ:
  - Monitoring 側がリスク条件で Kill Switch を評価すると `data/kill.flag` を書き込みます（ExecutionEngine は起動時や稼働中にこれを参照して停止します）。
  - `KillSwitch.clear()` により明示的に削除可能。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時にクリアされます（本番では注意）。

---

## 主要コマンド一覧

- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from] [--to] [--db]

---

## ログ

- ログ出力:
  - デフォルトは stdout（コンソール）とファイル（logs/<app_name>.log）
  - ログ設定は kabusys.utils.logging_setup.setup_logging() で統一管理
  - ログレベルは環境変数 `LOG_LEVEL` または引数で指定できます
  - ログファイルは日次ローテーション（30 日保持）

---

## 注意点 / 運用メモ

- プロセス優先度設定（utils.process_priority）は psutil を使います。権限不足の環境では設定に失敗して警告が出ますが、処理は継続します。
- Monitoring は監視 DB（SQLite）を使い、monitoring 用テーブルの作成・マイグレーションを自動実行します（init_monitoring_db）。
- Paper trading は本番 DB と完全分離して動作するよう設計されています（`Settings.is_paper` に基づく挙動）。
- AI 機能を利用する場合は OpenAI API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ・クリップ・フェイルセーフの考慮が実装されていますが、コスト・レート制限に注意してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・パッケージの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — Monitoring 起動スクリプト
    - config.py                       — Settings（.env 読み込み、設定ラッパー）
    - config_setup.py                 — .env 対話ウィザード
    - validate_config.py              — 設定検証 CLI
    - utils/
      - logging_setup.py              — ログ初期化ユーティリティ
      - process_priority.py           — プロセス優先度・CPU affinity
    - execution/                       — 発注エンジン関連（Engine, BrokerFactory 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - risk_manager.py
      - reconciler.py
    - monitoring/
      - monitoring_db.py              — 監視 DB 層（SQLite）
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

（実際のツリ―はリポジトリ全体を参照してください）

---

## 開発・拡張のヒント

- DuckDB を用いてファクター計算や AI 前処理を行うため、prices_daily / raw_financials / raw_news 等のテーブルスキーマに沿ったデータ投入が必要です。
- validate_config.py は起動前の安全チェックとして有効です（--strict で警告も失敗として扱えます）。
- ai モジュールは OpenAI SDK のレスポンス形式に依存します。テストでは API 呼び出し関数をモックする仕組みが各所に用意されています（_call_openai_api のパッチ等）。
- 実運用時は `.env` を絶対に Git にコミットしないこと（config_setup のヘッダにも注意書きあり）。

---

必要であれば README に追記する内容（例: 具体的な設定例、DB スキーマ詳細、Docker / systemd ユニットのサンプル、ユニットテストの実行方法）を教えてください。