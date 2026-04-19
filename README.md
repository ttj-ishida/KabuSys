# KabuSys

日本株向け自動売買システムのリポジトリ (KabuSys)。  
この README はソースツリー（src/kabusys/*）に基づいた概要、機能、セットアップ／起動方法、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。主な役割は次のとおりです。

- 発注エンジン（ExecutionEngine）：ライブまたはペーパートレードでの発注ロジック、注文管理、リスク管理、照合（reconciliation）。
- 監視（Monitoring）：システム状態、注文の異常、リスク（ドローダウン・ポジション上限等）を定期的にチェックし、必要に応じて Kill Switch（停止フラグ）を投げる。
- ポートフォリオ構築（Portfolio）：候補選定、重み算出、ポジションサイズ計算、セクター制限など純粋関数群。
- リサーチ（Research）：DuckDB の時系列データを用いたファクター計算・将来リターン算出・IC計算など。
- AI 支援（AI）：OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定。
- ツール類：ペーパートレード結果検証レポート生成など。
- 設定ユーティリティ：.env 対話式ウィザードや起動前設定検証 CLI。

設計上の注意点（抜粋）：
- .env 読み込みはプロジェクトルート（.git や pyproject.toml を検出）を起点に行う。
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）。
- AI モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とする。API 呼び出しはリトライやフェイルセーフを備える。
- ロギングは共通ユーティリティで設定（stdout + 日次ローテーションファイル）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を利用し DB を分離
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実プロセス存在を監視
  - TradeMonitor: 注文の滞留、約定異常、レイテンシ監視
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件を満たした場合に data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 上記を束ねてポーリング実行
- Portfolio
  - 候補選定、等重／スコア重み付け、リスクベースの株数計算、セクターキャップ、レジーム乗数
- Research
  - momentum / volatility / value ファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
  - DuckDB を用いた SQL + Python 実装
- AI
  - ニュースのセンチメントスコアリング（ai_scores テーブルへの保存）
  - マクロニュース + MA200 に基づいた市場レジーム判定（market_regime テーブル）
  - OpenAI（gpt-4o-mini）とのバッチ・JSON 連携、リトライ・バリデーション実装
- ツール
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）
- 設定・ユーティリティ
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - 統一ロギング設定・プロセス優先度設定ユーティリティ

---

## 必要条件 / 依存ライブラリ（代表例）

※正確な requirements.txt はリポジトリに含まれていないため、代表的な依存パッケージを記載します。

- Python 3.10 以上（型注釈に PEP 604 の `X | Y` を使用）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml（config 検証で YAML の内容チェックを行う場合に任意）
- sqlite3（標準ライブラリ）
- その他：標準ライブラリ（logging, pathlib, threading, datetime 等）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順 (クイックスタート)

1. リポジトリをクローンしてソース配下に移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```

3. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 必要に応じて:
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH など

4. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認
   - デフォルトでは `data/` に SQLite や PID / フラグファイル、`logs/` にログが作られます。権限や所有権を確認してください。

6. （任意）DuckDB に分析用データを投入
   - research モジュールは DuckDB の `prices_daily`, `raw_financials`, `raw_news` 等のテーブルを前提としているため、事前にデータを準備してください。

---

## 起動 / 使い方

主要なエントリポイント（モジュールとして実行）:

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV によって動作モードが変わります:
    - development: 発注を行わない開発用
    - paper_trading: MockBroker を利用し、デフォルトで data/paper_trading.db に記録
    - live: 実口座へ発注（kabuステーション API）

  - 停止方法:
    - モニタリング側から kill.flag が書き込まれるか（KillSwitch）
    - または `data/stop_requested.flag` を作成すると終了ループが検出して停止します。

- Monitoring を起動（常駐ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用してログを書き込みます
  - 実行時にはプロセス優先度を上げます（ユーティリティで platform を考慮）

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング（プログラムから呼ぶ例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, target_date=date(2026, 4, 1), api_key='YOUR_OPENAI_KEY')
  ```

- 市場レジーム判定（プログラムから呼ぶ例）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026, 4, 1), api_key='YOUR_OPENAI_KEY')
  ```

注意点:
- AI 機能は OPENAI_API_KEY（または api_key 引数）を必要とします。
- Paper trading モードは発注を行わないことを必ず確認してください（設定ミスに注意）。
- Kill Switch（data/kill.flag）の自動クリア挙動は環境変数 KILL_FLAG_CLEAR_ON_START で制御されます（本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

詳しくは `src/kabusys/config.py` の Settings クラスのプロパティを参照してください。

---

## ロギング / ファイル配置

- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
  - コンソールは stdout に出力（cron 等でのリダイレクトを想定）
- DB:
  - DuckDB: data/kabusys.duckdb（分析データ）
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db（paper_trading モード時）
- PID / フラグ:
  - data/execution.pid（実行中 PID）
  - data/kill.flag（Kill Switch 発動時に作成）
  - data/stop_requested.flag（手動停止用フラグ。run_*.py はこのファイルを検出して終了）

---

## ディレクトリ構成（主要ファイル）

以下はソース構成（`src/kabusys`）の抜粋です。実際のリポジトリにはさらに多くのファイルがある可能性があります。

- src/kabusys/
  - __init__.py
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照; 実装あり)
  - execution/                — 発注関連（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など）
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
  - data/                     — （実行時に使用する DB / ファイル群が置かれるデフォルト場所）
  - logs/                     — ログディレクトリ（実行時に作成）

---

## 開発・運用時の注意点

- 本番（KABUSYS_ENV=live）での設定は厳重に管理してください（LINE 通知、Kill Switch 設定等）。
- .env は絶対に Git にコミットしないでください（config_setup も README に警告あり）。
- AI モジュールを運用する際は API コストやレート制限、レスポンスのバリデーションに注意してください。実装にはリトライとスコアクリッピング等の安全策が含まれますが、運用監視は必要です。
- DuckDB / SQLite のスキーマは code 内で初期化・マイグレーション処理が含まれる場合がありますが、分析データの投入・メンテナンスは別途必要です。
- ログディレクトリや data ディレクトリの作成に失敗した場合、ロギングや DB 書き込みに影響が出ます。権限とディスク容量を監視してください。

---

## よく使うコマンド（まとめ）

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に加えたい具体的なサンプル設定ファイル（.env.example）や requirements.txt、デプロイ手順（systemd / supervisor / Dockerfile など）が必要であれば、その内容を提供します。どの情報を優先して追加しますか？