# KabuSys

日本株自動売買システムの部分実装リポジトリ。  
本リポジトリには、監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、ファクターリサーチ、AI（ニュースセンチメント）周りのユーティリティ群が含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する複数コンポーネント群をまとめたコードベースです。主な目的は以下です。

- ExecutionEngine：ブローカー API 経由で注文を発行・管理するエンジン
- Monitoring：システム健全性・注文状況・リスクを定期チェックしてログ／アラート／キルスイッチを実行
- Research：DuckDB 上の時系列データからファクターや将来リターンを計算
- AI モジュール：ニュースを LLM（OpenAI）で評価して銘柄別センチメントを生成
- Portfolio：候補選定・重み付け・ポジションサイズ計算の純粋関数群
- Tools：ペーパートレーディングの検証レポート出力などの補助スクリプト

設計方針の一例：
- データ処理は基本的に DuckDB / SQLite を利用
- Paper Trading 環境は本番データベースと分離
- LLM 呼び出しはフェイルセーフ（エラー時はスコアを 0 等にフォールバック）で実装

---

## 主な機能

- システム監視（CPU / メモリ / ディスク / プロセス状態 / データ鮮度）
- 注文監視（滞留注文、約定価格異常の検出）
- リスク監視（ドローダウン、ポジション上限の監視とアラート／kill flag）
- LINE によるアラート送信（AlertManager）
- Streamlit ベースの監視ダッシュボード（読み取り専用）
- ExecutionEngine（Paper/Live 切替。Paper の場合 MockBroker を使用し専用 DB に記録）
- Reconciler（起動時の注文状態同期・ポジション差分検出）
- ポートフォリオ構築関数（候補選定、等重／スコア重み、リスク調整、株数計算）
- Research（モメンタム・ボラティリティ・バリューの計算、IC / 統計サマリ）
- AI モジュール：ニュースを LLM でスコアリング → ai_scores テーブルへ書き込み
- Tools：Paper Trading 検証レポート生成コマンド

---

## セットアップ

前提
- Python 3.9+（ソースは型ヒント等で 3.10 を想定している箇所がありますが、3.9 以降で動作します）
- Git レポジトリのクローン

推奨手順（概要）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt がない場合は上記を目安にインストールしてください。実行に応じて他パッケージが必要になる場合があります。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 例（最低限の必須項目）：
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を利用する場合）
     - KABUSYS_ENV=development | paper_trading | live
     - (任意) PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - (任意) SQLITE_PATH=data/monitoring.db
     - (任意) DUCKDB_PATH=data/kabusys.duckdb
     - (任意) LINE_CHANNEL_ACCESS_TOKEN=...（アラート送信に使用）
     - (任意) LINE_USER_ID=...

5. データディレクトリ作成
   - mkdir -p data

注意点
- Settings クラスで必要な環境変数を require している箇所があります（未設定時は ValueError）。
- PAPER_FILL_MODE の有効値: instant, partial, never, reject
- KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかでなければなりません。

---

## 使い方

以下は主要な実行コマンド例です。プロジェクトルートから実行してください。

1. 監視プロセスを起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 補足:
     - デフォルトのポーリング間隔は 60 秒です。環境変数 MONITOR_POLL_INTERVAL で上書き可能（整数秒）。
     - 停止は data/stop_requested.flag を作ることで監視ループが検知して終了します（または Ctrl+C）。

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 専用 DB（デフォルト: data/paper_trading.db）を使います。本番 DB と分離されます。
     - 実行中に data/stop_requested.flag を作成するとエンジンが安全に停止します。
     - 実行時に優先度を high に設定しようとします（psutil による設定。権限により失敗することがありますがログに記録されます）。

3. Paper Trading 検証レポートの生成
   - python -m kabusys.tools.paper_verification_report
   - 期間を指定する場合:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db /path/to/paper_trading.db
     - 環境変数 PAPER_TRADING_SQLITE_PATH が優先されます（引数 > 環境変数 > デフォルト）。

4. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは SQLite を読み取り専用モードで開きます（DB が存在しない場合は起動前に Monitoring を実行してください）。

5. AI 機能（ニューススコア・レジーム判定）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して利用します（プログラム経由で呼ぶことを想定）。
   - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用します。

停止／キルフラグ
- data/stop_requested.flag：run_monitoring / run_execution が監視している停止フラグ（存在を検知してループを抜ける）
- data/kill.flag：KillSwitch（リスク条件で ExecutionEngine を停止するためのフラグ）。KillSwitch は理由文字列を内容として書き込みます。
- data/execution.pid：ExecutionEngine の PID を書き込むファイル。SystemMonitor はこの PID ファイルを見てプロセス生存確認します。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しで使用（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に使用（任意）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, ...（Settings クラスを参照ください）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化できます

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / 設定読み込みと Settings クラス（.env 自動ロードロジック含む）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（Paper/Live 切替を含む）

サブパッケージ（主要モジュール）
- execution/
  - order_manager.py — 注文 State Machine の外向き API
  - reconciler.py — 起動時の注文・ポジション照合
  - （その他 broker/engine/ repository 実装群 が想定されます）
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（init / CRUD）
  - system_monitor.py — CPU/メモリ/ディスク / プロセス / データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限のチェック
  - kill_switch.py — kill.flag の書き込みロジック
  - alert_manager.py — LINE Push による通知
  - monitoring_engine.py — 各モニタの統合ループ
  - streamlit_dashboard.py — Streamlit での監視ダッシュボード
- ai/
  - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込む処理
  - regime_detector.py — ETF + マクロニュースで市場レジームを判定
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ等
- portfolio/
  - portfolio_builder.py — 候補選定・等配分・スコア配分
  - position_sizing.py — 株数計算・集約キャップ処理
  - risk_adjustment.py — セクター上限・レジーム乗数
- utils/
  - process_priority.py — psutil ベースで優先度 / CPU affinity を設定するユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

data/
- （実行時に生成される SQLite / DuckDB ファイルやフラグファイル置き場。デフォルトパスを使用する場合ここに DB を置きます）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kabusys.duckdb（DUCKDB_PATH）
  - stop_requested.flag / kill.flag / execution.pid 等

---

## 注意事項・トラブルシュート

- psutil によりプロセス優先度や CPU affinity を設定しますが、権限不足で失敗することがあります（警告ログが出ますが処理は継続します）。
- DuckDB / SQLite の接続はファイルパスで行われます。既存ファイルとのマイグレーション（例: カラム追加）ロジックが一部実装されています（monitoring_db.init_monitoring_db）。
- OpenAI API を利用する機能はネットワーク依存です。API エラー時はリトライやフェイルセーフ（スコア 0 など）を行う実装になっていますが、API キーの設定は必須です。
- Paper Trading と Live は DB を分離しているため、paper_trading 環境で誤って本番 DB を操作するリスクは低く設計されています（Settings.is_paper による分岐）。

---

## 開発にあたっての補足

- 多くのモジュールは「副作用の少ない純粋関数」か「DB/外部 API に対する薄いラッパー」で実装されています。ユニットテストが書きやすい設計を目指しています（例: AI API 呼び出しはラップしてモックしやすくしてある）。
- 各モジュールのドキュメント文字列（docstring）に設計方針や注意事項が詳述されています。実装や拡張を行う際はまず docstring を参照してください。

---

必要であれば、実行例（環境変数を設定した .env 例）、systemd / supervisor でのプロセス管理例や、CI 用のセットアップ手順、単体モジュールの簡単な API 使用例などの追加ドキュメントも作成できます。どの情報を優先して追加しますか？