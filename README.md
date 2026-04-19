KabuSys — 日本株自動売買システム
================================

本リポジトリは、日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージ（kabusys）です。
コンポーネントは大きく分けて Execution（発注エンジン）、Monitoring（監視）、Research（ファクター計算・解析）、Portfolio（銘柄選定・ポジションサイズ算出）、AI（ニュース NLP / レジーム判定）で構成されています。

ここではプロジェクトの概要、主要機能、セットアップ方法、起動・利用方法、およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
- 目的: 日本株の自動売買を支援するためのモジュール群（発注エンジン、リスク管理、監視、ファクター計算、AIによるニュース解析など）。
- 設計方針:
  - モジュール毎に責務を分離（DB 永続化層 / ビジネスロジック / utils）。
  - Paper trading（ペーパートレード）を本番 DB と分離して安全に運用可能。
  - DuckDB を分析・リサーチ用 DB として利用、SQLite を監視・発注ログ用に利用。
  - OpenAI API を利用したニュース NLP / レジーム判定機能を持つ（API キー必須）。

主な機能一覧
-------------
- Execution（実行エンジン）
  - 実取引用ブローカー接続（kabuステーション など）とペーパートレード用 Mock ブローカーを切替可能（KABUSYS_ENV）。
  - OrderManager / RiskManager / Reconciler による発注・リスク管理・約定整合処理。
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag 等）。

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス死活、データ鮮度等の監視。
  - TradeMonitor: 発注・約定ログの整合性・滞留注文・約定異常検出（コード内に該当ロジックあり）。
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボード更新、リスクログ記録。
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる。
  - MonitoringEngine: 上記を束ねて定期ポーリング・アラート発火。

- Research（ファクター・解析）
  - ファクター計算: Momentum / Volatility / Value（DuckDB の prices_daily, raw_financials を参照）。
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等。

- Portfolio（銘柄選定・配分）
  - 候補選定（スコア順）、等分配・スコア加重配分、セクター上限適用、ポジションサイズ計算（単元丸め、リスクベース配分、投下資金制限のスケーリング）。

