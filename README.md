# KabuSys — README (日本語)

このドキュメントはリポジトリ内のコードベースに対する簡易 README です。プロジェクトの概要・機能・セットアップ方法・使い方・ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤です。本システムは以下の主要機能を含み、発注ロジック・監視・検証・AI によるニュース解析・市場レジーム判定などを提供します。

主な設計方針：
- DuckDB / SQLite を用いたローカルデータ処理（prices_daily / raw_financials / raw_news 等）
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を分離
- Paper trading（モックブローカー）と本番を環境変数で切替可能
- 外部 API（kabuステーション, J-Quants, OpenAI 等）は設定で接続

バージョン情報:
- パッケージバージョン: `kabusys.__version__ = "0.1.0"`

---

## 主な機能一覧

- Execution (発注)
  - OrderManager / ExecutionEngine / Reconciler：発注・状態管理・再同期
  - Broker クライアントの抽象化（本番 / モック対応）
  - RiskManager によるポジション上限・ドローダウン等の制御

- Monitoring（監視・アラート）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：条件に応じて flag ファイルを書き ExecutionEngine を停止させる
  - AlertManager：LINE Messaging API による通知（クールダウン制御）
  - Streamlit ダッシュボード（監視表示）

- Portfolio construction（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等分配 / スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・aggregate cap）

- Research / Factor 計算
  - momentum / volatility / value などのファクター計算（DuckDB 上で実行）
  - 将来リターン・IC 計算・統計サマリー

- AI 関連
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores への書き込み）
  - regime_detector: マクロニュース + ETF MA を組合せた市場レジーム判定

- ユーティリティ
  - 環境変数設定ローダ（.env 自動読み込み、優先順）
  - process priority / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル）

以下は最小のセットアップ手順（想定: Python 3.10+）。

1. リポジトリをクローン / 取得

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージ（例）
   - 本プロジェクトで使用されている主要ライブラリ：
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード用)
   - インストール例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - （プロジェクトに requirements.txt があればそちらを利用してください。）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 代表的な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants トークン（必須）
     - KABU_API_PASSWORD: kabuステーション用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - PID_FILE_PATH / KILL_FLAG_PATH: pid/kill flag ファイルパス（デフォルトを使用可）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, デフォルト 60）

5. DB 初期化
   - Monitoring 周り（init_monitoring_db）は run スクリプトから自動で作成されます。必要に応じて手動で SQLite ファイルを作っておくことも可能です。

---

## 使い方（主要コマンド）

以下はモジュールとしての起動方法（パッケージが Python path にあることが前提）。

- 監視ループの起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 説明:
    - プロセス優先度を "high" に設定（可能なら）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）
    - 監視用 SQLite は Settings.sqlite_path（環境にかかわらず本番 sqlite_path を使う）

- Execution（発注エンジン）の起動
  ```
  python -m kabusys.run_execution
  ```
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に分離して記録
    - プロセス優先度を "high" に設定（可能なら）

- Paper Trading 検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション:
    - --from / --to: YYYY-MM-DD 形式で期間指定
    - --db: SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 説明:
    - 読み取り専用で SQLite に接続（URI に ?mode=ro を付与）
    - MonitoringEngine を起動していないと DB が存在しない旨が表示されます

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - OPENAI_API_KEY が必要（api_key 引数で上書き可）
    - API 呼び出し時の一時エラーや JSON パース失敗はフェイルセーフで処理し、概ね安全に継続します

---

## 重要な挙動・運用メモ

- 環境分離
  - Monitoring は常に Settings.sqlite_path（本番 DB を想定）を使用します。Execution は KABUSYS_ENV=paper_trading の場合、専用の paper_sqlite_path を使用して本番 DB と完全に分離します。
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - 0 以下の値は無効扱いされ、デフォルトにフォールバックします。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます（Windows / POSIX の差分を吸収）。権限がない場合は警告を出してスキップします。
- kill.flag
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由文字列を書き、ExecutionEngine に停止シグナルを送ります。既存の flag は上書きしません（冪等）。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に flag を自動でクリアする挙動を設定できます（Settings.kill_flag_clear_on_start）。
- .env 自動ロード
  - 自動ロード優先順: OS 環境変数 > .env.local > .env
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。見つからない場合は自動ロードをスキップします。
- Paper trading の約定挙動
  - PAPER_FILL_MODE によりモック約定の挙動を制御（instant / partial / never / reject）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込み、.env 自動ロード、各種パス/閾値を提供
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の分離等）
  - tools/
    - paper_verification_report.py
      - Paper Trading 検証レポート生成（コマンドライン）
  - monitoring/
    - monitoring_db.py
      - SQLite のスキーマ初期化 / MonitoringDB クラス（ログ永続化）
    - system_monitor.py
      - CPU/Memory/Disk/プロセス/データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常チェック
    - risk_monitor.py
      - ドローダウン / ポジション上限チェック
    - kill_switch.py
      - フラグファイルによる停止シグナル管理
    - alert_manager.py
      - LINE Push 通知
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py
      - Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (存在参照されます)
    - risk_manager.py (存在参照されます)
    - broker_factory.py (BrokerClientFactory)
    - ...（発注関連の主要ロジック）
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
  - data/ (実行時に生成される想定)
    - kabusys.duckdb (DuckDB、デフォルト) 
    - monitoring.db (SQLite、デフォルト)
    - paper_trading.db (Paper Trading 用 SQLite、デフォルト)

---

## 開発者向け補足

- DuckDB 接続はメモリでの高速集計を想定しています。ファクター計算等は DuckDB の SQL + Python を併用して実装されています。
- AI モジュールは OpenAI の Chat Completions API（gpt-4o-mini 等）を使用。API の失敗にはリトライやフォールバックロジックを備えていますが、利用には API キーが必要です。
- ロギングは基本 INFO レベルで初期化されています。詳細デバッグが必要な場合は LOG_LEVEL 環境変数で設定可能（Settings.log_level）。
- Windows / POSIX の差分吸収が入っている箇所があるため、プラットフォーム差に注意。

---

## よくある質問（FAQ）

Q: 監視はどの DB を使いますか？
A: Monitoring（run_monitoring）は常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。Execution は paper_trading 時に paper_sqlite_path を使用して分離します。

Q: MONITOR_POLL_INTERVAL を 0 にするとどうなりますか？
A: 0 以下の値は無効と判断され、デフォルトの 60 秒にフォールバックします（意図せぬ ValueError を防ぎます）。

Q: .env の読み込み順は？
A: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml で判定します。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

以上です。追加で README に含めたいサンプル .env ファイルや、各コマンドのデモ出力（例）を作成する等の要望があればお知らせください。