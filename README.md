# KabuSys

日本株向け自動売買システムの一部を実装した Python パッケージ（実験/運用向けのコンポーネント群）。
このリポジトリには、注文実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、AI（ニュース NLP / レジーム判定）、および運用用ツールが含まれます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- 市場データ（DuckDB）を参照してファクターやリサーチ指標を計算する研究モジュール
- 注文発行・リスク管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状況・注文ログ・リスクを永続化する監視モジュール
- ニュースを LLM（OpenAI）で評価して銘柄別センチメントを算出する AI モジュール
- 運用支援スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一例:
- 本番とペーパートレードは DB を分離（KABUSYS_ENV による切替）
- LLM 呼び出しは冪等性・リトライ・バリデーションを重視
- ロギング/プロセス優先度/停止フラグなど運用面の考慮あり

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト: python -m kabusys.run_execution
  - ペーパートレードモード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し専用 SQLite に記録
  - Kill Switch による安全停止（data/kill.flag）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor 統合のポーリング：python -m kabusys.run_monitoring
  - 監視ログの永続化 (SQLite)
  - アラート送信のフック（LINE など）
- Portfolio
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限適用など
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続）
  - 将来リターン・IC 計算などの統計ツール
- AI
  - ニュース NLP による銘柄別センチメントスコア算出（OpenAI）
  - マクロ + ETF MA200 乖離を用いた市場レジーム判定（OpenAI 補助）
- Tools
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## 必要環境（例）

- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML（config/*.yaml のパース検証に使用）
- SQLite（Python 標準ライブラリで利用）
- ネットワーク（本番で kabuステーション / OpenAI を使う場合）

pip によるインストール例（プロジェクト配布方法により調整）:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .      # setup.py / pyproject がある前提
pip install duckdb psutil openai
# optional: pip install PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意
2. 依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, PAPER_TRADING_SQLITE_PATH など
4. 設定を検証:
   ```
   python -m kabusys.validate_config
   # 必要に応じて strict モード:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリを作成（.env のパス先により異なるがデフォルトは data/）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・コマンド）

### 実行エンジン（ExecutionEngine）
- 起動:
  ```
  python -m kabusys.run_execution
  ```
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
  - 起動前に data/stop_requested.flag がある場合は起動をスキップします。
  - 停止したい場合は data/stop_requested.flag を作成するか、実行中に kill.flag を作成すると ExecutionEngine に停止要求が送られます。

### 監視プロセス（Monitoring）
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- 環境変数:
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）でポーリング間隔を上書き可能
- 特記事項:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログの一元管理のため）。
  - 監視ループは data/stop_requested.flag の存在で終了します。

### ペーパートレード検証レポート
- 使用例:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- オプション:
  - --db で SQLite DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

### 設定ウィザード / 検証
- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

### AI / Research API（プログラム内で利用）
- ニュース NLP スコア算出:
  ```python
  from kabusys.ai.news_nlp import score_news
  # conn: duckdb connection, target_date: datetime.date, api_key optional
  score_news(conn, target_date, api_key="...")
  ```
- レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")
  ```
- Research 関数例:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  res = calc_momentum(duckdb_conn, date(2026,4,1))
  ```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック・DB 分離
  - live: 本番
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（INFO 等）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔・秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: 0/1）

---

## 停止 / Kill Switch / フラグファイル

- data/stop_requested.flag
  - run_execution / run_monitoring のループを終了させるために存在をチェックするファイル。手動で作成すると次回ループで検出して終了します。
- data/kill.flag
  - KillSwitch が発動するとこのファイルを書き込み、ExecutionEngine に停止を促す仕組み。運用時は注意して扱ってください。
- PID ファイル
  - data/execution.pid 等を使用してプロセスの管理を行います。

---

## ログ

- デフォルト出力:
  - コンソール (stdout)
  - 日次ローテーションでファイル出力: logs/<app_name>.log（30日分保持）
- 環境変数 LOG_DIR で変更可能

ログ初期化ヘルパー:
- from kabusys.utils.logging_setup import setup_logging
- setup_logging(app_name="execution")

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を基準）

- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

サブパッケージ:
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py, ...
- monitoring/
  - monitoring_db.py, system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py, ...
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py
- research/
  - factor_research.py, feature_exploration.py, __init__.py
- ai/
  - news_nlp.py, regime_detector.py, __init__.py
- tools/
  - paper_verification_report.py, __init__.py
- utils/
  - logging_setup.py, process_priority.py, __init__.py
- data/                   — デフォルトの DB / フラグファイル置き場（運用環境で作成）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）での設定ミスは致命的な自動発注を引き起こす可能性があるため、validate_config の実行や LINE 等の通知設定を必ず確認してください。
- Kill Switch 等の自動停止ロジックは運用上重要ですが、KILL_FLAG_CLEAR_ON_START の値が 1 の設定は本番では推奨されません（誤って削除されると保護が失効するため）。
- OpenAI API を利用する機能は API 利用料が発生します。API キーの管理と呼び出し頻度には注意してください。
- DuckDB / SQLite のパスは .env で指定できます。バックアップ・監視を行ってください。
- ログディレクトリ作成失敗時はファイル出力が無効化されコンソールのみの出力になります。運用時は logs/ の権限を確認してください。

---

README はこのコードベースの概要と運用に必要な基本操作をまとめたものです。実際の利用時は各モジュール内の docstring とコメントを参照し、環境ごとの設定を慎重に行ってください。必要であれば README に導入手順（パッケージ化 / systemd / supervisor 用のサンプルサービス定義）を追加できます。