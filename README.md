KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のミニマル実装です。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine：発注・リスク管理・注文履歴の管理（実口座 / ペーパートレード対応）
- Monitoring：システム状態・注文状態・リスクをポーリングしてログ・アラートを生成
- Portfolio モジュール：銘柄選定・重み付け・ポジションサイズ計算
- Research モジュール：ファクター計算・特徴量解析
- AI モジュール：ニュースの LLM によるセンチメント評価（OpenAI）
- CLI ツール：.env ウィザード、設定検証、ペーパートレード検証レポート など

主な機能
--------
- Execution
  - 実口座（kabuステーション）とペーパートレード（MockBroker）を切替可能
  - 発注履歴の永続化（SQLite）
  - リスク管理（ポジション上限、投下資金制限、ドローダウン検出）
- Monitoring
  - CPU/メモリ/Disk/プロセス生存監視
  - 注文の滞留検出、約定異常検出
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - ログ永続化（SQLite）、ダッシュボード更新
- Portfolio
  - 候補選定（スコア順）、等配分/スコア加重、リスクベースの株数決定
  - セクターキャップ、レジーム乗数適用
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン計算・IC 計算・ファクター統計サマリー
- AI
  - ニュース記事を OpenAI に送って銘柄別センチメントを ai_scores に保存
  - マクロニュースを使った市場レジーム判定（bull/neutral/bear）
- ツール
  - 環境設定ウィザード（.env 生成）
  - 設定検証（必須環境変数・YAML ファイル等）
  - Paper Trading 検証レポート生成 CLI

必要条件
--------
- Python 3.9+（型アノテーションで | を使用しているため 3.10 推奨）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（config YAML 検証を行う場合）
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワークアクセス：kabuステーション（実運用時）、OpenAI（AI 機能利用時）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   （AI 機能や YAML 検証を使わない場合は openai / PyYAML は必須ではありません）

3. データディレクトリ作成（任意）
   - mkdir -p data logs

4. .env を作成（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成

主要な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 実行時の専用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能利用時）
  - LOG_LEVEL（DEBUG/INFO/...）
  - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）

設定検証
--------
.env や config/*.yaml の基本的な不備をチェックできます。
- 実行:
  - python -m kabusys.validate_config
  - 警告も失敗扱いにするには --strict を指定

使い方（実行例）
----------------

1. ExecutionEngine を起動
- 本番（実際に発注）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード（MockBroker、専用 DB に記録）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを変更可能

停止シグナル:
- data/stop_requested.flag が存在すると run_execution は起動しないか停止を試みます。
- Monitoring の KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（ExecutionEngine はこの kill.flag を参照して停止処理を行います）。

2. Monitoring（ポーリングループ）を起動
- デフォルト 60 秒間隔でポーリング:
  - python -m kabusys.run_monitoring
- 間隔を環境変数で上書き:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

Monitoring は実行環境にかかわらず（KABUSYS_ENV に依らず）production 用 sqlite_path を使用して監視ログを記録します。

3. Paper Trading 検証レポート生成
- データのある paper_trading DB を指定してレポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db の順で解決

4. AI 機能の利用（ニューススコアリング / レジーム判定）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定した上で、アプリケーションから該当関数を呼び出します。
  - 例（スクリプト内で）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key=None の場合は環境変数を使用

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（30 日分保持）
- ログディレクトリは環境変数 LOG_DIR で変更可能

開発メモ / 運用上の注意
---------------------
- .env は秘匿情報が含まれるため決して Git へコミットしないこと
- KABUSYS_ENV=live 設定時は設定内容（LINE トークン、kill フラグ設定など）を十分に確認すること
- paper_trading は実 DB と完全分離するよう設計されています（paper_sqlite_path を使用）
- OpenAI を使う機能は API 呼び出しや解析に費用が発生するため、本番で利用する際は慎重に制御してください
- psutil によるプロセス優先度設定は OS に依存し、一部環境で権限が必要になる場合があります

ディレクトリ構成
----------------
（リポジトリの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - data/                    — データファイル（例: monitoring.db, paper_trading.db）
  - logs/                    — ログファイル（出力時に自動作成）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — ExecutionEngine と発注関連（BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

補足ドキュメント
----------------
- PortfolioConstruction.md / StrategyModel.md 等の設計文書に基づいて実装されています（リポジトリに存在する場合は参照してください）。
- データスキーマや DuckDB のテーブル名（prices_daily / raw_financials / raw_news / ai_scores 等）はソース中に記載のクエリを参照してください。

問い合わせ / 貢献
-----------------
バグ報告・改善提案・プルリクエストはリポジトリの Issue/PR を通じてお願いします。README に書かれていない実装上の詳細説明が必要であれば、該当機能を指定して問い合わせてください。