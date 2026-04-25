# KabuSys

日本株自動売買プラットフォームの一部（ライブラリ／起動スクリプト群）です。本リポジトリには、実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI を用いたニュース NLP / レジーム判定などのユーティリティが含まれます。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）の起動および管理（run_execution.py）
- システム／注文／リスク監視（run_monitoring.py および monitoring パッケージ）
- ポートフォリオ構築と銘柄別資金配分ロジック（portfolio パッケージ）
- ファクター計算・特徴量探索（research パッケージ）
- ニュースを LLM でスコアリングする AI モジュール（ai パッケージ）
- 環境設定ウィザード（config_setup.py）と設定検証ツール（validate_config.py）
- 運用支援ツール（例: paper_trading 用検証レポート生成スクリプト）

設計方針の一例:
- 本番用 DB パスとペーパートレード用 DB を分離
- LLM 呼び出しはリトライ/バリデーションを備えフェイルセーフ動作
- .env をプロジェクトルートから自動読み込み（必要に応じて無効化可能）

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine の起動（KABUSYS_ENV により本番 / ペーパー挙動切替）
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 環境設定
  - python -m kabusys.config_setup: .env を対話式で生成/更新するウィザード
  - python -m kabusys.validate_config: 設定の静的検証（--strict で警告も失敗に）
- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / monitoring_db
  - kill.flag による ExecutionEngine 停止シグナル生成
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター上限、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースの銘柄別センチメントスコア生成（OpenAI を利用）
  - マクロニュース + ETF MA を使った市場レジーム判定（LLM + ルールのハイブリッド）
- 運用ツール
  - paper_verification_report: ペーパートレード DB から運用検証レポートを出力

---

## 必要要件（推奨）

Python 3.10+ を想定しています。主な Python パッケージ（例）:

- duckdb
- psutil
- openai
- (任意) PyYAML — validate_config の YAML 検証で使用

実際の requirements.txt は本リポジトリに含まれていないため、使用する機能に応じて上記パッケージをインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存関係をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. 環境変数（.env）の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 手動: プロジェクトルートに `.env` を作成。主な環境変数の例は以下。

4. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告を厳格に扱う:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 主要な環境変数（要設定 / 任意）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 主要:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し DB を分離
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用）

簡単な .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方

- 実行エンジン（ExecutionEngine）を起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient・専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
    - 起動時、Priority を "high" に設定し PID ファイルを data/execution.pid に書きます。
    - data/stop_requested.flag が存在すると起動やループ内で停止処理します。

- 監視ループ（SystemMonitor）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）をオーバーライドできます（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path を参照して永続化します（環境にかかわらず production sqlite_path を使用）。

- .env（環境設定）ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラム的に利用）
  - ニューススコア付け:
    ```py
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```
  - これらは DuckDB のテーブル (prices_daily, raw_news, news_symbols, ai_scores, market_regime 等) を前提とします。

- ログ
  - デフォルトでコンソール（stdout）とファイル出力（logs/<app_name>.log）を併用します。
  - 日次ローテーション（30 日分保持）。

- Kill Switch / 停止フラグ
  - monitoring が Kill 条件を満たすと `data/kill.flag` に理由を書き込み、ExecutionEngine を停止させます。
  - 外部から停止を指示するには `data/stop_requested.flag` を作成します（run_* スクリプトはこれを検知して終了します）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル群（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py       — （アラート送信管理: LINE 等の実装を想定）
    - trade_monitor.py       — （注文ログの監視、滞留・異常検出）
  - execution/
    - （ExecutionEngine, OrderManager, BrokerFactory 等の実装を想定）
  - portfolio/
    - portfolio_builder.py   — 候補選定・等重・スコア重み
    - position_sizing.py     — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP / LLM 呼び出し・バリデーション
    - regime_detector.py     — レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記は実装済みファイルの主要抜粋です。追加のサブモジュールや実装ファイルが存在することがあります。）

---

## 運用上の注意 / ベストプラクティス

- .env は機密情報を含むため Git には絶対コミットしないでください（config_setup.py のヘッダーにも記載あり）。
- production（KABUSYS_ENV=live）で実行する前に `python -m kabusys.validate_config` で設定を検証してください。
- OpenAI 等の外部 API を利用する機能は API キーが必要です。キーの漏洩に注意してください。
- ペーパートレード（paper_trading）は本番 DB と分離されるよう設計されています。必ず PAPER_TRADING_SQLITE_PATH を分けて運用してください。
- kill.flag / stop_requested.flag / execution.pid などのフラグ／PID ファイルの管理は運用手順に明文化してください（自動化スクリプト等で消し忘れがあると起動しないことがあります）。
- DuckDB / SQLite ファイルはバックアップを検討してください（障害時のリカバリ）。

---

## 参考コマンドまとめ

- 環境ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に以下を追加できます:
- 各環境変数の完全な一覧（現在の README より詳細）
- 実行エンジン / ブローカークライアントの設計図（Flow）
- 例外ハンドリング・監視アラートの詳細
- テストの実行方法や CI 設定例

どの情報を追加したいか教えてください。