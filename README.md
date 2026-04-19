# KabuSys

日本株自動売買システムのリファレンス実装。価格データや財務データを用いたファクター計算、ポートフォリオ構築、発注エンジン（実取引 / ペーパートレード）、監視・アラート、LLM を使ったニュースセンチメント評価などを含むモジュール群を提供します。

---

## 主な機能

- ExecutionEngine
  - 本番（live）・ペーパートレード（paper_trading）に対応
  - Broker クライアント抽象化（環境により MockBrokerClient を使用）
  - 注文管理・リスク管理・照合（reconciler）を組み合わせた実行フロー
- Monitoring
  - システム・データ鮮度・注文の監視
  - Kill Switch（条件に応じて ExecutionEngine を停止するフラグ）
  - 監視ログの永続化（SQLite）
- Portfolio Construction（純粋関数群）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム調整
- Research / ファクター計算
  - Momentum / Volatility / Value などのファクター計算（DuckDB を使用）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI）連携
  - ニュース記事のセンチメントスコアリング（ai_scores テーブルへ書込）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
  - API 失敗時のフェイルセーフ実装（リトライ・フォールバック）
- 運用支援ツール
  - 環境設定ウィザード（.env 作成 / 更新）
  - 設定検証 CLI（.env / config/*.yaml の簡易チェック）
  - ペーパートレード検証レポート生成スクリプト

---

## セットアップ手順（概要）

必要条件: Python 3.10+（typing の union 演算子 `|` を利用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 最低限必要なライブラリ（例）:
     ```
     pip install duckdb psutil openai
     ```
   - YAML 内容検証を行うには PyYAML をインストール:
     ```
     pip install pyyaml
     ```

4. 環境変数の準備
   - 対話式ウィザードで `.env` を生成:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動で作成（例は下段の「主な環境変数」参照）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL 扱いにする場合は `--strict` を付与。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（デーモン化は含まず）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中は data/execution.pid に PID を書き込みます（Settings.pid_file_path で上書き可能）。

- Monitoring（ポーリング監視）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依存しません）。
  - 停止は data/stop_requested.flag の作成で行えます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションか環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます（デフォルト: data/paper_trading.db）。

- AI 関連（コード内 API）
  - ニュースのスコア付け: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` を使用。

---

## 主な環境変数（要/任意・デフォルト）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用・データベース
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）

AI 関連
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング／レジーム判定で必要）

運用フラグ
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env ファイルを読み込む処理をスキップします（テストなどで利用）。

注意: `.env` は絶対にリポジトリにコミットしないでください。

---

## 運用ノート（停止・フラグ）

- ExecutionEngine を強制停止させたい場合:
  - Kill Switch がトリガーされると `data/kill.flag` が書き込まれ、Engine は停止します。
  - kill.flag を手動でクリアするには KillSwitch.clear() を呼ぶか、ファイルを削除してください:
    ```
    rm data/kill.flag
    ```
- run_monitoring や run_execution の停止:
  - 監視ループやエンジンは `data/stop_requested.flag` の存在を監視しています。停止したい場合はこのファイルを作成してください。
- PID ファイル
  - ExecutionEngine は PID を data/execution.pid（Settings.pid_file_path）に書き込みます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みユーティリティ
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / affinity 設定
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装に依存するファイル群)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - data/ (ランタイムで生成される想定)
    - monitoring.db (SQLITE_PATH のデフォルト)
    - kabusys.duckdb (DUCKDB_PATH のデフォルト)
    - execution.pid / stop_requested.flag / kill.flag

（上記は主要なファイル群の抜粋です。実際の実装はさらにモジュールが存在します。）

---

## 参考・トラブルシューティング

- DuckDB / SQLite 関係
  - monitoring は本番用 sqlite_path を常に参照します。ペーパートレード DB は PAPER_TRADING_SQLITE_PATH で分離可能です。
- OpenAI 呼び出し
  - レート制限やネットワークエラー時は指数バックオフでリトライします。API キー設定を忘れると例外が発生します。
- ロギング
  - setup_logging() により stdout と日次ローテートファイル（logs/<app_name>.log）に出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- 環境ファイルの自動ロード
  - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要があれば README に含める例 .env テンプレートや、各コンポーネント（ExecutionEngine / MonitoringEngine）のより詳細な起動例・構成例も追記します。どの情報を優先して載せたいか教えてください。