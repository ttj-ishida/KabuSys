# KabuSys

日本株向け自動売買システムの一部を構成する Python モジュール群です。  
本リポジトリには発注実行エンジン、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI を利用したニュースセンチメント評価などの実装が含まれます。

---

## プロジェクト概要

KabuSys は以下の役割を持つコンポーネント群で構成されています。

- ExecutionEngine：発注の管理・ブローカー API とやり取りする実行エンジン
- Monitoring：システム稼働状況、注文滞留、ドローダウン等の監視とアラート送信（LINE）
- Portfolio：候補選定、配分・ポジションサイズ計算、セクター制約などのロジック
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI：ニュースを OpenAI（gpt-4o-mini 等）でスコアリングして ai_scores に格納
- Tools：Paper Trading 検証レポート生成スクリプト等

設計方針の一部：
- DuckDB / SQLite をローカル DB として利用し、外部発注 API とは分離
- AI 呼び出しは失敗に寛容（フェイルセーフ）、リトライ実装あり
- 実行／監視プロセスはフラグファイルによる停止制御を採用

---

## 主な機能一覧

- system_monitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス存在チェックを定期記録
- trade_monitor: 滞留注文、約定価格異常の検出とログ
- risk_monitor: ドローダウン監視（ハイウォーターマーク管理）とポジション上限監視
- kill_switch: ドローダウンやポジション上限に達した場合の kill.flag 出力（ExecutionEngine 停止トリガー）
- alert_manager: LINE Messaging API へのプッシュ通知（クールダウン管理）
- monitoring_engine: 各 Monitor を束ねたポーリングループ（テスト用の run_once/本番 run）
- Execution 起動スクリプト: 環境に応じて MockBroker を使う（paper_trading）など
- AI モジュール: ニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- research: モメンタム、ボラティリティ、バリューファクター、IC 計算、特徴量サマリ
- portfolio: 候補選定、等配分/スコア加重、リスク調整、位置サイズ計算
- tools: Paper Trading 検証レポート作成スクリプト

---

## 要求環境

- Python 3.10+
  - 型アノテーションで `|` を使用しているため Python 3.10 以上を推奨（3.11 推奨）
- 推奨パッケージ（一例、実際の requirements.txt がある場合はそちらを使用してください）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - その他、プロジェクトの別モジュールに応じた依存

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成して有効化する
2. 必要なパッケージをインストールする（上記参照）
3. プロジェクトルートに `.env`（または `.env.local`）を配置して環境変数を設定する
   - 自動的に `.env` / `.env.local` をロードする仕組みがあります（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
4. データディレクトリ（デフォルト `data/`）を作成する
5. 初回起動時は必要に応じて DB（DuckDB / SQLite）にテーブルが作成されます（init_monitoring_db にて冪等作成）

---

## 主な環境変数

（重要なものを抜粋）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）
  - paper_trading の場合、Execution 起動は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（AlertManager）
- LINE_USER_ID: LINE 送信先ユーザー ID（AlertManager）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止用ファイルパス）

注意事項:
- Monitoring は KABUSYS_ENV に関わらず監視用の本番 sqlite_path（Settings.sqlite_path）を使用します（run_monitoring の実装による）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB を使用して本番 DB と完全分離します。

---

## データベースとフラグファイル

デフォルトパス（環境変数で上書き可）:
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル（Execution）: data/execution.pid
- 停止フラグ（プロセス停止要求）: data/stop_requested.flag
- kill.flag（KillSwitch によるエンジン停止要求）: data/kill.flag

フラグの使い方:
- run_execution / run_monitoring は `data/stop_requested.flag` の存在を見てプロセスを優雅に終了します。
- KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（Execution 起動時にこのフラグをクリアする設定もあります）。

---

## 使い方（実行方法）

開発時はプロジェクトルートにて以下コマンドを利用してください（`src` を PYTHONPATH に入れるか、`python -m` 実行を使用）。

