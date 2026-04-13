KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・バックテスト・監視を目的としたモジュール群です。
本リポジトリには、注文実行エンジン・監視エンジン・ファクター計算・ポートフォリオ構築・
ニュース NLP（OpenAI）連携など、実運用に向けた機能が含まれます。

主な設計方針
- 実運用と paper_trading（モックブローカー）を明確に分離
- DuckDB を用いたリサーチ向け高速集計、SQLite を監視・注文ログに使用
- 外部 API 呼び出し（OpenAI / ブローカー）はフェイルセーフ（リトライ・フォールバック）を備える
- ルックアヘッドバイアス防止（日時参照は引数に依存する実装）

機能一覧
--------
- 実行（Execution）
  - ExecutionEngine 起動用スクリプト（run_execution.py）
  - BrokerFactory による実ブローカー / MockBroker の切替（KABUSYS_ENV）
  - OrderManager / OrderRepository / Reconciler による発注管理と再接続時の同期
  - RiskManager による発注前リスクチェック（最大ポジション率・利用率等）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とログ化
  - MonitoringEngine：各モニタを束ねたポーリングループ
  - AlertManager：LINE による通知（クールダウン管理付き）
  - KillSwitch：flag ファイル (data/kill.flag) 書き込みによる ExecutionEngine 停止シグナル
  - streamlit による監視ダッシュボード（streamlit_dashboard.py）
- リサーチ / ファクター
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily/raw_financials を参照してファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算など
- ポートフォリオ構築
  - 銘柄選定（select_candidates）、重み付け（等金額・スコア加重）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）
- AI（OpenAI 連携）
  - news_nlp.score_news：ニュース記事を集約して LLM にセンチメント評価を依頼、ai_scores に書き込み
  - regime_detector.score_regime：ETF（1321）MA200乖離とマクロニュースを組み合わせてレジーム判定（market_regime テーブルへ）
  - API 呼び出しはバッチ化・リトライ・レスポンス検証を実装
- ユーティリティ
  - Settings（環境変数 / .env の自動ロード）
  - process_priority：プロセス優先度 / CPU affinity 設定
  - monitoring_db：監視用 SQLite テーブル定義および CRUD ラッパー

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（duckdb / psutil 等に依存）
   - 仮想環境を作成して有効化してください（venv / pyenv など）

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用時はブローカー SDK 等が別途必要になる場合があります。

3. ソース配置
   - この README はソースルートに置く想定です。パッケージを直接参照する場合は PYTHONPATH に src を含めるかパッケージインストールしてください。
     例: export PYTHONPATH=$(pwd)/src

4. 環境変数 / .env
   - Settings モジュールは自動でプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（一部）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他しきい値（CPU_THRESHOLD_PCT など）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager 用）

5. データディレクトリ
   - data/ フォルダに DB や pid/flag を格納することが想定されています。必要に応じて作成してください。

使い方
------

基本的な起動方法例（開発ディレクトリのルートにいる前提）

- 監視ループを起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - もしくは: python src/kabusys/run_monitoring.py
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 備考:
    - run_monitoring は Settings.env に関わらず監視用 SQLite（SQLITE_PATH）を使用します。
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil による）。権限がない場合は警告でスキップします。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - もしくは: python src/kabusys/run_execution.py
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます（本番 DB と完全分離）。
    - 起動時にプロセス優先度を "high" に設定します。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH を指定して別 DB を参照可能（PAPER_TRADING_SQLITE_PATH に優先）
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等を標準出力に出力します。

- streamlit ダッシュボードで監視を確認
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いて簡易ダッシュボードを表示します。

- AI（OpenAI）バッチ処理（プログラム的に呼び出す例）
  - ニューススコアを付与:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="sk-xxx")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,1), api_key="sk-xxx")
  - 備考: OpenAI API キーを環境変数 OPENAI_API_KEY で設定しておくことも可能。API 呼び出しはバッチ化・リトライ・レスポンス検証済みです。

運用上の注意
- Paper trading と live は DB を分離してください（PAPER_TRADING_SQLITE_PATH）。
- run_monitoring は監視ログ作成のために production SQLITE_PATH を参照します（KABUSYS_ENV に依存しません）。
- KillSwitch は data/kill.flag を書き込んで ExecutionEngine 停止を促します（ExecutionEngine 側は起動時に kill.flag をクリアする挙動が設定可能）。
- OpenAI API を使用する機能は API 料金が発生します。API キー管理とレート制御に注意してください。
- process_priority / cpu_affinity 設定は権限によっては失敗します（警告に留まります）。

ディレクトリ構成（主なファイル）
--------------------------------
src/
  kabusys/
    __init__.py                — パッケージ定義、バージョン
    config.py                  — Settings / .env 自動ロード
    run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    run_execution.py           — ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py — Paper trading 検証レポート CLI
    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py (実装ファイルがある想定)
      broker_factory.py
      broker_api.py
      ...                      — 発注・ブローカー周りの実装
    monitoring/
      monitoring_db.py         — SQLite スキーマ & MonitoringDB ラッパー
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
      __init__.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py               — ニュースセンチメント取得（OpenAI）
      regime_detector.py        — 市場レジーム判定（OpenAI）
      __init__.py
    data/                       — データパイプライン・DuckDB 関連（prices_daily 等）
    utils/
      process_priority.py       — プロセス優先度 / CPU affinity
      __init__.py

（上記は本 README に含まれる主要モジュールのみ抜粋しています）

追加のヒント・デバッグ
--------------------
- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/...）。
- .env のパースは quote / escape / inline comment を考慮した実装です。.env.example を参照して設定してください。
- MonitoringDB.init_monitoring_db は冪等で、既存 DB に対するマイグレーション（列追加）も含みます。
- DuckDB 接続は高速集計に適しています。research モジュールは DuckDB 接続を受け取り純粋関数で処理します（副作用なし）。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含みません。実プロジェクトでは LICENSE を追加してください。
- バグ報告や機能追加は issue / PR でお願いします。テストケース（unit tests）を添えていただけると助かります。

以上。運用・セットアップ中に不明点があれば、どのスクリプトをどの環境で動かそうとしているか（環境変数の現状等）を教えてください。必要に応じて具体的なコマンド例や .env のテンプレートを作成します。