- AI（OpenAI 統合）
  - news_nlp: raw_news を集約して LLM に送信、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存。
  - regime_detector: ETF 200日MA とマクロニュースの LLM センチメントを合成して market_regime を判定・保存。

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）で .env を対話式作成。
  - 設定検証ツール（validate_config.py）で必須環境変数や config/*.yaml のチェック。
  - ログ設定ユーティリティ（utils/logging_setup.py）で stdout + 日次ローテートログ出力。
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）。

セットアップ手順
---------------
1. Python 環境
   - Python 3.9+ を推奨（実際の互換性はプロジェクトの要件に合わせてください）。

2. 依存パッケージ（例）
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例: pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使ってください: pip install -r requirements.txt）

3. .env の作成（環境変数設定）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードで .env を作成／更新できます。.env は絶対に Git にコミットしないでください。
   - 主要な環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB, デフォルト data/paper_trading.db)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading 用
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も異常扱いで終了コード 1 を返します。

5. DB 初期化
   - Monitoring / Execution 起動時に必要なテーブルは自動作成（init_monitoring_db）が実行されます。
   - DuckDB のテーブル（prices_daily, raw_financials など）はデータ投入が必要です（外部取り込みスクリプト等）。

使い方（実行例）
----------------

- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は sqlite_path を本番 DB として常に使用（KABUSYS_ENV に依存しない）。
  - 起動コマンド例:
    - python -m kabusys.run_monitoring
    - 補助的にバックグラウンドで実行:
      - nohup python -m kabusys.run_monitoring &

- Execution（発注エンジン）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
  - PID ファイル: data/execution.pid（停止や多重起動検知に使用）
  - 起動コマンド例:
    - python -m kabusys.run_execution
  - 停止フラグ（kill）:
    - monitoring の KillSwitch が条件を満たすと data/kill.flag が作成され、ExecutionEngine はそれを検知して停止します。
    - 手動で Kill をクリアする場合:
      - data/kill.flag を削除するか、KillSwitch.clear() を利用。
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムから利用）
  - 例: ニューススコアを生成して ai_scores に保存
    - from openai import OpenAI
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date, api_key="sk-...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="sk-...")

- ロギング
  - setup_logging を通じて stdout（コンソール）と logs/<app_name>.log（日次ローテート）に出力。
  - デフォルトログディレクトリ: logs/
  - LOG_LEVEL 環境変数でログレベルを調整。

環境変数（主要）
----------------
- KABUSYS_ENV: execution モード（development | paper_trading | live）。デフォルト development。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）。
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）。
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）。
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）。Monitoring は常にここを使用。
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）。
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）。
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。

注意事項 / 運用上のポイント
---------------------------
- .env は秘密情報を含むため絶対に Git にコミットしないでください（config_setup でも同注意書きあり）。
- Monitoring は KABUSYS_ENV に依らず sqlite_path を本番 DB として使用します。監視対象 DB を変更する場合は注意してください。
- KABUSYS_ENV=live を設定する際は、LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や Kill Switch の設定を十分確認してください（validate_config に警告あり）。
- psutil を使ったプロセス優先度設定は権限や OS に依存します。権限不足時は警告が出て処理は継続します。
- OpenAI 呼び出しは API 失敗時にリトライやフェイルセーフが組み込まれていますが、API コストやレート制限に注意してください。
- データテーブル（DuckDB の prices_daily, raw_financials など）は別途取り込みが必要です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）と役割です。

- kabusys/
  - __init__.py                     — パッケージ定義（バージョンなど）
  - config.py                        — 環境変数・設定管理（.env 自動読み込み含む）
  - config_setup.py                  — 対話式 .env 作成ウィザード
  - validate_config.py               — 起動前設定検証 CLI
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py                    — ニュース NLP（OpenAI 経由で銘柄別スコア算出）
    - regime_detector.py             — 市場レジーム判定（MA + LLM）
    - __init__.py

  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB の初期化・永続化 API
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — 発注/約定監視（滞留・異常検知）
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - kill_switch.py                 — kill.flag の作成・削除ロジック
    - alert_manager.py               — アラート送信管理（LINE 等）
    - monitoring_engine.py           — 総合監視ループ

  - execution/
    - execution_engine.py            — 実行エンジン本体（セッション制御）
    - broker_factory.py              — ブローカークライアントの生成（実／Mock 切替）
    - order_manager.py               — 発注管理
    - order_repository.py            — DB ベースの発注ログ保存
    - risk_manager.py                — 発注前リスク制限
    - reconciler.py                  — 発注結果と DB の整合性復元

  - portfolio/
    - portfolio_builder.py           — 候補選定・配分計算（純粋関数）
    - position_sizing.py             — 株数決定・スケーリング（純粋関数）
    - risk_adjustment.py             — セクターキャップ・レジーム乗数（純粋関数）
    - __init__.py

  - research/
    - factor_research.py             — モメンタム／ボラティリティ／バリュー等のファクター計算
    - feature_exploration.py         — 将来リターン／IC／統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py   — Paper Trading の検証レポート生成スクリプト
    - __init__.py

  - utils/
    - logging_setup.py               — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

付録: よく使うコマンドまとめ
----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- プログラム内で AI スコア実行（例）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, date(2026,4,11), api_key="sk-...")

最後に
------
この README はソースコードから自動的に抽出した情報に基づいて作成しています。実運用する前に必ず:
- .env の値（特に本番用の資格情報）を確認、
- validate_config によるチェックを実行、
- 小規模なテスト環境（development / paper_trading）で動作確認 を行ってください。

不明点や追加したいドキュメント（API 仕様、DB スキーマ、運用手順など）があれば教えてください。必要に応じて追補します。