例: PYTHONPATH を通して直接実行
```bash
# 開発ソースを使って実行する場合（プロジェクトルートで）
PYTHONPATH=src python -m kabusys.run_monitoring
PYTHONPATH=src python -m kabusys.run_execution
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

モジュール単独実行:
- 監視ループ（run_monitoring）
  - 環境変数: MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定（デフォルト60秒）
  - 監視は本番用 sqlite_path を使う点に注意
- 実行エンジン（run_execution）
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に記録し MockBrokerClient を使用
  - 実行中は data/execution.pid に PID を書き込み、停止要求は data/stop_requested.flag で受け付け
- Streamlit ダッシュボード
  - 起動例:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
- Paper Trading 検証レポート
  - 起動例:
    ```bash
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB パスは `data/paper_trading.db`。`--db` で上書き可。

AI 関連:
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行。OPENAI_API_KEY を環境変数に設定するか api_key 引数で渡す。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム判定を market_regime テーブルへ書き込む。

停止方法:
- 実行中の run_execution / run_monitoring を止めるには `data/stop_requested.flag` を作成するか、CTRL+C（KeyboardInterrupt）で終了できます。
- KillSwitch が条件を満たすと `data/kill.flag` を書き込み、次回 ExecutionEngine 起動時や監視ロジックで検知されます。

ログとプロセス優先度:
- 起動時にプロセス優先度を "high" に設定しようとします（権限不足の場合は警告ログが出ます）。

---

## 開発メモ / 注意点

- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基に自動的に `.env` / `.env.local` をロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MonitoringDB（SQLite）初回接続時にテーブルやインデックスを冪等的に作成します。また既存 DB に対して必要なマイグレーション（列追加）を行います。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンス検証を備えていますが、APIキーの設定やレート制限に注意してください。
- DuckDB / SQLite のファイルアクセスは排他やパスの権限制約に注意。Streamlit ダッシュボードは read-only URI を使って開きます。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要なファイル・ディレクトリ構成の抜粋です（src/kabusys を想定）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他、broker_factory / execution_engine / order_repository 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (推奨ディレクトリ、DB・フラグファイル格納)
      - monitoring.db (SQLite デフォルト)
      - paper_trading.db
      - kabusys.duckdb
      - stop_requested.flag
      - kill.flag
      - execution.pid

---

## よくある質問（FAQ）

Q: Monitoring と Execution は同じ SQLite を使いますか？  
A: Monitoring（run_monitoring）は Settings.sqlite_path（デフォルト data/monitoring.db）を使います。Execution は環境（KABUSYS_ENV）に応じて paper_trading 用 DB を使うか本番 DB を使うか切り替えます（Settings.is_paper）。

Q: MONITOR_POLL_INTERVAL の最小値や不正値はどう扱われますか？  
A: 環境変数 MONITOR_POLL_INTERVAL が整数でない、または 1 未満の値ならばデフォルト 60 秒にフォールバックします。

Q: OpenAI キーがない場合は AI モジュールは使えますか？  
A: AI 関連関数は api_key 引数または環境変数 OPENAI_API_KEY を必須とするものがあり、未設定の場合は ValueError を送出します（呼び出し側でハンドリングしてください）。ただし、regime_detector は API 失敗時にフォールバック値（macro_sentiment=0.0）で継続する実装です。

---

## 貢献・拡張

- 単体テストを追加して各モジュールの外部依存（OpenAI / Broker / DB）をモックすることを推奨します。
- position sizing の lot_size や証券別の単元管理、費用バッファの改良、より詳細なマイグレーションフレームワーク導入などが想定されます。
- 運用監視・メトリクス収集（Prometheus / Grafana）連携やログ集約の追加も有益です。

---

この README はリポジトリ内のソース（src/kabusys/*.py）を参照して作成しています。実運用にあたっては各環境変数の設定、ブローカー API キー、適切な DB バックアップポリシーなどを整備してください。