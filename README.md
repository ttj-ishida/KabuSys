# KabuSys

日本株自動売買システム（KabuSys）のリポジトリに含まれる主要モジュールの README です。  
このドキュメントはプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム（研究・ペーパートレード・本番対応）です。  
主な設計方針は以下の通りです。

- DuckDB / SQLite を用いたデータ処理と監視（分析用 / 監視用 DB を分離）
- 明確に分離されたモジュール群（ポートフォリオ構築・リスク制御・発注エンジン・監視・研究ツール・AI 補助）
- 環境変数 / .env を利用した設定管理。対話式ウィザードと検証ツールを提供
- Paper Trading（モックブローカー）をサポートし、本番 DB と分離して安全に検証可能
- OpenAI（LLM）を利用したニュース NLP / レジーム判定のためのインターフェースを備える（API キー必須）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式 .env 生成ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行エンジン
  - 発注エンジン起動スクリプト（`run_execution.py`）
  - Paper Trading モード（`KABUSYS_ENV=paper_trading`）では MockBroker を使用し `data/paper_trading.db` に記録

- 監視
  - System / Trade / Risk Monitor（監視データを SQLite に永続化）
  - Monitoring 起動スクリプト（`run_monitoring.py`）
  - Kill Switch（ドローダウンやポジション上限で ExecutionEngine を停止するフラグ）
  - アラート送信フローとログ管理

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分 / スコア配分、リスク補正（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- 研究・分析ツール
  - ファクター計算（Momentum / Value / Volatility）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
  - DuckDB を用いた高速分析

- AI（LLM）連携
  - ニュースのセンチメント分析（`kabusys.ai.news_nlp.score_news`）
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI（gpt-4o-mini など）を用いたバッチ評価・堅牢なリトライ実装

- 運用補助ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

- ユーティリティ
  - ログ設定（コンソール + 日次ローテーション、`kabusys.utils.logging_setup`）
  - プロセス優先度 / CPU affinity 設定（`kabusys.utils.process_priority`）
  - 監視 DB レイヤ（`kabusys.monitoring.monitoring_db`）

---

## 環境変数（主要）

必須（起動前に設定が必要／`.env.example` 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨・よく使う設定:
- KABUSYS_ENV — 実行環境（`development` / `paper_trading` / `live`）デフォルト: `development`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（`instant` / `partial` / `never` / `reject`。デフォルト: `instant`）
- LOG_LEVEL — ログレベル（`INFO` 等）
- OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp / regime_detector）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (`0`/`1`)。本番では `0` 推奨

監視ループのポーリング間隔:
- MONITOR_POLL_INTERVAL — `run_monitoring` のポーリング秒数（整数、デフォルト 60 秒）

ファイルフラグ・PID:
- data/kill.flag — Kill Switch（ExecutionEngine を停止させる）
- data/stop_requested.flag — 外部からプロセス（monitoring/execution）を止めるための簡易フラグ
- data/execution.pid — ExecutionEngine の PID（デフォルト）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、Python 仮想環境を作成
   - 推奨 Python: 3.10+
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 必要パッケージをインストール
   - コア依存（このリポジトリのコードで参照される主なライブラリ）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（`validate_config` の YAML 検証を有効にする場合）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. .env の作成
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成して必要な環境変数を設定してください（.env は Git 管理外にすること）。

4. 設定検証
   - 基本的な設定チェックを行う:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も失敗にしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリ作成
   - 必要に応じて `data/` や `logs/` を作成します。ログディレクトリは自動的に作成されますが権限などで失敗する場合があります。
     ```
     mkdir -p data logs
     ```

---

## 使い方（代表的な実行例）

- ExecutionEngine（発注エンジン）を起動
  - 標準（環境に依存して paper_trading か live が選ばれます）
    ```
    python -m kabusys.run_execution
    ```
  - 注意: `KABUSYS_ENV=paper_trading` の場合、モックブローカーを使用して `data/paper_trading.db` に記録されます。本番では `KABUSYS_ENV=live` を設定してください。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でループ間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（`SQLITE_PATH`）を参照します（Paper トレード環境でも監視は本番 DB を参照する設計になっています）。

- 設定ウィザード（対話式 .env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成ツール
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB は `data/paper_trading.db`。`--db PATH` で変更可能。
  - レポートでは稼働率、注文成功率、送信率、P95 レイテンシなどをチェックします。

- AI 関連（プログラム的呼び出し）
  - ニュース NLP（銘柄毎センチメントを ai_scores に書き込む）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 4, 20), api_key="sk-...")
    ```
  - レジーム判定
    ```py
    from kabusys.ai.regime_detector import score_regime
    n = score_regime(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```

- Kill Switch
  - `data/kill.flag` が存在すると ExecutionEngine に停止シグナルを送る設計です。Monitoring が条件を検出した場合に書き込まれます。
  - 起動時に kill.flag を消したい場合は `.env` の `KILL_FLAG_CLEAR_ON_START` を `1` にできますが、本番では `0` 推奨。

---

## 運用上の注意

- 本番 `KABUSYS_ENV=live` を設定する前に `validate_config` で設定を十分確認してください。`validate_config` は live 環境で追加警告を出します。
- OpenAI API を使う機能は API キーが必要です。鍵の漏洩に注意し `.env` は絶対にコミットしないでください。
- Paper Trading は本番 DB と分離されるよう設計されていますが、設定を誤ると本番データに影響する可能性があるため環境変数の確認を徹底してください。
- ログは `logs/<app_name>.log` に日次ローテートで保存されます。ログディレクトリの権限に注意してください。
- `run_execution` / `run_monitoring` は外部の stop フラグ（`data/stop_requested.flag`）を検知して安全に終了します。運用時はこれを用いて自動停止が可能です。

---

## ディレクトリ構成（主要ファイル）

リポジトリのソースは `src/kabusys` 以下にあります。主な構成を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、.env 自動読み込み
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 層（スキーマ定義・読み書きユーティリティ）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（flag ファイル書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - alert_manager.py — アラート送信管理（存在）

  - execution/
    - execution_engine.py — 発注エンジン（存在）
    - broker_factory.py — ブローカークライアント生成（Mock / 本番切替）
    - order_manager.py — 注文管理
    - order_repository.py — 注文永続化（SQLite）
    - reconciler.py, risk_manager.py, ...（発注ロジック関連）

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・aggregate cap
    - risk_adjustment.py — セクターキャップ / レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
    - __init__.py

  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

---

## 開発・拡張のヒント

- DuckDB へのスキーマやテーブル命名がコードに依存しているため、外部データのロード時はテーブル名（`prices_daily`, `raw_financials`, `raw_news`, `ai_scores`, `market_regime` など）を揃えてください。
- AI モジュールは OpenAI SDK の例外種別を考慮した堅牢な実装になっています。テスト時は `_call_openai_api` をモックすると容易にユニットテスト可能です。
- ポートフォリオ構築やポジションサイズ系の関数は純粋関数として実装されているため単体テストが容易です（状態副作用なし）。

---

不足している点や、README に加えてほしい具体的なコマンドや設定例があれば教えてください。必要ならサンプル .env の雛形や典型的な systemd / Supervisor の起動スクリプト例も作成します。