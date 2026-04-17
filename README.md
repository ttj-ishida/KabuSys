# KabuSys

日本株向け自動売買システムのコアモジュール群のリポジトリ（抜粋）。  
この README は提供されたコードベースに基づき、プロジェクトの概要・機能・セットアップ・起動方法・ディレクトリ構成を日本語でまとめたものです。

## プロジェクト概要
KabuSys は日本株の自動売買・研究・監視に必要な機能をモジュール化したライブラリ／ランタイム群です。主な役割は次のとおりです。

- Execution: 注文作成・送信・状態管理・再同期（Reconciler）を行う ExecutionEngine。
- Monitoring: システム状態（CPU／メモリ／ディスク）、データ鮮度、注文滞留・約定異常、ドローダウン等を監視しログ・アラート・停止フラグを管理する機能群。
- Portfolio: 候補選定、重み付け、ポジションサイズ算出、セクター制限・レジーム調整などのポートフォリオ構築ロジック（純粋関数）。
- Research: DuckDB を用いたファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ。
- AI: OpenAI（gpt-4o-mini など）を用いたニュースセンチメント、マクロセンチメントによるレジーム判定。
- Tools: Paper Trading の検証レポート生成や Streamlit ベースの監視ダッシュボードなどの補助ツール。
- Utils: プロセス優先度・CPU affinity 設定などのユーティリティ。

設計上、DB（SQLite / DuckDB）と外部 API（kabuステーション、J-Quants、OpenAI など）を分離し、paper_trading 環境では本番 DB と分離する仕組みがあります。

---

## 機能一覧（抜粋）
- 実行側
  - ExecutionEngine 起動（run_execution.py）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository）
  - 再同期・リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）

- 監視側
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor を束ねてポーリング、KillSwitch 判定、Alert 管理
  - AlertManager: LINE によるアラート送信（クールダウン管理）
  - streamlit_dashboard: 監視データ閲覧用ダッシュボード

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等重・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクターキャップ、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC、統計サマリー（calc_forward_returns, calc_ic, factor_summary）

- AI（LLM 統合）
  - ニュース NLP による銘柄別スコアリング（score_news）
  - マクロ / ETF（1321）を用いた市場レジーム判定（score_regime）

- ツール
  - paper_verification_report: Paper Trading 検証レポート生成
  - モニタリング DB 初期化（init_monitoring_db）

---

## 必要条件 / 依存関係
- Python 3.10 以上（typing の | 演算子等を使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準付属）
- （任意）LINE Messaging API トークン、OpenAI API キー、kabu ステーション用パスワードなどの外部サービスの認証情報

インストール例（仮の requirements.txt がある場合）:
```
pip install -r requirements.txt
```
個別インストール例:
```
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）
多くは .env/.env.local から読み込まれます（Settings クラス参照）。代表的なキーとデフォルト／説明:

- 認証関連
  - JQUANTS_REFRESH_TOKEN （必須）: J-Quants API トークン
  - KABU_API_PASSWORD （必須）: kabuステーション API パスワード
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
  - LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（AlertManager）
  - LINE_USER_ID: LINE 送信先ユーザー ID

- システム / 環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker を用い paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使う
  - LOG_LEVEL: ログレベル（DEBUG|INFO|...）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch が書き込むフラグ（default: data/kill.flag）

- モニタリング閾値 / 挙動
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化
  - KILL_FLAG_CLEAR_ON_START=1: 起動時に kill.flag を自動でクリア（Settings.kill_flag_clear_on_start）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（Mock の約定動作）

---

## セットアップ手順（簡易）
1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. .env を作成（.env.example を参考に必要なキーを設定）
   - 少なくとも JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定
   - OpenAI 機能を使う場合は OPENAI_API_KEY を設定
   - LINE 通知を使用する場合は LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定
5. data ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意: Settings モジュールはプロジェクトルートに .git または pyproject.toml を探して .env を自動読み込みします。テスト等で自動ロードを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）
- ExecutionEngine を起動（本番/ペーパー両対応）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBroker が使用され、paper 用 DB（data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/stop_requested.flag により安全に停止できます（外部でファイルを置く）。

- Monitoring（SystemMonitor の単純なポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可（デフォルト 60）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- Streamlit ダッシュボード（監視データ閲覧）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 指定した SQLite DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

- AI 機能（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は例外になる箇所があります。

---

## 停止 / リスタート制御
- stop_requested.flag（data/stop_requested.flag）
  - run_execution.py / run_monitoring.py はこのファイルの存在を監視しています。ファイルが存在すると起動を抑止したり、実行中のループを終了します。

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が重大な条件（ドローダウン超過等）を検出するとここに理由を書き込みます。ExecutionEngine 側でこのファイルを検知して安全停止などに利用します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動でクリアできます（運用上の注意点あり）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なファイルと役割です。実ファイル群はさらに細分化されています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py       — モメンタム/ボラ/バリューファクター
    - feature_exploration.py   — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 連携）
    - regime_detector.py       — 市場レジーム判定（ETF + マクロ）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / ラッパー
    - system_monitor.py        — システム監視
    - trade_monitor.py         — 注文監視
    - risk_monitor.py          — ドローダウン等の監視
    - monitoring_engine.py     — 各 Monitor を束ねる
    - kill_switch.py           — kill.flag の管理
    - alert_manager.py         — LINE プッシュ通知
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 注文ステートマシン外向き API
    - reconciler.py           — 起動時のリコンシリエーション
    - ...（Broker / OrderRepository 等の実装）
  - monitoring/
    - run_monitoring.py       — 監視開始スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity

---

## 実運用上の注意点
- paper_trading 環境は本番 DB と明確に分離されます。KABUSYS_ENV を paper_trading に設定して確認してください。
- OpenAI API を使う機能はネットワーク・課金を伴います。API キーの管理に注意してください。
- LINE 通知はトークン／ユーザー ID が正しく設定されている場合のみ送信されます。トークン未設定時はログ出力にフォールバックします。
- Monitoring DB（SQLite）は単一ファイルです。アクセス頻度やバックアップ・排他に注意してください（Streamlit は read-only モードで開くことを推奨）。
- process priority / CPU affinity は psutil を利用しています。権限不足で設定に失敗することがあります（その場合はログ警告が出ます）。

---

## 開発・拡張のヒント
- DuckDB 接続を渡す設計のため、データ処理／リサーチ機能はローカルで簡単にテストできます。
- AI 関連の API 呼び出し部分はモックしやすくテスト可能（コード内で _call_openai_api をパッチする設計が取られています）。
- monitoring_db.init_monitoring_db() は idempotent（冪等）で初期化・マイグレーション処理を行います。ローカルテスト時に DB 作成が自動で行われます。

---

必要であれば、README に実際の .env.example のテンプレートや、より詳細な起動・運用手順（systemd のユニットファイル例や docker-compose 例など）を追加で作成します。どの情報を追加したいか教えてください。