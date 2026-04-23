KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株取引の自動売買を想定した小規模なフレームワークです。  
本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注実行）とそれを補助する OrderManager / RiskManager / Reconciler
- 監視（Monitoring）サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- 開発用ユーティリティ: .env ウィザード、設定検証、Paper Trading 検証レポート生成 等

主な設計方針：
- 本番 DB と Paper Trading DB は分離（KABUSYS_ENV により切替）
- DuckDB を分析用に、SQLite を監視・履歴用に使用
- .env による設定管理（自動ロード機能あり。無効化も可能）

機能一覧
--------
- 実行（run_execution.py）
  - 実際のブローカークライアントか MockBrokerClient（ペーパートレード）を切替
  - リスク管理（ポジション上限・ドローダウン等）
  - 発注 / 注文管理 / 照合（reconciler）
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）に基づく安全停止
- 監視（run_monitoring.py + monitoring package）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック、プロセス存否チェック
  - リスク監視（ドローダウン、ポジション上限）
  - Alert 発行（AlertManager 経由）
  - Kill Switch による Execution 停止シグナル
- ポートフォリオ（portfolio package）
  - 候補選定（スコア/順位による上位抽出）
  - 等金額 / スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap）
- リサーチ（research package）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン計算・IC（Information Coefficient）算出など
- AI（ai package）
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定
  - OpenAI 呼び出しは冪等性・リトライ・バリデーションを配慮
- ツール
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10 以上（コード中での型注釈に Python 3.10 の union 型（|）を使用）
- git 等でリポジトリをクローン済み

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   必要最小パッケージ（本リポジトリで利用されているもの）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の検証を行う場合に必要）
   例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、実運用では環境に合わせてバージョン固定してください。

3. .env（環境変数）作成
   - 対話形式ウィザードで .env を作成:
       python -m kabusys.config_setup
   - 作成後、設定を検証:
       python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

4. データディレクトリ
   - デフォルトで以下のファイル/ディレクトリを使用します（必要に応じて .env で上書き）:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite 監視 DB)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - logs/ (ログファイル保存先)
   - 初回起動時に不足ディレクトリは自動作成される処理が多くありますが、権限等に注意してください。

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / オプション
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - OPENAI_API_KEY — AI モジュールを使用する場合必須
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 本番起動時の kill.flag 自動クリア（1=クリア、0=クリアしない）

使い方
------
起動スクリプト
- 実行（ExecutionEngine）を起動:
    python -m kabusys.run_execution
  挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に stop_requested.flag を作成すると安全停止します。
    - 実行中の PID は data/execution.pid に記録されます。

- 監視（Monitoring）を起動:
    python -m kabusys.run_monitoring
  挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB を参照）。
    - 停止フラグ stop_requested.flag を検知するとループを終了します。

ユーティリティ
- .env ウィザード:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

AI / リサーチ関数（プログラムから呼び出す例）
- ニュースセンチメントスコアを書き込む:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

- レジーム判定を書き込む:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

注意点・運用メモ
- Paper Trading と本番 DB は明確に分けること（設定と validate_config を活用）。
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine を停止させられるため、本番では自動クリア設定に注意（KILL_FLAG_CLEAR_ON_START）。
- OpenAI API 呼び出しは API キーと課金が必要。API のレート制限やエラーに対してリトライを行いますが、運用上の監視が必要です。
- ログは logs/<app_name>.log（日次ローテーション）と stdout に出力されます。LOG_DIR / LOG_LEVEL を .env で調整してください。

ディレクトリ構成（抜粋）
-----------------------
リポジトリ内の主要ファイル / ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py     — マクロ + ETF MA200 によるレジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 用監視 DB 層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視、該当実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 monitor を束ねるエンジン
    - alert_manager.py       — アラート通知（LINE など、実装に依存）
  - execution/               — Execution 関連（Engine / OrderManager / BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等ファクター計算
    - feature_exploration.py — 将来リターン・IC 計算 等
  - data/                    — データパイプライン・DuckDB テーブル定義等（別ファイル）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

- data/（実行時に作成されることが多い）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - kill.flag, stop_requested.flag, execution.pid

その他
-----
- 本リポジトリに含まれるモジュールは、テスト・開発・運用の観点で意図的にフェイルセーフ設計（API 失敗時のフォールバック、リトライ、部分書込みなど）を採用しています。
- 詳細な実装や追加の設定（ブローカークライアント実装、AlertManager の LINE 通知実装など）は execution / monitoring 以下の各モジュールを参照してください。
- 実運用前に必ず python -m kabusys.validate_config による確認を行ってください。

質問や補足の希望があれば、どの部分（起動手順、環境変数、特定モジュールの説明など）を詳しく書けばよいか教えてください。