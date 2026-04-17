# KabuSys — README

このリポジトリは日本株向けの自動売買・研究・監視フレームワークです。  
本README はコードベース（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 日次・リアルタイムの売買シグナル生成とポートフォリオ構築（portfolio）
- 発注・注文管理・リコンシリエーション（execution）
- システム稼働・注文状態・リスク監視（monitoring）
- 研究用ファクター計算・特徴量解析（research）
- ニュース NLP によるセンチメント評価・レジーム判定（ai）
- Paper Trading 用ツール・検証レポート（tools）
- プロセス優先度設定などユーティリティ（utils）

設計方針の特徴：
- DuckDB / SQLite を用いたローカル DB 中心の処理（外部サービスへの過度な依存を避ける）
- Paper Trading（テスト環境）は本番 DB と完全分離
- OpenAI（LLM）呼び出し部分はフェイルセーフ / リトライ実装あり
- ルックアヘッドバイアス回避（日付参照の扱いに注意）

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注セッション起動 / 停止
  - BrokerClientFactory による本番 / Paper トレードの切替
  - OrderManager / OrderRepository による注文生成・同期
  - Reconciler による再起動時の自動復旧（OrderSent 照合・ポジション差分検出）

- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・データ鮮度・Execution プロセスの監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、dashboard 更新
  - KillSwitch：閾値到達時に kill.flag を作成して Execution を停止させる
  - AlertManager：LINE Messaging API による通知（オプション）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio / Strategy
  - 銘柄選定、等重・スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ算出（単元株丸め・aggregate cap 調整）

- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュースの銘柄別センチメント評価（OpenAI 使用）
  - マクロニュース + 1321 ETF の MA200 を合成した市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提：
- Python 3.10 以上（| 型や match などの近年の構文サポート、typing の垂直統合のため）
- git リポジトリルートに `pyproject.toml` または `.git` があること（.env 自動読み込みのため）

1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai requests streamlit
   - その他プロジェクトで必要なパッケージがあれば追記してください（requirements.txt がある場合はそれを利用）
4. data ディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 主要な環境変数例（.env に記載する例）：
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL（← 監視ループ上書き可）
6. DB 初期化
   - run_execution / run_monitoring 実行時に monitoring DB のテーブルは自動で作成されます（init_monitoring_db を呼び出します）。

注意：Paper Trading は `KABUSYS_ENV=paper_trading` を設定すると、本番 sqlite と分離された `PAPER_TRADING_SQLITE_PATH` を使用します。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 特記事項：
    - 起動前に `data/stop_requested.flag` があると起動せず終了します。
    - `set_process_priority("high")` によりプロセス優先度を上げようとします（権限が無い場合は警告を出してスキップ）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` に記録します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（Settings.sqlite_path）を用いて永続化します（環境に関係なく本番 sqlite を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 標準出力に検証サマリ（稼働率、注文成功率、レイテンシ等）

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite DB を読み取り専用で開いて可視化します。

- AI モジュール（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出し時に OPENAI_API_KEY を渡すか環境変数で設定してください。

- .env 自動読み込みの挙動
  - プロジェクトルート（.git または pyproject.toml が見つかった場所）を基準に `.env`（既存の OS 環境変数を上書きしない）→ `.env.local`（上書き可）を順次読み込みます。
  - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（要点）

- KABUSYS_ENV: development | paper_trading | live（デプロイ環境）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 sqlite（paper_trading 環境時使用）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）

---

## 停止・強制停止の仕組み

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はループ内でこのファイルの存在を監視し、検出すると安全に停止します（外部管理用の停止フラグ）。

- KillSwitch（monitoring.kill_switch）
  - RiskMonitor 等の結果に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側は `Settings.kill_flag_path` を参照して起動時にクリアやチェックを行う設計です（設定で挙動を調整可能）。

---

## ディレクトリ構成（抜粋 & 説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, ...（発注ロジック、ブローカー抽象）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - kill_switch.py, alert_manager.py — フラグ・通知関連
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定・ウェイト・サイズ計算
  - research/
    - factor_research.py, feature_exploration.py — ファクター / 研究用ユーティリティ
  - ai/
    - news_nlp.py, regime_detector.py — ニュース NLP（OpenAI） / レジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/  （実行時に生成・使用）
    - monitoring.db（default: SQLITE_PATH）
    - kabusys.duckdb（default: DUCKDB_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - execution.pid, kill.flag, stop_requested.flag, ...（制御ファイル）

---

## 開発・運用上の注意

- Paper Trading と Live は DB を分離して扱うこと（PAPER_TRADING_SQLITE_PATH を設定）。
- OpenAI 呼び出しを行う AI モジュールは料金・レート制限に注意（リトライ処理は実装済み）。
- process priority / cpu affinity の設定は OS に依存し、権限不足では警告を出してスキップします。
- .env には機密情報（API キー等）を平文で置くためアクセス制御に注意してください。
- DuckDB / SQLite のバージョン差異により executemany 等の挙動が異なるため、空配列バインド等はコード側で回避しています。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化（例）
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb psutil openai requests streamlit

- 実行
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、README にサンプル .env.example やデプロイ手順（systemd / supervisor 用のサービス定義例）、より詳しい各モジュールの説明（API、関数シグネチャ、戻り値フォーマット）を追記できます。どの部分を拡張したいか教えてください。