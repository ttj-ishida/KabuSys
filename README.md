# KabuSys

日本株向け自動売買システムの一部を実装したモジュール群です。本リポジトリは実運用向けの監視・実行・リサーチ・AI ツールを含み、SQLite / DuckDB を用いたローカル永続化と外部 API（kabuステーション、J-Quants、OpenAI 等）との連携を想定しています。

---

## 概要

- 監視（Monitoring）：システム状態、注文滞留、ドローダウン等をポーリングしてログ/アラート出力。ダッシュボード（Streamlit）や LINE 通知をサポート。
- 実行（Execution）：Broker クライアント経由で発注を行う ExecutionEngine（起動スクリプトを含む）。paper_trading モードではモックブローカーを使用して本番 DB と分離。
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、リスク調整、株数計算など純粋関数群。
- リサーチ（Research）：DuckDB 上でファクター計算・特徴量解析を実行するユーティリティ群。
- AI（AI）：ニュースの NLP による銘柄センチメント評価や市場レジーム判定（OpenAI API を利用）。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
- TradeMonitor：滞留注文・約定異常価格の検出
- RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
- KillSwitch：条件成立時に flag ファイルを書き ExecutionEngine 停止指示
- MonitoringEngine：上記 Monitor を束ねて定期実行（ポーリング）
- AlertManager：LINE Messaging API による通知（クールダウン機構付き）
- Streamlit ダッシュボード（監視データ閲覧）
- ExecutionEngine 起動スクリプト（paper_trading モード対応）
- Paper Trading 検証レポート生成ツール（期間指定でレポート出力）
- Portfolio モジュール（候補選定・重み・ポジションサイズ計算）
- Research モジュール（ファクター計算、IC、統計サマリ）
- AI モジュール（news_nlp: ニュースセンチメント、regime_detector: 市場レジーム判定）

---

## 必要環境 / 依存パッケージ（例）

Python 3.10+ を想定しています。実行には以下の主要ライブラリが必要です（requirements.txt を用意している場合はそちらを使ってください）。

- duckdb
- psutil
- requests
- openai (または OpenAI の SDK)
- streamlit (ダッシュボードを使う場合)
- その他、標準ライブラリ

インストール例:
pip install duckdb psutil requests openai streamlit

（実際のプロジェクトでは requirements.txt を用意することを推奨します）

---

## セットアップ

1. リポジトリをクローンしてソースが入ったディレクトリを作業ディレクトリにする。
2. 仮想環境を作成して依存をインストールする（上記参照）。
3. プロジェクトルートに `.env` / `.env.local` を置くと自動で環境変数を読み込みます（ただし OS 環境変数が優先され、`.env.local` は上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. データディレクトリ（デフォルト `data/`）を作成しておくと便利です。

主要な環境変数（例・説明）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、paper_trading 用の SQLite DB とモックブローカーが使われ、本番 DB と完全分離されます。
- PAPER_FILL_MODE — Paper Trading の約定モード (`instant` / `partial` / `never` / `reject`; デフォルト: instant)
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60。run_monitoring で参照）

例 .env（雛形）
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO

---

## 起動 / 使い方

各モジュールはモジュール実行形式で起動できます。ソースツリーが PYTHONPATH に入るようにプロジェクトルートから実行してください（例: src を package ルートにしている場合は python -m kabusys.xxx）。

1. 監視ループ（SystemMonitor 単体起動）
   - コマンド:
     python -m kabusys.run_monitoring
   - 説明:
     - デフォルトで MONITOR_POLL_INTERVAL=60 秒。環境変数で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
     - 起動時にプロセス優先度を "high" に設定し、SQLite（monitoring DB）と DuckDB に接続します。
     - 監視は本番 sqlite_path を利用（KABUSYS_ENV に依らず本番 DB を想定）。

2. 実行エンジン（ExecutionEngine）
   - コマンド:
     python -m kabusys.run_execution
   - 説明:
     - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
     - 起動時にプロセス優先度を "high" に設定します。
     - 起動後は ExecutionEngine.run_session() を実行（内部で注文処理等を行います）。

3. Streamlit ダッシュボード（監視 UI）
   - コマンド:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - `--db` で監視 DB のパスを指定（デフォルト: data/monitoring.db）。
     - read-only 接続で表示します。MonitoringEngine を先に起動してデータを作成してください。

4. Paper Trading 検証レポート
   - コマンド:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - 説明:
     - PAPER_TRADING_SQLITE_PATH 環境変数または `--db` で DB を指定できます。
     - 出力は標準出力に検証サマリ（稼働率、成功率、送信率、レイテンシ等）を表示します。

5. AI / レジーム判定等（プログラム呼び出し）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime はプログラムからインポートして使用します。
   - OpenAI API を使う機能は `OPENAI_API_KEY` を環境変数か関数引数で渡す必要があります。
   - エラー時はフェイルセーフ（スコア 0 やスキップ）で継続する設計です。

---

## 重要な挙動・注意点

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数優先）。
  - 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- DB 分離（paper_trading）
  - `KABUSYS_ENV=paper_trading` の場合、Execution は paper_trading 用 SQLite を使用して本番 DB と分離されます（安全対策）。

- PID / kill.flag
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を使ってプロセス生存を管理します。
  - KillSwitch は `KILL_FLAG_PATH`（デフォルト data/kill.flag）を作成することで外部から ExecutionEngine の停止をトリガーできます。起動時にフラグをクリアするオプションも設定可能（Settings.kill_flag_clear_on_start）。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil を用いた OS 毎の制御）。権限不足等で失敗する可能性があり、その場合は警告が出ます。

- OpenAI（API）利用
  - ニュース NLP / レジーム判定は OpenAI API（gpt-4o-mini 等）を想定。429 やネットワークエラー等はエクスポネンシャルバックオフでリトライしますが、最終的に失敗した場合はフェイルセーフ（スコア 0.0 等）で継続します。
  - API キーは `OPENAI_API_KEY` 環境変数で設定してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込みロジック
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py — psutil を使った優先度 / affinity 設定
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite テーブル作成・簡易永続化 API
  - system_monitor.py — CPU / メモリ / データ鮮度 / PID チェック
  - trade_monitor.py — 滞留注文 / 約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイル書き込みロジック
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 監視コンポーネント統合
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ...（発注・同期・再起動復旧ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 株数計算・スケーリング
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility 計算
  - feature_exploration.py — 将来リターン / IC / 統計
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — マクロ + ETF によるレジーム判定（OpenAI）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

データディレクトリ（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag

---

## 開発・運用に関するメモ

- DB マイグレーションは簡易的に実装されています（monitoring_db.init_monitoring_db は列追加を試みます）。
- ai モジュールやブローカーファクトリ等は外部 API への依存が大きいため、単体テストではモックを利用する前提です（コード中にモック対応箇所あり）。
- ロギングは標準 logging を使用。環境変数 `LOG_LEVEL` で制御できます。

---

README に記載のない個別の使い方や API、設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する想定です。必要であればそれらの抜粋やサンプル設定、起動例（systemd ユニット / supervisor 設定）などの追加ドキュメントを作成します。どの情報を優先的に追加しますか？