KabuSys — README
===============

概要
----
KabuSys は日本株自動売買のためのモジュール群です。戦略用のファクター計算 / ポートフォリオ構築、実行エンジン（注文送信・リコンシリエーション・リスク管理）、監視機能（システム状態・注文滞留・ドローダウン監視）、およびニュース NLP / レジーム判定などを含みます。  
コードは純粋関数的な部分（ポートフォリオ構築など）と、DB / ブローカー / 外部 API と連携する実行部分に分かれており、テスト可能性と本番運用の安全性（冪等処理・フェイルセーフ）を重視した設計です。

主な機能
---------
- ポートフォリオ構築
  - 候補選別 (select_candidates)
  - 等重配分 / スコア加重配分 (calc_equal_weights, calc_score_weights)
  - ポジションサイズ計算（リスクベース等）(calc_position_sizes)
  - セクターキャップ適用、レジーム乗数 (apply_sector_cap, calc_regime_multiplier)
- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター計算 (duckdb を利用)
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）連携
  - ニュースセンチメントのスコア化 (news_nlp.score_news)
  - マクロニュース + ETF MA200 を使った市場レジーム判定 (regime_detector.score_regime)
- 実行系（Execution）
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時リコンシリエーション（OrderSent の突合せ、ポジション差分検出）
  - BrokerClientFactory による本番 / ペーパーの分離（KABUSYS_ENV=paper_trading 時は MockBrokerClient）
- 監視（Monitoring）
  - SystemMonitor：CPU/Memory/Disk、プロセス PID、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・保有上限監視、kill.flag 書き込みによる Execution 停止
  - AlertManager：LINE への一方向通知（クールダウン管理付き）
  - MonitoringEngine：上記を束ねたポーリングループ
  - Streamlit による監視ダッシュボード（streamlit run で起動）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ
----------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb, psutil, requests, streamlit, openai
   - pip install -r requirements.txt があればこれを使用。なければ手動で:
     - pip install duckdb psutil requests streamlit openai

3. 環境変数 / .env
   - プロジェクトルートの .env（もしくは .env.local）を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（デフォルト値を含む）:
     - KABUSYS_ENV: deployment 環境 ("development" | "paper_trading" | "live") — デフォルト: development
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp, regime_detector）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用（空なら通知は送信されません）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の fill 動作（instant | partial | never | reject）デフォルト: instant
     - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60（整数、1以上）
     - LOG_LEVEL: ログレベル（"DEBUG","INFO",...）デフォルト: INFO
     - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（"1"で有効）

   - 最小の .env 例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development

使い方
------
- 監視（MonitoringEngine を単独で起動）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）。
    - 監視は monitoring 用の sqlite_path（Settings.sqlite_path）を用い、環境にかかわらず本番 path を使用します（intentional）。
    - プロセス優先度を high に設定し、SystemMonitor / TradeMonitor / RiskMonitor のチェックを繰り返します。

- 実行エンジン（ExecutionEngine）起動
  - コマンド:
    - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、BrokerClientFactory は MockBrokerClient を返し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH or data/paper_trading.db）を使用します。本番 DB と完全分離されます。
    - 実行開始時に PID ファイルを書き、kill.flag による外部停止に対応します。
    - 設定は Settings クラス（環境変数ベース）で管理。

- Streamlit ダッシュボード（監視 UI）
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - read-only モードで監視 SQLite を開き、Overview / Positions / Orders / System タブを表示します。
    - MonitoringEngine が定期的にデータを書き込んでいることが必要です。

- Paper Trading 検証レポート
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db で DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
  - 説明:
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等を集計し、簡易 PASS/FAIL を返します。

