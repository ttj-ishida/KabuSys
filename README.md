# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリは、発注処理（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI によるニュース分析などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコア機能をモジュール化したコードベースです。主な役割は以下です。

- ExecutionEngine：ブローカークライアントを用いた発注処理（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文状態・リスクをポーリング監視し、kill flag（停止指示）やアラートを管理
- Portfolio：銘柄選定・重み付け・株数計算などのポートフォリオ構築ロジック（純粋関数）
- Research：DuckDB に格納した市場データを用いたファクター計算・特徴量解析
- AI：ニュースを LLM（OpenAI）でスコアリングしてセンチメントや市場レジーム判定に利用
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- Utilities：ロギング設定、プロセス優先度設定、環境設定読み込みなど共通ユーティリティ

設計上の注意点：
- .env / .env.local を自動で読み込み（プロジェクトルート検出）します（無効化可）。
- Paper trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離して `data/paper_trading.db` を用います。
- OpenAI を利用する AI 機能は `OPENAI_API_KEY` が必要です（関数呼び出し時にキーを渡すことも可）。

---

## 機能一覧

- 設定管理
  - .env ウィザード（対話式）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- 実行（Execution）
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - 本番 / ペーパートレード分離（PAPER_TRADING_SQLITE_PATH）
  - リスク管理（RiskManager）、オーダー管理（OrderManager）等（内部モジュール）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプトでポーリング監視（環境変数で間隔上書可）
  - kill/stop フラグ（data/kill.flag, data/stop_requested.flag）による外部停止
  - SQLite ベースの監視ログ（monitoring_db）
- ポートフォリオ
  - 候補選定、等金額/スコア重み、リスク調整（セクター上限）、ポジションサイズ計算
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュース記事を LLM でスコアリング → `ai_scores` へ書込
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 必要環境・依存関係

- Python 3.9+
- 主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config yaml の検証を行う場合、任意）
- 任意:
  - sqlite3（標準ライブラリ）
  - その他（プロジェクトで利用する外部パッケージ）

インストール例（仮の requirements がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
# またはパッケージ化されている場合:
# pip install -e .
```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能で必要

監視関連:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などは Settings で参照

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` を自動読み込みします。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` を作成（対話式ウィザード推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. data / logs ディレクトリ等が自動で作成されますが、適宜権限やパスを確認してください。

---

## 使い方（主要コマンド）

- 実行エンジン起動（Execution）
  - 本番または paper_trading に応じて DB を切り替えます。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中は `data/execution.pid` に PID を書きます。停止指示は `data/stop_requested.flag` を作成することで行えます。

- 監視プロセス起動（Monitoring）
  - ポーリング監視を開始します（MONITOR_POLL_INTERVAL で間隔を調整）。
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite (Settings.sqlite_path) を利用します（環境に依存せず本番 DB を想定）。
  - `MONITOR_POLL_INTERVAL` 環境変数で秒数指定（1 以上）。無効値はデフォルト 60 秒へフォールバック。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  # デフォルト DB は data/paper_trading.db。--db で別ファイル指定可
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI / リサーチ機能の呼び出し（ライブラリ利用）
  - news スコアリング（例）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    # duckdb 接続と api_key を渡して呼び出す
    ```

- ログ:
  - デフォルトのログディレクトリは `logs/`。`kabusys.utils.logging_setup.setup_logging` によって stdout と日次ローテートファイルが設定されます。

---

## 実行時のファイル / フラグ

- data/execution.pid — 実行エンジンの PID（ExecutionEngine）
- data/stop_requested.flag — run_execution / run_monitoring の外部停止トリガー
- data/kill.flag — KillSwitch が起動時に書き込む（ExecutionEngine を止める目的）
- SQLite / DuckDB: デフォルトは data/monitoring.db（SQLite） / data/kabusys.duckdb（DuckDB）

---

## ディレクトリ構成

主要なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/設定読み込み
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイルは上記以外にも多数あります。詳細はリポジトリツリーを参照してください）

---

## 開発者向けメモ

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- テスト時や CI で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使う分析/リサーチ処理はローカルにデータを用意してから実行してください（prices_daily / raw_financials テーブル等）。
- AI 機能をテストする場合は OpenAI の API 制限・料金に注意してください。テストはモック化推奨です（モジュール内の API 呼び出しを patch 可能）。

---

## よくある質問 / トラブルシュート

- ログファイルが作成されない:
  - `logs/` ディレクトリの作成に失敗するとコンソール出力のみになります。権限を確認してください。
- MONITOR_POLL_INTERVAL を指定しているが無視される:
  - 環境変数名や値（整数）を確認してください。不正値はデフォルト 60 秒にフォールバックします。
- Paper Trading の DB が本番 DB と混ざっている:
  - `KABUSYS_ENV=paper_trading` にすると `paper_sqlite_path`（PAPER_TRADING_SQLITE_PATH）を使用する設計です。環境変数を確認してください。

---

この README はコードベースの主要点をまとめたサマリです。追加の実行例や詳細設計（API の仕様、Strategy / Execution の詳細）はプロジェクト内のドキュメント（例えば PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であれば README を拡張して起動例やデプロイ手順、環境別運用手順を追記できます。