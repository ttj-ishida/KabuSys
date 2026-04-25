# KabuSys

日本株向け自動売買システムのコアライブラリ群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 支援など）。

この README はリポジトリ内の主要スクリプト／モジュールに基づいて、セットアップ方法・使い方・構成を簡潔にまとめたものです。

注意: 実行に必要な外部パッケージ（duckdb, psutil, openai など）は環境に応じてインストールしてください。requirements.txt はこのリポジトリに含まれていない想定です。

## プロジェクト概要
- 目的: 日本株の自動売買に関わる実行エンジン（ExecutionEngine）とそれを支える監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLPベースのスコアリング、レジーム判定などを提供する。
- 設計方針:
  - 実行系と監視系はファイルベース（SQLite / DuckDB / フラグファイル）で連携し、本番とペーパートレードを分離可能。
  - LLM（OpenAI）を使った処理は冪等性と失敗時のフォールバックを重視。
  - 多くの機能は純粋関数（DB に依存しない）で実装され、テストしやすく設計。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番／ペーパートレード分離（KABUSYS_ENV に依存）
  - ブローカークライアントの抽象化（Mock を含む）
  - PID 管理・停止フラグ検出
- Monitoring（run_monitoring.py, monitoring/*）
  - システムリソース監視（CPU/メモリ/ディスク）
  - 発注／約定ログ監視（stale order, anomaly）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（kill.flag）による実行系停止
  - アラート管理（AlertManager 経由）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ（research/*）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）など
- AI（ai/*）
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（価格 + マクロ記事による LLM 合成）
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ（utils/*）
  - ロギング設定（ログローテート）
  - プロセス優先度 / CPU affinity 設定

## 必要要件（例）
以下をインストールしてください（バージョンは適宜調整）。
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）
- その他プロジェクトで使う依存パッケージ

例:
pip install duckdb psutil openai pyyaml

## セットアップ手順（ローカル）
1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # (Windows では .venv\Scripts\activate)
3. 必要パッケージをインストール:
   pip install duckdb psutil openai pyyaml
4. .env の準備（対話式ウィザードを推奨）:
   python -m kabusys.config_setup
   ウィザードで入力された値はプロジェクトルートの .env に保存されます。
5. 設定検証:
   python -m kabusys.validate_config
   --strict オプションを付けると警告も失敗扱いになります。

## 環境変数（主なもの）
Settings クラスで扱われる代表的な環境変数（デフォルトは括弧内）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — デフォルト: "instant"
- KABUSYS_ENV ("development" | "paper_trading" | "live") — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- LOG_DIR (ログ出力先ディレクトリ、デフォルト: logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト: 60)

.env は Git にコミットしないでください（機密情報を含むため）。

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 実行中は data/execution.pid（デフォルト）に PID を書く等の管理を行います。
  - 停止条件: data/stop_requested.flag を作成すると起動スレッド検出で停止します。

- 監視プロセス起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings にかかわらず本番 sqlite_path（data/monitoring.db など）を使用します。
  - 停止条件: data/stop_requested.flag が検出されると終了します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI / レジーム・ニューススコア（プログラムから呼び出す例）
  from datetime import date
  import duckdb
  from kabusys.ai import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  -> ai_scores テーブルへ書き込まれた銘柄数を返します。

注意: OpenAI API 利用には環境変数 OPENAI_API_KEY または api_key 引数が必要です。

## 停止・フラグ関連
- data/stop_requested.flag
  - run_execution / run_monitoring がループ中に存在をチェックし、存在すると優雅に停止します（外部から停止するときに使用）。
- data/kill.flag
  - KillSwitch により書き込まれ、ExecutionEngine に対する強制停止シグナルとして機能します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では推奨されません（安全のため 0 を推奨）。

## ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（logs/<app_name>.log）。
- LOG_DIR 環境変数または setup_logging の引数で変更可能。
- コンソール出力は stdout を使用します。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/ — 発注周りコンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, 等）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 + DB 操作ラッパ
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（ファイル参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — フラグ書き込みによる停止
    - alert_manager.py — アラート送信（LINE 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数決定・総額調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM センチメントスコアリング
    - regime_detector.py — 市場レジーム判定 (ma200 + macro sentiment)
  - data/ — 実行時に使うファイル群（デフォルト）
    - monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（注）一部モジュールはこの README 作成時点の抜粋に基づいて説明しています。実際の機能や追加ファイルはリポジトリ全体を参照してください。

## 開発上の注意
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にする、LINE 通知等を正しく設定する等の安全ガードを確認してください。
- DuckDB / SQLite のパスは Settings で上書きできます。ペーパートレードは専用 DB に記録され本番 DB と分離されます。

---

さらなる詳細（各モジュールの使用方法や内部設計）は該当ソースファイルの docstring / コメントを参照してください。README に抜けや不明点があれば、どの項目を追記すべきか教えてください。