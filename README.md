# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（プロトタイプ）。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI を利用）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 日次・リアルタイムのシグナル生成・発注（ExecutionEngine）
- システム稼働・発注状態の監視（Monitoring）
- ペーパートレード用の分離された DB と検証ツール
- ポートフォリオ構築（候補選定・重み・株数計算・リスク調整）
- ファクター計算・特徴量探索（DuckDB を利用した分析）
- ニュースの LLM（OpenAI）によるセンチメント評価・市場レジーム判定
- 環境設定ウィザード (.env) と設定検証 CLI
- ログ設定・プロセス優先度ユーティリティ等のユーティリティ

設計上のポイント:
- DuckDB を分析用 DB として利用、SQLite を監視・発注ログ用に利用
- Paper trading（KABUSYS_ENV=paper_trading）時は実口座と完全に分離された DB / Mock ブローカーを使用
- AI 系処理は OpenAI API（例: gpt-4o-mini）と連携（API キーが必要）
- 自動ロードされる .env の仕組み（プロジェクトルートの .env / .env.local）

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine の起動スクリプト（src/kabusys/run_execution.py）
  - 本番 / ペーパートレードの分離（PAPER_TRADING 用 DB）
  - ブローカーファクトリ・注文管理・リスク管理・再整合（reconciler）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの永続化（monitoring_db.py）
  - Kill Switch（条件により execution を停止する flag 書き込み）
  - run_monitoring スクリプト（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL（環境変数でポーリング間隔変更、デフォルト 60 秒）

- ポートフォリオ（portfolio）
  - 候補選定、等重・スコア重み計算（portfolio_builder）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（position_sizing）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC（Information Coefficient）等の分析ユーティリティ

- AI（ai）
  - ニュース NLP（news_nlp）：raw_news を LLM に送って銘柄別スコアを書込
  - レジーム判定（regime_detector）：ETF の MA とマクロ記事の LLM スコアを合成

- ツール
  - 環境設定ウィザード（config_setup.py）で .env を対話的作成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

- ユーティリティ
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - .env 自動読み込みロジック（config.py）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備し仮想環境を作成・有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 必要なパッケージをインストールします（最低限）:

   pip install duckdb psutil openai

   - 開発用途で YAML の検証をしたい場合: pip install PyYAML
   - 実際の requirements.txt はリポジトリにないため、上記パッケージをプロジェクトの用途に応じて追加してください。

3. プロジェクトルートに移動し、初期ディレクトリを作成しておくと便利です（実行時に自動作成される場合もあります）:

   mkdir -p data logs

4. .env を作成します（2通り）:

   - 対話式に生成（推奨）:

     python -m kabusys.config_setup

     対話ウィザードは .env を作成・更新し、必須項目（J-Quants トークンや kabu API パスワード等）を促します。
     .env は絶対にバージョン管理にコミットしないでください。

   - 手動で作成: .env.example（存在する場合）を参照して環境変数を設定

5. 設定を検証:

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い

6. （AI 機能を使う場合）OPENAI_API_KEY を設定してください（.env に記載可）。

注意:
- 自動 .env 読み込みはデフォルトで有効です。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## 環境変数（代表的なもの）

必須（最低限実行に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

重要な任意設定（デフォルト値あり）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO 等
- OPENAI_API_KEY: OpenAI を使う機能に必要
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

その他:
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）

（完全な一覧は src/kabusys/config.py、config_setup.py を参照してください）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）

  python -m kabusys.config_setup
  # --env-file オプションでファイルパス指定可

- 設定検証

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動

  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL (秒) — デフォルト 60 秒
  - 停止: プロジェクトルート data/stop_requested.flag を作成するとループが終了します

- 実行エンジン（ExecutionEngine）起動

  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中は data/execution.pid に PID を書く（設定によりパス変更可）

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  - --db PATH: SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 系ユーティリティ（プログラム呼出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続を受け取りテーブルへ書き込みます。OPENAI_API_KEY が必要です（引数で渡すことも可能）。

ログ:
- logs/<app_name>.log に日次ローテートで保存（デフォルト logs/ ディレクトリ）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — 監視ループ起動スクリプト
- run_execution.py         — 実行エンジン起動スクリプト

サブモジュール:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（テーブル定義・読み書き）
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - system_monitor.py      — システム稼働・データ鮮度チェック
  - trade_monitor.py       — （発注状況監視）※詳細はコード参照
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - alert_manager.py       — （通知管理）※詳細はコード参照
- execution/
  - execution_engine.py    — ExecutionEngine（注文実行のコア）
  - broker_factory.py      — ブローカークライアント生成
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数計算・資金配分
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ログの統一設定
  - process_priority.py    — プロセス優先度 / CPU affinity
- data/ (実行時に使用 / 生成されるファイル)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/  — ログ出力先（デフォルト）

---

## 運用上の注意点

- .env は秘密情報（API キー等）を含むため Git へコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大になり得ます。validate_config の実行を強く推奨します。
- Monitoring は Settings.env にかかわらず monitoring 用の sqlite_path（デフォルト data/monitoring.db）を使用します。
- 実行エンジンは paper_trading 時に専用 DB を利用し、本番 DB と完全に分離されます。
- OpenAI を利用する機能は API 使用コストが発生します。API キー管理とレート制御に注意してください。
- プロセス優先度設定は psutil に依存します。権限不足などで設定に失敗してもプロセスは継続します（警告ログのみ）。

---

この README はリポジトリ内のコード（主要モジュール）を基に作成しています。さらに詳しい仕様・設計ノートは各モジュールの docstring やコメントを参照してください。必要であれば各機能の詳細ドキュメント（API 仕様、DB スキーマ、運用手順）を別途作成します。