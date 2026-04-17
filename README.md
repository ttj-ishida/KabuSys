# KabuSys

日本株自動売買システムの軽量実装（モジュール群のスニペットを基にしたリポジトリ）。  
本リポジトリは主に以下の責務を持つコンポーネント群で構成されています：実行エンジン、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI（ニュースNLP / レジーム判定）、およびユーティリティ。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する以下の要素を備えます。

- ExecutionEngine：ブローカークライアントを使った注文作成・管理・リスク制御・再同期（Reconciler）等。
- Monitoring：システム稼働状況・注文滞留・ドローダウンなどの監視、アラート送信（LINE）、停止フラグの発行。
- Portfolio：銘柄選定・重み計算・ポジションサイズ決定などのポートフォリオ構築ロジック（純粋関数群）。
- Research：DuckDB 上の価格・財務データを使ったファクター計算・将来リターン/IC分析。
- AI：OpenAI を用いたニュースのセンチメント評価（news_nlp）や、市場レジーム判定（regime_detector）。
- Tools：Paper Trading 検証レポート生成など、運用支援ツール。

この README はリポジトリ内の主要スクリプトの使い方、設定、ディレクトリ構成を説明します。

---

## 主な機能一覧

- 実行モード切替（開発 / paper_trading / live）
- Paper Trading 用のブローカーのモック化と専用 DB 分離
- 注文管理（OrderManager）、再同期（Reconciler）
- リスク管理（最大ポジション割合、利用率、ドローダウン等）
- 監視機能
  - CPU / メモリ / ディスク割合のログ
  - データ鮮度チェック（DuckDB の最終価格日）
  - 注文滞留・約定異常価格検知
  - ドローダウン・ポジション上限の監視と kill flag 書き込み
  - LINE によるアラート送信（AlertManager）
  - ストリームリットによる監視ダッシュボード
- ポートフォリオ構築
  - 候補選定（スコア/等配分）、セクター制限、ポジションサイズ計算（lot 整数丸め、aggregate cap 処理）
- Research（DuckDB）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン・IC・統計サマリ
- AI 機能
  - ニュースを LLM（gpt-4o-mini）でスコア化し ai_scores に保存
  - ETF(ma200) とマクロニュースを組み合わせた市場レジーム判定

---

## セットアップ手順

前提：Python 3.8+（コードは型ヒントで 3.10+ 想定）。SQLite は標準ライブラリ。外部ライブラリを使う箇所あり。

推奨インストール（例）:

pip を使う場合:
```
pip install duckdb psutil requests streamlit openai
```

推奨的に requirements.txt を用意している場合は：
```
pip install -r requirements.txt
```

必須ディレクトリ作成:
```
mkdir -p data
```

環境変数（.env）:
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

例（.env）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_userid
LOG_LEVEL=INFO
```

準備（DB 初期化等）:
- run_monitoring.py / run_execution.py の起動時に必要なテーブルは自動で作成されます（init_monitoring_db が実行されます）。

注意:
- Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を用い、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。本番 DB と完全分離されます。
- OpenAI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。

---

## 環境変数一覧（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）（デフォルト: instant）
- PID_FILE_PATH: 実行エンジン PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag path（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag をクリアするか（1 でクリア）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

自動 .env 読み込みの優先順位:
1. OS 環境変数
2. .env.local（存在すれば優先上書き）
3. .env

---

## 使い方

※ コマンドはプロジェクトルート（src がある場所）を想定しています。パッケージをインストールしている場合は python -m kabusys.xxx でも動きます。

1) 実行エンジン（ExecutionEngine）を起動
- 本番 / 開発 / paper_trading は KABUSYS_ENV により切替。
- Paper Trading の場合は PAPER_TRADING_SQLITE_PATH を使い、MockBroker を使う。

例（Paper Trading）:
```
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

例（Live / Development）:
```
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

実行エンジンは data/execution.pid を作成し、停止は data/stop_requested.flag を作るか（run_execution が検出して停止）、kill.flag（Settings.kill_flag_path）で停止トリガーとすることができます。

2) 監視プロセスを起動
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（デフォルト 60）。
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用し、モニタリングテーブルの初期化を行います。

3) Streamlit 監視ダッシュボード
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
読み取り専用モードで DB に接続します。MonitoringEngine が作成する monitoring.db を参照してください。

4) Paper Trading 検証レポート生成ツール
- 期間を指定して paper_trading DB からレポートを生成します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
```

5) AI 機能（ニューススコア / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続と日付で呼び出し、ai_scores に書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルに書き込みます。
- コマンドラインエントリは用意されていませんが、スクリプトから呼び出して使用します（OPENAI_API_KEY 必須）。

停止フロー / フラグ:
- data/stop_requested.flag — 実行ループの外部停止指示に使用（両 run_* スクリプトで検出）。
- data/kill.flag — KillSwitch が書き込み、実行エンジンを停止させるためのフラグ（監視が治安上の理由で発行）。

---

## 開発・デバッグのヒント

- Settings は .env / .env.local を自動でロードしますが、テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Process 優先度や CPU affinity は utils.process_priority.set_process_priority / set_cpu_affinity で制御しています。呼び出し時に初期設定で High に上げる実装になっています（プラットフォームの権限による制約あり）。
- DuckDB は prices_daily / raw_financials 等の表を期待します。研究モジュールは DuckDB コネクションを受け取り SQL + Python で処理します。
- monitoring_db.init_monitoring_db は冪等的にテーブルと必要なカラムを作成・マイグレーションします（起動のたびに安全に呼べます）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数 / 設定の読み取りロジック（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading レポート生成ツール（CLI）
  - execution/
    - execution_engine.py — ExecutionEngine（起動・セッション管理） ※実装ファイルはリポジトリに依存
    - order_manager.py — OrderManager（発注フロー）
    - order_repository.py — OrderRepository（SQLite）
    - reconciler.py — Reconciler（再同期）
    - broker_factory.py — Broker クライアント生成（paper/mock/live 切替）
    - ...（その他実装ファイル）
  - monitoring/
    - monitoring_db.py — monitoring SQLite のスキーマ & DB API
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — 注文滞留 / 価格異常の検出
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE 通知実装
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・キャップ調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等ファクター計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化（ai_scores へ書込）
    - regime_detector.py — マクロ + ma200 を使ったレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/  — デフォルトの DB / flag / pid ファイル格納先（実行時に作成）

---

## ライセンス / 貢献

この README はコードスニペットから作成されています。実運用で使用する際は以下を検討してください：

- 実ブローカー API の取扱い（鍵・認証・ネットワーク）に関するセキュリティ対策
- エラーハンドリング、テスト、CI、監査ログ等の整備
- 資金管理・規制遵守（実運用時は自己責任）

貢献や改善提案は Pull Request / Issue を通じて歓迎します。

---

もし README のフォーマット（追加のセクションやコマンド例、詳細な env サンプル、要件ファイルの推奨内容など）を拡充したければ、目的（運用手順 / デプロイ / 開発環境）を教えてください。必要に応じて追記します。