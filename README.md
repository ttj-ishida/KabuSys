# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の主要機能をモジュール単位で提供します：発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター計算・研究、ニュースNLP（OpenAI 経由）など。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要
- 日本株自動売買システム（KabuSys）のコアロジック群。
- 発注管理、リコンシリエーション、リスク管理および監視・アラート、研究用ファクター計算、ニュースの LLM によるセンチメント評価を含む。
- DuckDB を用いた時系列データ分析、SQLite による監視ログ／トレードログ保存。
- OpenAI API を利用したニュース NLP / レジーム判定機能を備える（任意）。

## 主な機能一覧
- Execution（実行）
  - ExecutionEngine による発注セッション管理
  - Broker クライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - OrderManager / OrderRepository / Reconciler による注文状態管理と再同期
  - RiskManager による発注時の制約（最大ポジション比率等）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留 / 約定価格異常の検知
  - RiskMonitor: ドローダウン・ポジション数上限の検知
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み・LINE 通知
  - streamlit ダッシュボード（監視用）
- Portfolio（ポートフォリオ構築）
  - 銘柄選定（スコア順）、等配分 / スコア加重配分
  - セクター上限適用、レジーム乗数、株数決定（lot 単位で丸め）
- Research（研究）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）・統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース集合を LLM に投げて銘柄ごとセンチメントを ai_scores に書き込み
  - regime_detector: マクロニュース + ETF(1321) の MA200 乖離を合成して market_regime を算出
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、成功率、レイテンシ等）

## 依存関係（概要）
- Python 3.9+（型アノテーション等を使用。実運用では 3.10+ 推奨）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード実行時）
- 標準ライブラリ: sqlite3, logging, datetime, argparse ほか

pip インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt がある場合はそちらを使用してください）

## セットアップ手順（簡易）
1. リポジトリをクローン／チェックアウト。
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. プロジェクトルートに `.env` を作成（`.env.example` を参考に必要な環境変数を設定）。
   - 自動ロードが不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能（テスト時など）。
4. データディレクトリを作成（必要に応じて）:
   - デフォルトの DB パス: `data/monitoring.db`（monitoring）, `data/kabusys.duckdb`（DuckDB）, `data/paper_trading.db`（paper_trading）
   - 実行 PID / フラグ用: `data/execution.pid`, `data/kill.flag`, `data/stop_requested.flag` など
5. （Paper Trading）モードで動かす場合は `KABUSYS_ENV=paper_trading` を設定すると mock ブローカー・別 DB を使用。

## 環境変数（主要）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading のときは mock ブローカー・別 SQLite (`PAPER_TRADING_SQLITE_PATH`) を使用
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants 関連トークン
- KABU_API_PASSWORD: （必須）kabu API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
- PAPER_FILL_MODE: paper_trading 時の約定モデル ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine が書き込む PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: "1" で start 時に kill.flag を自動クリア
- LOG_LEVEL: ログレベル（"DEBUG" 等）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）。不正値や <=0 はデフォルトにフォールバック。

## 実行方法（代表例）

- 監視ループを起動（monitoring）
```
# デフォルトの monitoring DB/paths を使う
python -m kabusys.run_monitoring
# or
KABUSYS_ENV=development MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
備考:
- run_monitoring は環境にかかわらず「本番 sqlite_path（設定された SQLITE_PATH）」を監視 DB として使用します。
- ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能。0 以下や不正な文字列は 60 秒にフォールバック。
- 停止: Ctrl+C、またはプロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループが終了します。

- 実行エンジンを起動（ExecutionEngine）
```
python -m kabusys.run_execution
# Paper Trading の場合
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
備考:
- paper_trading 時は MockBrokerClient を使用し、paper 用 DB（デフォルト data/paper_trading.db）へ書き込みを行います。本番 DB と完全分離されます。
- 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
- 実行中に `data/stop_requested.flag` を作成するとエンジンが停止します。
- ExecutionEngine は起動時に PID ファイルを生成します（Settings.pid_file_path）。

- Paper Trading 検証レポートを生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
出力: 稼働率、注文成功率、送信率、レイテンシ等のレポート。DB が存在しない場合はエラーを出力します。

- Streamlit ダッシュボード（監視）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
ブラウザで監視用ダッシュボードを確認できます（読み取り専用モードで SQLite を開きます）。

- AI 関連（news_nlp / regime_detector）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。キー未設定時は例外が発生します。
  - news_nlp.score_news, regime_detector.score_regime の各関数は DuckDB 接続と target_date を受け取ります。コマンドラインエントリは提供されていないため、スクリプトや管理ジョブから呼び出して利用してください。

## ファイルベースの停止・警告フロー
- data/stop_requested.flag: run_monitoring / run_execution のループを終了させる（存在を検知して正常終了）。
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine 停止用）。KillSwitch はドローダウンやポジション上限超過で書き込む。既存の kill.flag がある場合は再書き込みしない（冪等）。
- PID ファイル: ExecutionEngine の PID を pid_file_path（デフォルト data/execution.pid）に保存。SystemMonitor は該当 PID の存否をチェックし stale PID 検出時にファイルを削除してアラートを上げる。

## ディレクトリ構成（主要ファイルの説明）
リポジトリの主要なパッケージ構成（src/kabusys）:

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA で市場レジーム判定
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite の初期化・読み書きラッパー（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - alert_manager.py — LINE による通知（push）
    - kill_switch.py — 条件に応じて kill.flag を書き込む
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注の外向き API（OrderManager）
    - reconciler.py — 起動時のリコンシリエーション（復旧）
    - （その他: broker_factory, execution_engine, order_repository など、発注関連コンポーネントが存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・資金配分・スケール調整
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - data/（実行時生成）
    - monitoring.db, kabusys.duckdb, paper_trading.db, execution.pid, kill.flag, stop_requested.flag など

（上記は主要ファイル抜粋。実際のコードベースにはさらに細かいモジュールが含まれます）

## 開発者向けの注意事項 / 運用メモ
- Settings は自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数は上書きされません）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の DB 初期化（init_monitoring_db）は冪等です。既存 DB に対して必要なマイグレーション（カラム追加）も行います。
- MONITOR_POLL_INTERVAL の値が不正（文字列や 0/負数）だとデフォルト 60 秒にフォールバックします。
- Process priority や CPU affinity 設定は psutil を使います。権限不足で失敗することがあるため、失敗時は警告ログが出てスキップされます。
- OpenAI を使う機能は API 呼び出し失敗に対してバックオフ・フェイルセーフ処理を入れていますが、API キーの管理・レート制御は運用側で注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離する設計になっています。実運用時に誤って本番 DB を上書きしないよう環境変数を確認してください。

## よく使うコマンドまとめ
- 仮想環境作成、依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt もしくは個別パッケージインストール
- 監視起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースに基づく要点をまとめたものです。実運用前に `.env.example`（存在する場合）を参照し、必要な環境変数や API キー・DB パスを正しく設定してください。追加の詳細（API 実装、Broker adapter、ExecutionEngine の動作など）は各モジュールの docstring を参照してください。