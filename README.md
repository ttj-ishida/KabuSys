# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注・リスク管理、監視、及び AI を使ったニュース NLP を統合した自動売買プラットフォームの一部です。DuckDB / SQLite をデータストアに使用し、kabuステーション API（または Paper Trading のモック）経由で注文実行を行います。

---

## プロジェクト概要

主な目的は以下です。

- 日次／リアルタイムのファクタ計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み計算・サイズ計算）
- 実際の発注を担う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働・注文の監視（Monitoring）
- ニュース記事を LLM でスコアリングして投資判断に活用（AI モジュール）
- 設定ウィザード・検証ツール・運用レポート（CLI ツール群）

---

## 主な機能一覧

- 設定ウィザード（`.env` を対話的に生成／更新）: `python -m kabusys.config_setup`
- 設定検証（環境変数・config YAML の存在確認）: `python -m kabusys.validate_config`
- ExecutionEngine 起動（本番 / ペーパー分離）: `python -m kabusys.run_execution`
  - KABUSYS_ENV=`paper_trading` 時は MockBrokerClient を使用し専用 SQLite（`data/paper_trading.db`）へ記録
- Monitoring 起動（SystemMonitor のポーリング）: `python -m kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
- Paper Trading 検証レポート生成: `python -m kabusys.tools.paper_verification_report`
- DuckDB ベースのファクター計算（momentum / volatility / value 等）
- ニュース NLP による銘柄別センチメントスコア取得（OpenAI 使用）
- Kill Switch による安全停止（dradawdown／ポジション上限等で kill.flag を書き込み Execution を停止）

---

## 前提条件（開発 / 実行環境）

- Python 3.10+（型ヒント等を利用）
- pip で以下の主要ライブラリをインストール
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- SQLite（Python 標準ライブラリの sqlite3 を利用）
- 任意: kabuステーション 等の外部 API クライアント（実行時に必要）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数の準備
   - 対話式ウィザードで `.env` を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 必要に応じて OPENAI_API_KEY（AI モジュール利用時）
4. 設定検証（推奨）:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。

注意:
- 自動で `.env` を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml）を基に `.env` / `.env.local` を順に読み込みます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（起動コマンド）

- 実行エンジン（Execution）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、Paper 用 DB（デフォルト: `data/paper_trading.db`）へ記録し、本番 DB と完全分離します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
  - 実行中に `data/stop_requested.flag` を作成すると実行エンジンは停止します。

- 監視（Monitoring）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で変更可能（正の整数）。
  - 監視は MonitoringDB（SQLite）にログを吐きます（`Settings.sqlite_path` を参照）。
  - 停止フラグ（`data/stop_requested.flag`）を検出するとループを抜けて終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db PATH` で SQLite ファイルを指定できます（環境変数 `PAPER_TRADING_SQLITE_PATH` も利用可）。

- AI モジュール（ライブラリ関数として利用）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は DuckDB 接続、target_date は datetime.date
    score_news(duckdb_conn, target_date, api_key="...")  # api_key 省略可（OPENAI_API_KEY にフォールバック）
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトあり／省略可能）:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: `development`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（デフォルト: `INFO`）
- OPENAI_API_KEY — OpenAI を使う場合に必須（AI モジュール）

監視関連:
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — Kill Switch / PID 管理関連設定

（詳しくは `kabusys.config.Settings` を参照してください）

---

## ファイル・フラグの説明（運用メモ）

- data/stop_requested.flag
  - 存在すると run_execution / run_monitoring の起動ループが停止／起動阻止のトリガーとなります（手動で停止する際に利用）。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを送る用途で使用されます。
- data/execution.pid
  - ExecutionEngine の PID を書き込むファイル（設定によりパスは変更可能）。
- logs/
  - `kabusys.utils.logging_setup.setup_logging` により `logs/<app_name>.log` が日次ローテーションで出力されます（デフォルト 30 日保存）。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュールと役割:

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（自動 .env ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注／リスク管理／ブローカークライアントの実装（Engine 起動用）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル初期化・CRUD ヘルパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視ロジック
  - monitoring_engine.py, kill_switch.py, alert_manager.py — 監視の統合と通知

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・丸め
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — ファクター計算（DuckDB を利用）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — MA とマクロ記事を組み合わせて市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成

---

## 開発・運用上の注意点

- 本番運用時は KABUSYS_ENV を `live` に設定してください。`live` 時には追加のガード（LINE 通知設定確認等）を行っています。
- `.env` を絶対にリポジトリにコミットしないでください（`config_setup.py` のヘッダにも注意書きあり）。
- Monitoring は常に本番 sqlite_path（`Settings.sqlite_path`）を参照します。Paper Trading は Execution 側のみ専用 DB に分離されます。
- OpenAI API の呼び出しは外部コストが発生します。API レート制限やエラー時のフェイルセーフ（スコア＝0）実装あり。
- ローカルテスト時に自動環境読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml
  ```

- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じてこの README をプロジェクト固有の手順（Docker, systemd ユニット、CI 設定、requirements.txt 作成など）に合わせて拡張してください。追加で API キーの取り扱い、Dockerfile、ユニットテストの実行方法などの記載が必要なら教えてください。