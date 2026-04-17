# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（研究 → シグナル → 実行 → 監視）を構成する Python モジュール群です。  
以下はコードベースに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- DuckDB / SQLite を用いたデータ保管・分析（価格データ、財務データ、ニュースなど）
- ファクター計算・特徴量生成（research）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ExecutionEngine を用いた発注ロジック（paper_trading と live の分離）
- 監視コンポーネント（プロセス・データ鮮度・約定監視・リスク監視）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- 運用支援ツール（.env ウィザード／設定検証／Paper Trading レポート生成）

設計上の特徴：
- 実行モード（development / paper_trading / live）に応じた振る舞い
- Paper Trading は実運用 DB と分離（data/paper_trading.db）
- 監視（monitoring）は環境にかかわらず本番の monitoring DB を参照
- LLM（OpenAI）呼び出しは失敗時にフェイルセーフで継続する（部分失敗を許容）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い paper_trading DB に記録
- 監視起動スクリプト（python -m kabusys.run_monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- AI モジュール
  - news_nlp: ニュースを LLM でセンチメント評価、ai_scores に書込
  - regime_detector: MA200 とマクロニュースから市場レジーム判定
- 研究モジュール（ファクター・ボラティリティ・将来リターン・IC 計算など）
- ポートフォリオ構築（候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限）
- ツール: Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（依存パッケージの例）

主要依存（プロジェクト内で使用されているもの）：
- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config 検証で任意）

実際は pyproject.toml / requirements.txt があればそれに従ってください。インストール例：
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. レポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb psutil openai pyyaml

3. data ディレクトリを作成（DB や PID/flag 用）
   - mkdir -p data

4. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、実行環境などを設定して .env を生成します。
   - 生成後、設定の検証を行う:
     - python -m kabusys.validate_config
     - 問題があれば .env を修正して再検証

5.（オプション）Paper Trading DB の初期準備
   - デフォルト: data/paper_trading.db
   - Paper Trading を使う場合は .env で PAPER_TRADING_SQLITE_PATH を設定できます。

---

## 主要な環境変数（要設定項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

任意/推奨（代表的なもの）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）※ monitoring は常にここを参照
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

簡易 .env の例（ウィザードで生成されます）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## 使い方（起動・停止・運用）

基本的にモジュールは Python の -m で実行します。

1. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

2. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録
     - PID ファイル: data/execution.pid（Settings.pid_file_path）
     - 起動前に data/stop_requested.flag があると起動をしません

3. 監視（Monitoring）起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
   - 監視は Settings.sqlite_path（monitoring.db）を常に使用します（環境に依存しない）

4. 停止方法
   - 実行中の run_execution / run_monitoring は Ctrl+C で停止可能
   - 監視や実行を外部から停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成します：
     - touch data/stop_requested.flag
     - run_execution / run_monitoring はループ内でこのファイルを検出して安全に停止します
   - KillSwitch: リスク条件（ドローダウンやポジション上限）により data/kill.flag を書くと ExecutionEngine に停止シグナルを送れます
     - kill.flag の場所は Settings.kill_flag_path（デフォルト data/kill.flag）

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
   - 簡易な稼働率・注文成功率・レイテンシ等のレポートを標準出力に表示します

---

## モードの違い（KABUSYS_ENV）

- development
  - ローカル開発・テスト向け。実際の発注は行わない想定（BrokerFactory 等の挙動に依る）
- paper_trading
  - MockBrokerClient を利用し、data/paper_trading.db に注文ログ等を記録（本番 DB と完全分離）
  - PAPER_FILL_MODE で約定挙動を調整可能（instant / partial / never / reject）
- live
  - 実際の発注を行う本番モード。設定ミスに十分注意（validate_config が警告出力します）

---

## 注意点 / 運用メモ

- 監視（monitoring）は常に Settings.sqlite_path（monitoring.db）を参照します。Paper Trading でも監視 DB は同じ場所です。
- run_execution は Paper Trading 時に別 DB（PAPER_TRADING_SQLITE_PATH）を使用します（設定により上書き可能）。
- OpenAI を使用する機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しは失敗時にフェイルセーフ動作（スコア 0.0 等）となりますが、API キーの設定を推奨します。
- process_priority（psutil）を使ってプロセス優先度を "high" に上げる処理があります。実行環境の権限により設定が失敗する場合があります（警告ログが出力されます）。
- monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で上書きできます。0 以下や不正値は無視されデフォルト 60 秒にフォールバックします。
- ファイルベースのシグナル（data/stop_requested.flag, data/kill.flag）は運用上の簡易 Kill Switch として使用されます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env の読み込みと Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite 監視テーブル定義・永続化 API
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - monitoring_engine.py   — 各モニタの束ね（Polling）
  - kill_switch.py         — kill.flag 書き込みユーティリティ
  - alert_manager.py       — （未掲示のファイルが存在）
- execution/               — Execution 関連（Engine, BrokerFactory, OrderManager 等）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定ロジック
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py — 将来リターン計算・IC・統計
- tools/
  - paper_verification_report.py — Paper Trading レポート生成スクリプト
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

プロジェクトルート:
- config/*.yaml            — 各種テンプレート（system_config.yaml など、運用用）
- data/                    — デフォルトの DB / PID / flag を格納する場所（例: data/monitoring.db）

---

## よく使うコマンド例

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

- 停止（外部から）
  - touch data/stop_requested.flag

---

## 開発・拡張メモ

- DuckDB 接続は research / ai モジュールで使用され、prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- Execution 系の実装（BrokerClientFactory、ExecutionEngine、OrderRepository など）は実際のブローカー接続を抽象化しているため、テストやシミュレーション用に Mock を差し込める設計です。
- LLM 関連の API 呼び出しは各モジュール内でラップされているため、テスト時は該当関数をモックすることで実動作をエミュレートできます（コード内にモック用の patch コメントあり）。

---

必要であれば README にさらに「API リファレンス」「運用チェックリスト」「設定ファイルのテンプレート（config/*.yaml）」などを追記できます。どの情報を優先して追加しますか？