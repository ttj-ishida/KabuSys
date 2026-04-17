# KabuSys

日本株向け自動売買システム（ライブラリ/ツール群）  
このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・AI を用いたニュース評価・研究用ユーティリティなどを含むモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群です。主な役割は以下です。

- 市場データ（DuckDB）の利用によるファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- ExecutionEngine による注文実行（本番 / ペーパートレード切替）
- 監視コンポーネント（システム状態・注文滞留・リスク監視）と Kill Switch
- OpenAI を用いたニュースセンチメント評価・レジーム判定
- 各種ユーティリティ・検証ツール

設計上、データベース（SQLite / DuckDB）を利用した状態永続化、環境変数を用いた挙動切替、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・リスク管理・リコンサイル）
  - Broker クライアントの切替（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - ペーパートレードは本番 DB と分離（data/paper_trading.db を使用、設定で上書き可）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック）
  - TradeMonitor（滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション数上限監視）
  - KillSwitch（閾値超過時に data/kill.flag を作成して ExecutionEngine を停止）
  - AlertManager（LINE Push 経由での通知、クールダウン管理）
- Portfolio
  - 候補選定（スコア順）、等重/スコア重み付け、ポジションサイズ決定（単元丸め／リスクベース等）
  - セクター上限適用、レジーム乗数
- Research / Data
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC 計測、ファクター統計サマリ
- AI
  - ニュースの LLM（OpenAI）によるセンチメントスコア付与（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（market_regime テーブルへ書き込み）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定で稼働率／成功率／レイテンシ等を出力）
- 設定支援
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール

   最低限必要なパッケージ（プロジェクト内で参照あり）:

   - duckdb
   - psutil
   - openai
   - requests
   - PyYAML（config 検証のため任意）

   例:

   ```
   pip install duckdb psutil openai requests PyYAML
   ```

   ※ 実運用では requirements.txt を用意して管理してください。

4. データディレクトリ作成

   ```
   mkdir -p data
   ```

   デフォルトの DB パス:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - SQLite (paper_trading): data/paper_trading.db

5. 環境変数設定（.env ファイルを作成するのが簡単）

   対話式ウィザードを実行して `.env` を生成できます:

   ```
   python -m kabusys.config_setup
   ```

   必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD  
   OpenAI を使う機能を使う場合は OPENAI_API_KEY を設定してください。

   例（.env の一部）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   ```

6. 設定検証（任意）

   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

ここでは主要な実行例を示します。

- ExecutionEngine（エンジン）を起動

  - 本番・開発・ペーパートレードの挙動は環境変数 KABUSYS_ENV で制御します（development / paper_trading / live）。

  ```
  # 例: ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  ペーパートレード時は MockBrokerClient を用い、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。エンジン起動時には data/execution.pid を生成し、停止は data/stop_requested.flag や data/kill.flag で制御されます。

- 監視ループを起動

  ```
  python -m kabusys.run_monitoring
  ```

  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書きできます。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログの永続化先は設定で決定）。

- Paper Trading 検証レポートの生成

  ```
  # デフォルト DB を読む
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- 設定ウィザード（.env 作成）

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- AI 関連（プログラムから呼び出し）

  OpenAI を利用する関数（例）:

  - ニュースセンチメント付与:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  どちらも api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定してください。DuckDB 接続オブジェクト（duckdb.connect(...) の返り値）を引数に与えて使用します。

注意事項:
- KABUSYS_ENV=paper_trading の場合は本番 DB と分離されます（ペーパートレード DB を使用）。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil による処理）。権限がない場合は警告を出してスキップします。
- Kill Switch / 停止フラグファイル: data/kill.flag（KillSwitch）、data/stop_requested.flag（run_*.py の停止トリガ）などを利用します。

---

## 主要な環境変数

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

よく使うオプション
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必要）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（詳細は kabusys.config.Settings を参照）

設定ミス検出用スクリプト: python -m kabusys.validate_config

---

## ディレクトリ構成

以下は主要なファイル / モジュール一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動読み込み・Settings
    - config_setup.py          — 対話式 .env 作成ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - execution/               — Execution エンジン関連（order_manager など）
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
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
    - utils/
      - process_priority.py

上記のサブパッケージ群が各機能を分離して実装しています（ビジネスロジック / IO を適切に分離する設計が意図されています）。

---

## 運用メモ / FAQ

- データベースのマイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対するカラム追加マイグレーション（例: peak_value, latency_ms）も実施します。

- Kill Switch の動作
  - RiskMonitor 等の結果に基づき KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動でクリアされます（本番では 0 推奨）。

- OpenAI の呼び出し
  - レート制限・一時的な接続障害・5xx 等に対しては指数バックオフでリトライする実装が入っています。API キーは環境変数か関数引数で渡します。

---

## 貢献 / 開発

- コードはモジュール単位でテストしやすいように設計されています（多くの関数が純粋関数または副作用を限定）。ユニットテストやモックを用いたテストを推奨します。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

---

必要であれば、README にサンプル .env のテンプレートや systemd / supervisord 用のサービス定義例、SQL スキーマの詳細、よくあるトラブルシュート（OpenAI の認証エラー、psutil の権限問題、ファイルパスの権限）などを追加できます。どの情報が要るか教えてください。