重要な実装ノート（運用上のポイント）
---------------------------------
- Settings._find_project_root は .git または pyproject.toml を検出してルートを決定するため、CWD に依存せず .env を自動ロードします。
- MonitoringDB.init_monitoring_db はテーブルとマイグレーション（カラム追加）を冪等に行います。多くの起動スクリプトで初期化が呼ばれます。
- MONITOR_POLL_INTERVAL が 0 や負数の場合はデフォルト（60秒）にフォールバックします（time.sleep の例外回避）。
- AI（OpenAI）呼び出しはリトライ、JSON 検証、結果クリッピング（±1.0）など冗長なチェックが入っており、API エラー時は安全なフォールバック（スコア無しや 0.0）で継続します。
- KillSwitch はリスク監視の閾値超過時に flag ファイルを書き、ExecutionEngine は起動時にこのファイルを見て停止します（kill_flag_clear_on_start により起動時にクリア可能）。
- process priority / cpu affinity は psutil を使ってプラットフォーム差分を吸収します。権限不足や未対応 OS の場合は警告を出しスキップします。
- Paper trading では本番 DB と分離され、PAPER_FILL_MODE によりモックの約定挙動を調整できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                 — パッケージ定義（__version__ 等）
    config.py                   — Settings（.env / 環境変数読み込み）
    utils/
      process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
    portfolio/
      portfolio_builder.py      — 候補選定・重み計算（等重・スコア重み）
      risk_adjustment.py        — セクター上限・レジーム乗数
      position_sizing.py        — 株数算出ロジック（単元丸め・集計キャップ）
    research/
      factor_research.py        — Momentum / Volatility / Value 等のファクター計算
      feature_exploration.py    — 将来リターン・IC・統計
    ai/
      news_nlp.py               — ニュースセンチメント（OpenAI）
      regime_detector.py        — レジーム判定（MA200 + マクロセンチメント）
    execution/
      order_manager.py          — OrderManager（送信・状態遷移）
      reconciler.py             — 起動時リコンシリエーション
      ...                       — （Broker API/Factory, repositories など多数）
    monitoring/
      monitoring_db.py          — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py         — システム状態・データ鮮度監視
      trade_monitor.py          — 注文滞留・約定異常監視
      risk_monitor.py           — ドローダウン・ポジション上限監視
      kill_switch.py            — kill.flag 制御
      alert_manager.py          — LINE 通知
      monitoring_engine.py      — 各 Monitor を束ねる実行エンジン
      streamlit_dashboard.py    — Streamlit ダッシュボード
    tools/
      paper_verification_report.py — Paper Trading 用検証レポート
    run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
    run_execution.py            — ExecutionEngine 起動スクリプト
    ...                         — その他モジュール

追加のヒント / トラブルシューティング
---------------------------------------
- DB ファイルが見つからないエラー:
  - monitoring 用や paper_trading 用 SQLite ファイルは初回起動時に作成されますが、DuckDB や prices_daily テーブルなどは事前に準備しておく必要があります。research / ai モジュールは DuckDB 上のテーブル（prices_daily / raw_financials / raw_news 等）を参照します。
- OpenAI API 呼び出しが失敗する場合:
  - OPENAI_API_KEY を確認し、レート制限時は自動リトライが働きますが、長時間失敗する場合はログに警告が出ます。fail-safe によりスコアは 0 またはスキップされます。
- ログ・デバッグ:
  - Settings.log_level 環境変数でログレベルを調整できます。開発時は DEBUG にすると内部処理の詳細が分かります。
- kill.flag の管理:
  - 実行中の強制停止は kill.flag を作成して行う（監視が検出したリスクで自動作成）。手動でクリアする場合は指定パスのファイルを削除してください。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していれば自動でクリアします。

ライセンス / 貢献
-----------------
本リポジトリのライセンスやコントリビュート規約がある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

最後に
------
この README はコードベースの主要機能と運用方法をまとめたものです。各モジュールの docstring（ソース内コメント）にも詳細な設計ノート・利用上の注意が含まれているため、実装を修正したり運用する際はそれらを参照してください。必要であれば、運用手順（systemd / supervisord によるデーモン化、ログローテーション、バックアップ）などの運用ドキュメントも追加できます。