# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。
本リポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、
LLM を使ったニューススコアリング等のコンポーネント群を含みます。

この README ではプロジェクト概要、機能一覧、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- 目的: 日本株の自動売買パイプライン（発注、リスク管理、監視、レポーティング、リサーチ、AI スコアリング等）を統合したサンプルシステム。
- 設計方針:
  - モジュール化: 発注ロジック、監視、ポートフォリオ、リサーチ、AI 部分を分離。
  - 可能な限り副作用を排し、DuckDB / SQLite 等のローカル DB を用いた解析・永続化。
  - 本番・ペーパートレードの切替を環境変数で制御。
  - LLM（OpenAI）呼び出しは失敗時フェイルセーフで継続。

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine を起動してブローカー経由で発注（Kabuステーションなど）。  
  - `KABUSYS_ENV=paper_trading` で MockBroker を使用し、paper_trading DB に記録（本番 DB と分離）。
  - PID ファイル・停止フラグによる安全停止制御。

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングし、system_status / trade_logs / risk_logs / dashboard に記録。
  - Kill Switch による自動停止（例: ドローダウン超過）と LINE 通知等のアラート連携（設定がある場合）。
  - 監視ループは環境にかかわらず本番 sqlite_path を使用。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定、等重・スコア重み、リスクベースのポジションサイジング。
  - セクターキャップ、レジーム乗数の適用。

- リサーチ（Research）
  - DuckDB 上でのファクター計算（Momentum, Volatility, Value 等）。
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー。

- AI（LLM）連携
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores テーブルへ格納。
  - マクロニュース + ETF MA200 乖離を使った市場レジーム判定。

- ツール
  - 設定ウィザード（.env の対話式作成）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存例（手動インストール）:
     - pip install duckdb psutil openai

3. プロジェクトルートに移動（パッケージは src 配下に配置されている前提）
   - python の実行モジュールにパスを通す（例: 開発時）
     - export PYTHONPATH=src  (Windows: set PYTHONPATH=src)

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 作成後に設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ
   - ログ: デフォルトは logs/
   - DB / PID / フラグ: デフォルトは data/
   - 必要に応じて次のファイルに注意:
     - data/execution.pid（ExecutionEngine 用 PID）
     - data/kill.flag（Kill Switch 用フラグ）
     - data/stop_requested.flag（run_* スクリプトの外部停止用）

---

## 使い方（主要スクリプト・API）

- ExecutionEngine の起動
  - コマンド:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV によって本番 DB / paper_trading DB を切り替える。
    - 起動時に data/stop_requested.flag が存在すると起動を中止。
    - 終了は stop flag を作成するか SIGINT（Ctrl-C）。
  - PID/stop フラグ:
    - 起動中に stop を要求するにはプロジェクトルートの data/stop_requested.flag を作成。

- Monitoring の起動
  - コマンド:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照するため）。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で exit(1)。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / Research API（ライブラリ的に呼び出す）
  - AI ニューススコア:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - api_key が None の場合は OPENAI_API_KEY を参照します。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - これらは DuckDB 接続と日付を受け取り、ファクターを返します。

- ログ設定
  - 各スクリプトは共通の logging 設定を行います（kabusys.utils.logging_setup.setup_logging）。
  - デフォルトログディレクトリ: logs/
  - 環境変数 LOG_DIR で変更可。

---

## 停止・フェイルセーフの仕組み

- stop_requested.flag
  - run_execution / run_monitoring のループを外部から安全に停止するためのファイル（data/stop_requested.flag）。
  - ファイルが存在すると監視ループ / エンジンは順次停止します。

- kill.flag（Kill Switch）
  - RiskMonitor 等が深刻なリスク（ドローダウン超過等）を検知すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にすることが推奨されます（自動クリアは危険）。

---

## 主要ディレクトリ構成

（src 配下のパッケージ構成。実際のルートはプロジェクトの layout に依存します。）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — （発注ログ監視 / 省略されているが存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各モニタまとめ
  - execution/  — 発注エンジン関連（BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py — ログ初期化
    - process_priority.py — プロセス優先度 / CPU affinity 設定

注: 上記は主要なファイルの抜粋です。実装全体は src/kabusys 以下に展開されています。

---

## ヒント / 運用注意点

- 本番環境（KABUSYS_ENV=live）では設定内容（LINE 絡み・KILL_FLAG_CLEAR_ON_START 等）を慎重に扱ってください。
- .env は決して Git にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- OpenAI API を使う機能はトークン要・API コストが発生します。呼び出し回数・バッチサイズに注意してください。
- DuckDB / SQLite のファイルパスは環境変数で変更可能。バックアップと排他制御（同時アクセス）を運用で考慮してください。
- run_monitoring は監視専用で常に本番の monitoring DB を参照するよう設計されています（意図的）。

---

この README はコードベースの主要な使い方と運用上の注意をまとめたものです。さらに詳しい仕様やアルゴリズム設計（ポートフォリオ構築、ストラテジー仕様、ExecutionEngine の内部）は各モジュールの docstring / コメントを参照してください。

何か追加したい項目やドキュメントの出力形式（より詳細な運用手順、サンプル .env、デプロイ手順等）があれば教えてください。