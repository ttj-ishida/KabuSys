# KabuSys

日本株自動売買システムのコアライブラリ / ツール群の README（日本語）

このリポジトリは自動売買エンジン、監視、ポートフォリオ構築、リサーチ／AI 補助モジュールなどを含むモジュール群です。  
下記はプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリです。主な目的は以下：

- 実行エンジン（ExecutionEngine）による発注管理（paper/live 切替対応）
- 監視サブシステム（MonitoringEngine）によるプロセス/リソース/注文の監視とアラート／Kill Switch
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- Paper Trading 検証レポート生成ツール

設計方針として、DB（SQLite / DuckDB）を利用したデータ永続化、環境変数ベースの設定、フェイルセーフ（API 失敗時のフォールバック）等を重視しています。

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV による paper_trading / live の切替
  - paper_trading 時は MockBrokerClient を使い、専用 SQLite（デフォルト: data/paper_trading.db）に分離
  - リスク管理（RiskManager）や OrderManager、Reconciler を組み合わせた ExecutionEngine

- 監視（run_monitoring.py / MonitoringEngine）
  - システム資源（CPU/Memory/Disk）、プロセス生存、データ鮮度、注文の滞留や約定異常を定期監視
  - Kill Switch（ファイルベース）による Execution 停止シグナル
  - 監視データは SQLite（デフォルト: data/monitoring.db）へ永続化

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重/スコア重み付け、レジーム乗数、セクター上限適用
  - 発注株数（単元株）を考慮したポジションサイズ算出（risk_based / equal / score）

- リサーチ（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC, 統計サマリー等

- AI（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini）でニュースを銘柄別にセンチメント付与し ai_scores テーブルへ保存
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）

- ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
  - 環境変数・設定管理（kabusys.config）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントの | 演算子等を利用）
- 推奨パッケージ（主要機能を使う場合）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証は任意）
- 標準ライブラリ: sqlite3, logging, argparse など

（requirements.txt はこのリポジトリには含まれていないため、必要に応じて下記をインストールしてください）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数の準備
   - 対話式に .env を作成する:
     - python -m kabusys.config_setup
   - または手動で .env を作成（ルートに .env）。必要な主要キー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）

5. 設定の事前検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリの確認
   - デフォルトの DB や PID / フラグファイルは data/ 配下に置かれます。logs/ ディレクトリにログが書かれます（kabusys.utils.logging_setup が自動作成）。

---

## 使い方（主なコマンド）

- 実行エンジンを起動（デーモン管理は外部で）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループは data/stop_requested.flag が存在すると終了します（停止フラグ）。

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ関数をプログラムから呼ぶ（例）
  - ニューススコア付与（プログラム内で）:
    - from kabusys.ai import score_news
    - n = score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意: AI 関連は OpenAI API キー（OPENAI_API_KEY / api_key 引数）が必須です。API 呼び出し失敗時は安全側のフォールバック（例: macro_sentiment=0.0）を行う設計になっていますが、キーが無い場合は例外が発生します。

---

## 監視 / Kill Switch の挙動

- kill.flag（デフォルト: data/kill.flag）は ExecutionEngine に対する停止要求に利用されます（Settings.kill_flag_path）。
- Monitoring がリスク条件（例: ドローダウン超過、ポジション上限超過）を検出すると、KillSwitch が flag を書き込みます（既存の flag があれば再書き込みしない）。
- ExecutionEngine / run_execution.py は data/stop_requested.flag または kill.flag 等の存在を確認して停止処理を行います（run_execution は data/stop_requested.flag を監視してスレッドを停止します）。
- 強制停止や手動停止は flag ファイルを作成することで行えます。逆に ExecutionEngine 起動時に Settings.kill_flag_clear_on_start を 1 にしておくと自動でクリアしますが、本番では 0 を推奨します。

---

## 主要ファイルとディレクトリ構成

（src/kabusys 以下を要約）

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / 設定管理（Settings クラス）
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 起動前設定検証 CLI

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス生存チェック
  - trade_monitor.py — （注文関連監視モジュール、コードベースに存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視（RiskMonitor）
  - kill_switch.py — ファイルベースの Kill Switch
  - monitoring_engine.py — モニタ群の束ね役

- execution/（実行エンジン関連: BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - run_execution.py から組み立てて起動

- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 株数計算・集計上限・丸め
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — レジーム判定（MA200 + LLM）
  - __init__.py (score_news 等をエクスポート)

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- data/（実行時に使用する DB / PID / flag 等を配置するディレクトリの例）
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用デフォルト）
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution の動作モード: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — MockBroker の約定モード（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

---

## 開発メモ / 注意事項

- DuckDB 接続は research / ai モジュールで使われます。 prices_daily や raw_financials テーブルの存在が前提です。
- monitoring_db.init_monitoring_db は冪等にテーブル作成とマイグレーション（列追加）を行います。
- OpenAI API 呼び出しではリトライ・バックオフやレスポンス検証を実装しており、失敗時は安全側のフォールバックを行いますが、API キー自体が無い場合は失敗します。
- 実環境（KABUSYS_ENV=live）では LINE 通知等の設定確認や Kill Switch 設定を慎重に行ってください（validate_config に live 向けのガードも組込まれています）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗するとコンソールのみで継続します。

---

この README はコードベースからの抜粋に基づく概要です。各モジュールの詳細や拡張点は該当ファイルの docstring / コメントを参照してください。必要であれば、さらに具体的な使用例（ExecutionEngine の引数や OrderManager の API など）を追記します。