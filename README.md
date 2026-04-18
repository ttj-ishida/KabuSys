# KabuSys

日本株向け自動売買システム（KabuSys）のコードベース README（日本語）

このリポジトリは、発注エンジン（ExecutionEngine）、監視システム、ポートフォリオ構築、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定等の補助ツールを含む自動売買プラットフォームの実装です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群から構成されます。

- 発注/実行エンジン（本番またはペーパートレード切替）
- システム・注文・リスク監視（ログ永続化: SQLite）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リサーチ（ファクター計算、特徴量解析、IC計算）
- AI 補助（ニュースのセンチメント評価、レジーム判定：OpenAI API を利用）
- 運用用ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、本番 API 呼び出しは必要箇所に限定し、データ解析は DuckDB を中心に行い、監視・ログは SQLite に保存します。ペーパートレードは本番 DB と完全分離して動作します。

---

## 主な機能一覧

- Execution:
  - ExecutionEngine を使った注文管理（OrderManager / RiskManager / Reconciler 等）
  - KABUSYS_ENV に応じて MockBroker（paper_trading）を使用
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存監視
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、kill flag 書込み
  - MonitoringEngine: 各 Monitor を束ねて定期実行
- Portfolio:
  - 候補選定、等ウェイト・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数適用
- Research:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI:
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント（ai_scores へ挿入）
  - regime_detector: ETF とマクロニュースを合成して daily regime を判定
- ユーティリティ:
  - 環境設定ウィザード（.env 生成: `kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - ペーパートレード検証レポート（`kabusys.tools.paper_verification_report`）
  - ロギング設定ユーティリティ、プロセス優先度設定 など

---

## 前提（Prerequisites）

- Python 3.10 以上（typing に `|` を使うため最低 3.10 推奨。3.11 を推奨）
- SQLite（標準ライブラリ）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定 YAML の検証に任意）
- ネットワーク接続（kabuステーション API / OpenAI を使用する場合）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成し依存をインストール（上記参照）
3. 初期設定（.env）を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成してください。
   - 自動ロード: プロジェクトルートに `.env` / `.env.local` があればライブラリ起動時に自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになる
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータベースファイル（data/ 以下）や logs ディレクトリの作成は自動で行われますが、権限等に注意してください。

---

## 主要な環境変数（代表）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DB 関連:
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- ログ:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- ペーパートレード:
  - PAPER_FILL_MODE（instant/partial/never/reject）
- Kill Switch 関連:
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- その他:
  - OPENAI_API_KEY（AI 機能を使う場合）

注意: Settings モジュールは自動で .env を読み込みます（プロジェクトルートの特定に .git または pyproject.toml を使用）。CWD に依存しないロード方式です。

---

## 使い方（起動・主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - 動作概要:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に記録します。`live` の場合は本番 sqlite_path を使用。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
    - 実行中は `data/execution.pid` に PID を書きます（停止時は削除）。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に「本番の sqlite_path（SQLITE_PATH）を使用」します（monitoring は環境にかかわらず本番 DB を参照）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが終了します。

- 設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb connection と target_date を渡して実行
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    ```

---

## 停止 / KillSwitch / フラグの扱い

- stop_requested.flag:
  - run_monitoring.py / run_execution.py は起動中に `data/stop_requested.flag` の存在を確認し、存在すると安全にループを終了します。
  - 通常は運用側が停止要求ファイルを作成してプロセスを終了させます。

- kill.flag:
  - KillSwitch はリスク条件（例: ドローダウンやポジション上限）を満たした場合に `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Engine 起動時に kill.flag を自動クリアします（本番では危険なためデフォルトは 0）。

- PID ファイル:
  - `data/execution.pid` に ExecutionEngine の PID を書きます。

---

## ログ

- ロギングはルートロガーに統一的に設定されます（kabusys.utils.logging_setup.setup_logging を用いる）。
- デフォルトログディレクトリ: `logs/`。アプリ名ごとにファイル名が生成されます（例: logs/execution.log, logs/monitoring.log）。
- コンソール出力は stdout へ、ファイルは日次ローテーション（30日分保持）となります。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なパッケージ/モジュールを抜粋します（`src/kabusys` 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                    — Execution 関連（OrderManager, RiskManager 等）
    - (各実装ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - pipeline.py                  — データ取得/更新パイプライン（DuckDB 連携）
    - stats.py                     — 正規化ユーティリティなど
  - monitoring/, execution/, portfolio/, research/ の詳細実装ファイル多数

（上記は抜粋です。実際のファイル構成はリポジトリツリーを参照してください。）

---

## 開発・運用上の注意点

- 自動で .env を読み込みますが、OS 環境変数は優先されます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 機能は OpenAI API キー（OPENAI_API_KEY）が必要です。API 失敗時はフェイルセーフとして処理を継続するよう設計されていますが、結果に注意してください。
- monitoring は常に本番 sqlite_path（SQLITE_PATH）を参照します。ペーパートレード用 DB は Execution 側で切り替えられます（KABUSYS_ENV=paper_trading）。
- データ鮮度チェック等は DuckDB の `prices_daily` や raw_news テーブルのデータに依存します。リサーチや AI 部分は入力データの品質に影響されます。
- ログディレクトリや DB ファイルの書き込み権限を運用環境で事前に確認してください。
- 本番運用前に `python -m kabusys.validate_config` を必ず実行し、警告・エラーを確認してください。

---

## サンプル .env（抜粋）

以下は最低限必要な項目の例（`.env` に絶対にコミットしないでください）。

KabuSys は config_setup で生成することを想定しています。

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx (AI 機能利用時)
KILL_FLAG_CLEAR_ON_START=0
```

---

必要に応じて README をプロジェクトの実行ポリシーや運用手順（デプロイ手順、監視/アラートの受信先設定、バックアップ方針など）に合わせて拡張してください。質問や特定の起動方法の例（systemd ユニットファイル、Docker 化など）が必要であれば教えてください。