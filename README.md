# KabuSys — README

このリポジトリは日本株向けの自動売買システム「KabuSys」の一部実装を含みます。  
本 README はコードベースから読み取れる機能・構成・セットアップ・実行方法を日本語でまとめたものです。

注意: 実行には外部ライブラリ（duckdb, psutil, openai など）や各種 API キーが必要です。実行前に .env を適切に設定してください。.env は絶対にリポジトリにコミットしないでください。

概要
---
KabuSys は以下の主要機能を持つ自動売買システム（モジュール群）です。

- ExecutionEngine：発注・注文管理・リスク管理・整合処理を行うエンジン（本番 / ペーパートレード切替あり）
- Monitoring：システム状態、注文滞留、ドローダウン等を監視し、Kill Switch（停止フラグ）やアラートを発行
- Portfolio construction：銘柄選定、重み計算、ポジションサイズ計算、セクター制限などのポートフォリオ構築ロジック
- Research：ファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量探索（IC 等）
- AI：ニュース記事の自然言語処理による銘柄センチメント評価、マーケットレジーム判定（OpenAI API を利用）
- Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト
- 設定管理：.env ウィザード（config_setup）、設定検証（validate_config）

主な機能一覧
---
- 環境に応じた実行モード（development / paper_trading / live）
- Paper Trading モードでは MockBroker を用い、本番 DB と分離して data/paper_trading.db に記録
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）による定期チェックとログの永続化（SQLite）
- DuckDB を用いた時系列データ（prices_daily / raw_financials / raw_news 等）を参照したファクター計算
- OpenAI（gpt-4o-mini など）を使ったニュースセンチメント集約と市場レジーム判定（LLM 呼び出しはリトライ・フェイルセーフ実装）
- Kill Switch（data/kill.flag）による外部からの安全な停止操作
- 各種ユーティリティ（プロセス優先度設定、PID / stop フラグの取り扱いなど）

セットアップ手順
---
1. Python 環境準備
   - Python 3.9+ を推奨。仮想環境（venv, pyenv-virtualenv 等）を使用してください。

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 追加で sqlite3 は標準ライブラリ、その他の依存は用途に応じて導入してください。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env をプロジェクトルートに配置（.env.example を参考に）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を .env または環境変数に設定

4. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict オプションを使用

5. データディレクトリ
   - デフォルトで data/ 配下に DuckDB / SQLite / PID / フラグファイルが置かれます。必要に応じて .env でパスを変更してください。
   - 例（デフォルト）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

使い方（実行例）
---
- 実行エンジン起動（本番 / ペーパートレードに応じて .env の KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときは paper_db に記録され、本番 DB と分離されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（環境にかかわらず）本番用の sqlite_path を使用する設計です（monitoring 用 DB）。

- 停止 / Kill
  - data/stop_requested.flag を作成すると run_* スクリプトは早期終了します（内部 stop フラグ）。
  - KillSwitch は data/kill.flag を作成して ExecutionEngine を停止する仕組みです。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ関数の利用（ライブラリとして）
  - 例: ニューススコアを生成（プログラム内で）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - 例: レジーム評価
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

環境変数（主なもの）
---
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で参照）
- PAPER_FILL_MODE — Paper Trading の約定動作（instant/partial/never/reject）

注意事項 / 実行上の小メモ
---
- .env の自動ロードはデフォルトで有効（config.py がプロジェクトルートを探索して .env, .env.local を読み込みます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する機能は API 呼び出し失敗時にフェイルセーフ（0.0 やスキップ）で継続する実装になっています。ただし API キーが未設定の場合は例外になります。
- DB スキーマのマイグレーション（monitoring_db.init_monitoring_db）は起動時に冪等に実行され、必要に応じてカラム追加（例: latency_ms, peak_value）を行います。
- プロセス優先度設定（utils.process_priority.set_process_priority）はプラットフォーム毎にフォールバック実装があり、権限不足などの際は警告でスキップします。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env auto-load）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/ai/
- news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores に書き込むロジック
- regime_detector.py — マクロニュース＋ETF MA を用いた市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py — SQLite による監視ログ層（テーブル定義・読み書き）
- system_monitor.py — システム状態 / データ鮮度チェック
- trade_monitor.py — 注文滞留・約定異常検出
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag の作成 / 検知ロジック
- monitoring_engine.py — 各 Monitor を束ねたポーリングエンジン
- alert_manager.py — （アラート送信のラッパー。実装別）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み付け（等重・スコア重み）
- position_sizing.py — 発注株数計算・リスク制限・単元丸め
- risk_adjustment.py — セクターキャップ・レジーム乗数適用
- __init__.py — API_export

src/kabusys/research/
- factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDB 利用）
- feature_exploration.py — 将来リターン計算・IC・統計サマリー
- __init__.py — エクスポート（zscore_normalize など）

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- __init__.py

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（注）実際の production 用 ExecutionEngine、OrderRepository、BrokerClient 等の実装はこの抜粋の他に存在する想定です（コード中で参照されています）。

貢献 / カスタマイズ
---
- 新しい YAML 設定ファイル（config/*.yaml）を追加・編集したら python -m kabusys.validate_config で検証してください。
- OpenAI を利用する機能のテストは、API 呼び出しラッパー（_call_openai_api）をモックすることで実施できます（コードにそのためのコメントあり）。
- .env を変更した後、実行プロセスに反映するためにプロセスの再起動が必要です。

ライセンス
---
- 本 README に示した情報はリポジトリ内のソースコードに基づく技術ドキュメントです。ライセンス情報はリポジトリルートの LICENSE 等を参照してください。

以上。必要であれば、README に掲載する具体的な .env の雛形や、よくあるトラブルシューティング（依存関係・DB 初期化・OpenAI エラー処理など）を追加できます。どの項目を詳細化したいか教えてください。