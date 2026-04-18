# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注エンジン、監視機構、AI を使ったニュース解析などを含む総合的な自動売買システムのコードベースです。本 README はローカルでのセットアップ・起動・主要機能の使い方をまとめたものです。

注意: .env は機密情報（API トークンなど）を含むため絶対に Git にコミットしないでください。

---

## 概要

- リサーチ（DuckDB ベース）のファクター計算、特徴量探索
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine（発注ロジック、リスク管理、OrderManager 等）
- Monitoring（システム稼働監視、取引ログ、リスク監視、Kill Switch）
- AI モジュール（OpenAI を使ったニュースセンチメント評価／市場レジーム判定）
- CLI ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート生成）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、ただし環境変数が優先）
  - `config_setup` による対話式 .env 生成
  - 設定検証ツール `validate_config`（YAML 構成ファイルの存在/パース検証は PyYAML に依存）

- 実行／監視
  - `run_execution.py`：ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し `data/paper_trading.db` に記録
    - PID ファイル: `data/execution.pid`
    - 停止フラグ: `data/stop_requested.flag`
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプト
    - デフォルトポーリング間隔 60 秒（環境変数 `MONITOR_POLL_INTERVAL` で上書き）
    - 監視ログは production の sqlite_path を使用（環境に依らず）
    - 停止フラグ: `data/stop_requested.flag`

- 監視・アラート
  - システムリソース（CPU／メモリ／ディスク）、Execution プロセスの監視
  - Trade／Risk の監視（滞留注文、約定異常、ドローダウン、ポジション上限）
  - KillSwitch による flag ファイルで Execution 停止指示

- ポートフォリオ（純粋関数群）
  - 候補選定（score / rank ベース）
  - 等分 / スコア加重重み
  - ポジションサイズ計算（ロット丸め、集計キャップ、コストバッファ）
  - セクターキャップとレジーム乗数

- Research（DuckDB）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI（OpenAI）
  - ニュース記事を LLM で評価して ai_scores に書き込み（batch・リトライ・バリデーション実装）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）

- ツール
  - Paper Trading 検証レポート生成（期間指定可）
  - 設定ウィザード / 設定検証 CLI

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 最低限必要となる主なパッケージ（明示例）:
     ```
     pip install duckdb psutil openai
     ```
     - 設定検証で YAML をチェックしたい場合は `PyYAML` を追加:
       ```
       pip install PyYAML
       ```

4. 環境変数 / .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を編集（プロジェクトルート）  
     主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR、デフォルト: INFO)
   - .env の自動読み込み:
     - OS 環境変数 > .env.local > .env の順で読み込まれます
     - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 厳格モード（警告を FAIL 扱い）:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（フォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  - paper trading モードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔の変更:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - 監視ループは `data/stop_requested.flag` を検知すると終了します。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトパスが使われます。

- AI モジュール利用（ライブラリ API）
  - ニュース NLP スコア付け:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
    - API キーは引数 `api_key` か環境変数 `OPENAI_API_KEY` を使用
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
    ```

---

## 注意点 / 運用メモ

- 停止制御:
  - 監視・実行の停止は `data/stop_requested.flag` を作成することで検出して終了します（`run_monitoring.py`, `run_execution.py` が監視）。
  - Kill Switch は重大なリスク条件で `data/kill.flag` を書き込み、ExecutionEngine に停止を指示します。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされますが、本番では 0 を推奨します。

- 実行環境判定:
  - `Settings.env` は `KABUSYS_ENV`（development / paper_trading / live）で決まります。`Settings.is_paper` / `is_live` を参照して挙動を切り替えています。

- DB:
  - DuckDB（分析用）：`DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）
  - SQLite（監視ログ）：`SQLITE_PATH`（デフォルト: `data/monitoring.db`）
  - Paper Trading は `PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）に分離

- ログ:
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトで呼んでいます。
  - デフォルトログディレクトリは `logs/`。`LOG_DIR` 環境変数で変更可能。

- 依存ライブラリの注意:
  - `psutil`：プロセス優先度・CPU 情報取得に使用
  - `duckdb`：リサーチ / AI 集約の SQL 実行に使用
  - `openai`：AI 機能（news_nlp, regime_detector）
  - `PyYAML`：`validate_config` が YAML のパースチェックに使用（任意）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 設定管理（.env ロード、Settings クラス）
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite 永続化層（監視用テーブル）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — （取引監視ロジック、コードベースに実装あり）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py — フラグベースの停止指示
  - alert_manager.py — （アラート送信管理、実装あり）

- execution/
  - execution_engine.py — 発注エンジン本体（EngineConfig 等）
  - broker_factory.py — ブローカークライアント生成
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りのコンポーネント

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュース記事の LLM スコアリング
  - regime_detector.py — 市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに多くのモジュールが含まれます）

---

## 開発・テスト向けヒント

- 自動環境変数ロードを無効にしてテストしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 単体テストでは外部 API 呼び出し（OpenAI など）をモックすることを推奨します（コード内でもテスト可能なようにコールを関数で分離しています）。
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db() や AI のテーブル操作で自動整備・マイグレーションされるよう設計されています。

---

必要であれば、各モジュールの API サンプルや設定項目の詳細（.env のテンプレートや config/*.yaml のフォーマット）を別ファイルで追記します。どの情報を優先して追加しますか？