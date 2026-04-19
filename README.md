# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注エンジン、監視、研究ツール、AI（ニュースセンチメント）連携などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の機能を持つモジュール型の自動売買基盤です。

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注実行エンジン（execution） — paper/live 切替可能
- 監視コンポーネント（monitoring） — システム／注文／リスク監視、Kill Switch
- AI 連携（ai） — ニュースセンチメント、レジーム判定（OpenAI 使用）
- 運用ユーティリティ（config_setup, validate_config, tools）

主要な起動スクリプト:
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor（監視ループ）起動スクリプト
- tools/paper_verification_report.py — ペーパートレード検証レポート出力

---

## 機能一覧

- 環境ごとの設定管理（Settings クラス）
  - KABUSYS_ENV: development / paper_trading / live
  - .env 自動読み込み（プロジェクトルートを基準）
- 発注エンジン
  - paper_trading 時は MockBrokerClient を使用し paper DB に分離記録
  - リスク管理（RiskManager）、注文管理（OrderManager）など
  - 停止フラグ（data/stop_requested.flag, data/kill.flag）対応
- 監視
  - システムリソース、データ鮮度、発注ログなどを定期記録（SQLite）
  - リスク監視（ドローダウンや保有上限）と Kill Switch
  - アラート送信フック（AlertManager で統合）
- 研究・分析
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索・IC 計算・統計サマリー
- AI（OpenAI）
  - ニュースを用いた銘柄別センチメント算出（ai.news_nlp）
  - マクロニュースと ma200 を合成したレジーム検出（ai.regime_detector）
  - API レート制限や 5xx 等へのリトライ実装あり
- 運用ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート出力ツール（tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨
- 仮想環境の利用を推奨（venv / virtualenv / poetry 等）

1. レポジトリをクローンし、プロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt 等がある場合はそちらを参照してください。主な依存例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config の YAML 検証に使用。任意）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数の初期化（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。生成後、設定を検証:
   ```
   python -m kabusys.validate_config
   ```

5. データディレクトリの作成（必要に応じて）
   - デフォルトで使用されるパス:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite 監視 DB)
     - data/paper_trading.db (ペーパートレード時の SQLite)
     - logs/ ディレクトリ（ログファイル保存）

   ウィザードや起動時に自動作成されることもありますが、必要に応じて事前に作成してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 時の約定モード: instant | partial | never | reject) — default: instant
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔[秒], default: 60)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨

例 (.env) — ウィザードで生成されます:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx
```

---

## 使い方（起動・運用）

### 1) 設定検証
対話式設定後に検証:
```
python -m kabusys.validate_config
# strict モード（警告もエラー扱い）
python -m kabusys.validate_config --strict
```

### 2) ExecutionEngine（発注エンジン）起動
- paper_trading の場合、設定により MockBrokerClient を使用して data/paper_trading.db に記録します。
- 起動前に data/stop_requested.flag が存在すると起動しません。

起動:
```
python -m kabusys.run_execution
```

停止:
- 実行中に data/stop_requested.flag を作成すると、エンジンは検知して停止します（監視や運用からの停止信号）。
- Kill Switch（監視側）が検出した場合は data/kill.flag が書き込まれ、ExecutionEngine 側で処理されます。

### 3) 監視ループ（Monitoring）起動
監視は Settings で指定された sqlite_path（監視 DB）を使用します（環境に依らず本番 sqlite_path を参照）。

起動:
```
# ポーリング間隔指定（秒）:
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

停止:
- data/stop_requested.flag を作成すると監視ループが終了します。

### 4) ペーパートレード検証レポート
ペーパートレード用 DB（デフォルト: data/paper_trading.db）から検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### 5) AI 機能
- ニュースセンチメントやレジーム検出は OpenAI API を利用します。環境変数 OPENAI_API_KEY を設定してください。
- 例:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

（上記はプログラム内 API です。呼び出す際は DuckDB 接続を渡します。）

---

## 運用上の注意点

- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- process_priority を High に設定するユーティリティが起動時に呼ばれます（管理者権限や OS により設定できない場合は警告のみ）。
- Kill Switch はリスク監視が一定条件を満たした場合に data/kill.flag を作成します。ExecutionEngine は kill.flag を検知して発注停止を行います。KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では自動クリアを無効にすることを推奨）。
- Paper Trading は本番 DB と分離して運用されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成

主なファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - data/  (データ用ディレクトリ: DB, フラグファイル等)
  - logs/  (ログ出力ディレクトリ)
  - ai/
    - news_nlp.py — ニュースセンチメント (OpenAI)
    - regime_detector.py — レジーム検出
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリにはさらに多くのモジュール／ファイルが含まれている可能性があります。上は主要ファイルの一覧です。）

---

## 開発者向けメモ

- DuckDB 接続を受け取る研究モジュール（research）は、prices_daily / raw_financials 等のテーブルに依存します。データ投入は別途データパイプラインを参照してください。
- AI 関連モジュールは OpenAI SDK の仕様変更に注意して下さい（レスポンスパース・例外処理を慎重に）。
- monitoring_db.init_monitoring_db() は既存 DB に対するマイグレーション（カラム追加）を含み、冪等に動作します。
- 単体テストでは環境変数自動ロードを無効化する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

---

必要であれば、README を英語版に翻訳したり、セットアップを docker/docker-compose で自動化する手順サンプルを追加できます。どの情報を優先して追記しますか？