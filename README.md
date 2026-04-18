# KabuSys

日本株自動売買フレームワーク（ライブラリ＋起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム／研究プラットフォームです。  
主な目的は以下です。

- 市場データを使った因子計算・特徴量探索（Research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- ExecutionEngine による発注制御（本番・ペーパートレードを分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュース NLP（OpenAI）を使ったセンチメント評価とレジーム判定
- 運用検証用のユーティリティ（例: Paper Trading 検証レポート）

設計方針として、DB（DuckDB / SQLite）をデータソースにし、LLM 呼び出しはオプション（OpenAI API）で行います。実行スクリプトはプロセス優先度の調整やログ設定を一貫して行います。

---

## 機能一覧

- Config / Env 管理
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 起動前検証（python -m kabusys.validate_config）
- Execution
  - ExecutionEngine（本番 / paper_trading 切替）
  - BrokerClientFactory による Broker クライアント抽象化
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の構成要素
- Monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - 監視ログを永続化する SQLite 層（monitoring_db.py）
  - Kill Switch（data/kill.flag）による Execution 停止
- Research
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン / IC 計算、統計サマリ
- Portfolio
  - 候補選定・重み計算（等ウェイト／スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（risk_based / equal / score）
- AI（OpenAI 連携）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一ログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## 前提・依存ライブラリ

（ソースで使用される主なパッケージ例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML の検証を行う場合、任意）

requirements.txt は本リポジトリに含まれていないため、ローカルで必要なパッケージを pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabu API パスワードなど主要設定を生成します。
4. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告も失敗扱いになります。
5. 初期 DB / ディレクトリ作成
   - アプリ実行時に logs/ や data/ 等を自動で作成しますが、必要なら手動で作ってください。
6. OpenAI 連携を使う場合は環境変数 `OPENAI_API_KEY` を設定

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（代表例）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject （paper_trading 時の約定振る舞い）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（開発向け）

注記:
- Monitoring (run_monitoring) は KABUSYS_ENV に関わらず `sqlite_path`（本番監視 DB）を使用します。
- Execution (run_execution) は `KABUSYS_ENV=paper_trading` の場合にペーパートレード用の `paper_sqlite_path` を使用して本番 DB と切り離します。

---

## 実行方法

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループを起動（デフォルトは 60 秒間隔）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（例: 30）。

- 実行エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  実行中は `data/execution.pid` を作成し、停止フラグ `data/stop_requested.flag` が存在すると安全に停止します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- AI 関連（プログラムから呼び出す）
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  どちらも `OPENAI_API_KEY` 環境変数か引数で API キーを渡してください。

---

## 停止・Kill の仕組み

- 実行停止（run_execution / run_monitoring）:
  - data/stop_requested.flag を作成すると起動中ループは検出して終了します（run_execution は開始前に既に flag があると起動を行いません）。
- Kill Switch:
  - monitoring の判定（ドローダウンやポジション上限等）により `data/kill.flag` が作成されると ExecutionEngine 側で停止判断が行われます。
  - kill.flag は Settings.kill_flag_clear_on_start により起動時に自動クリアする設定が可能（本番では 0 を推奨）。

---

## ログ

- ログはデフォルト `logs/` ディレクトリに日次ローテーションで出力されます（logs/<app_name>.log）。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されています。
- ログレベルは優先順: 関数引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。

---

## DB（簡単な説明）

- DuckDB: 分析用データ（prices_daily, raw_financials, raw_news, etc.）
- SQLite (monitoring.db): system_status, trade_logs, positions, risk_logs, dashboard などの永続化
- ペーパートレード時は ExecutionEngine が paper_trading 用 SQLite を使う（分離）

monitoring_db.init_monitoring_db(conn) は必要なテーブルとマイグレーションを冪等に作成・更新します。

---

## 開発向けメモ / 注意点

- 設定ファイル（.env）は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- OpenAI 呼び出しはリトライやフォールバック処理を備えていますが、API利用にはキーとコスト管理が必要です。
- 実機発注を行う `KABUSYS_ENV=live` の場合は LINE 通知等の設定を必ず確認してください（validate_config に警告があります）。
- process priority / cpu affinity は psutil 経由で OS に依存するため、権限や OS によって設定できない場合があります（ログに警告が出ます）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings
    - config_setup.py                — .env 対話ウィザード
    - validate_config.py             — 起動前検証 CLI
    - run_monitoring.py              — SystemMonitor ポーリングループ起動
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照実装がある想定)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/                      — 監視関連（上記）
    - tools/
      - paper_verification_report.py
    - data/ (実行時に生成される想定)
    - logs/ (ログ出力先)
- config/
  - *.yaml (system_config.yaml, strategy_config.yaml, ...)

---

## 参考コマンド一覧

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（ペーパートレードモード）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README は以上です。具体的な実行時の詳細（Broker 実装、Strategy 実装、config/*.yaml の中身など）はそれぞれのモジュール／設定ファイルを参照してください。必要であれば各サブモジュールの使い方（API シグネチャや設定項目一覧）を追記した README を作成します。どの部分を詳しく出力しますか？