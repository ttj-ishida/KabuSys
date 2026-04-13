KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 注文発行 / 実行（ExecutionEngine、OrderManager、BrokerClientFactory）
- 発注リコンシリエーション（Reconciler）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine、AlertManager）
- ポートフォリオ構築（候補選定・配分・サイズ計算・セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI（ニュースセンチメント / レジーム判定：OpenAI を利用）
- 管理ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

特徴
----
- 本番 / Paper Trading を環境変数 KABUSYS_ENV で切り替え（development / paper_trading / live）
- Paper Trading 時は MockBroker を使用し、DB を分離（data/paper_trading.db）
- DuckDB を用いた高速な時系列・ファクター計算
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・レジーム判定（API リトライ・バリデーション実装）
- 監視ループとアラート：LINE Push による一方向通知、kill.flag による外部停止シグナル
- Streamlit で監視ダッシュボードを提供
- 検証用レポート生成ツール（paper_verification_report）

セットアップ
-----------

前提
- Python 3.10 以上（型表記に | を使用）
- SQLite（標準ライブラリ）およびファイルシステムへの書き込み権限

推奨手順（ローカル）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests streamlit

   ※requirements.txt がある場合は pip install -r requirements.txt を利用してください。

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定（.env をプロジェクトルートに置くと自動読み込みされます）
   自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。  
   自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な環境変数（例）
   - KABUSYS_ENV=development|paper_trading|live
   - JQUANTS_REFRESH_TOKEN=<token>         (必須: 一部機能)
   - KABU_API_PASSWORD=<password>          (必須: ブローカー連携)
   - OPENAI_API_KEY=<key>                  (AI 機能を使う場合)
   - LINE_CHANNEL_ACCESS_TOKEN=...         (監視アラート送信に必要)
   - LINE_USER_ID=...                      (LINE 通知先)
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - PAPER_FILL_MODE=instant|partial|never|reject

   例 .env（最小）
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=secret
   JQUANTS_REFRESH_TOKEN=...
   ```

5. 初回起動時に必要な DB テーブルは各起動スクリプトが自動で作成します（init_monitoring_db）。

使い方
------

コマンド（パッケージモードで実行可能）
- 監視ループを起動（SystemMonitor のポーリング）
  - 実行:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL (秒、デフォルト 60) — 1未満や不正値はデフォルトにフォールバック
  - 備考:
    - 監視は Settings に従い常に本番用 sqlite_path を参照します（KABUSYS_ENV に依存せず）。
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil による試行、権限不足時は警告で続行）。

- 実行エンジン（注文発行）を起動
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に処理を記録します（本番 DB と分離）。
    - ブローカークライアント、OrderRepository、RiskManager、Reconciler を組み立てて実行セッションを開始します。

- Streamlit ダッシュボード（監視）起動
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 読み取り専用で接続（存在しない / 開けない場合はエラーメッセージを表示）。

- Paper Trading 検証レポート生成
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH  # PAPER_TRADING_SQLITE_PATH 環境変数と置換可能
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、および PASS/FAIL 判定を標準出力に表示します。

主要な動作と運用ノート
- KABUSYS_ENV による挙動差分
  - paper_trading: ブローカーはモック、DB は paper_trading_sqlite_path（デフォルト data/paper_trading.db）
  - live: 本番運用向け（実ブローカー）
  - development: 開発用

- kill.flag
  - KillSwitch は data/kill.flag（デフォルト）を作成して ExecutionEngine に停止シグナルを送ります。  
  - ExecutionEngine 側は起動時に kill_flag_clear_on_start の設定によりフラグをクリアすることができます。

- PID ファイル
  - ExecutionEngine は PID を PID_FILE_PATH（デフォルト data/execution.pid）に書きます。SystemMonitor はこの PID を参照してプロセスの生存確認を行います。

- 監視 DB のマイグレーション
  - init_monitoring_db() は必要なテーブルとインデックスを冪等に作成し、既存スキーマにないカラム（例: peak_value, latency_ms）を追加する簡単なマイグレーション処理を行います。

- OpenAI API
  - news_nlp / regime_detector は OPENAI_API_KEY を使用します。未設定時はエラーまたはフォールバック動作（例: macro_sentiment=0）をします。API 呼び出しはリトライやレスポンス検証を実装しており、異常時はフェイルセーフでスキップします。

ディレクトリ構成（主要ファイル）
--------------------------------
（プロジェクトルートの src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み含む）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント合成）
    - __init__.py

  - monitoring/
    - monitoring_db.py         — SQLite 監視ログ層（MonitoringDB、init_monitoring_db）
    - system_monitor.py        — システム状態 / データ鮮度チェック
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・保有数上限監視
    - monitoring_engine.py     — 各 Monitor を束ねる
    - alert_manager.py         — LINE Push 通知
    - kill_switch.py           — kill.flag 書込 (Execution 停止シグナル)
    - streamlit_dashboard.py   — Streamlit ダッシュボード
    - __init__.py

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py
    - broker_factory.py
    - order_record.py
    - order_repository.py
    - (その他実装ファイル)

  - portfolio/
    - portfolio_builder.py     — 候補選定、等配分・スコア配分
    - position_sizing.py       — 発注株数決定・単元丸め・aggregate cap
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
    - __init__.py

  - research/
    - factor_research.py       — Momentum/Volatility/Value 等ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
    - __init__.py

  - data/
    - pipeline.py              — prices_daily などの取得補助（利用箇所参照）
    - stats.py                 — zscore_normalize 等（research で利用）

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
    - __init__.py

運用上の注意
------------
- ブローカー連携・実取引時は十分なテストと監視体制を構築してください。Paper Trading での検証を推奨します。
- OpenAI API を利用する機能は外部 API コストと遅延を伴います。rate limit や API キー管理に注意してください。
- process priority / cpu affinity の設定はプラットフォームごとに権限要件が異なります。psutil の警告ログが出る場合は権限を調整してください。
- DB ファイル（data/*.db）はバックアップ・アクセス権限に注意してください。

貢献・開発
----------
- テストや CI を整備してからの PR を歓迎します。
- 大きな機能追加（注文フローの変更、ブローカープロトコル拡張、UI 追加等）は設計文書（PortfolioConstruction.md, StrategyModel.md 等）に沿って行ってください。

ライセンス
----------
- 本ドキュメントではライセンス情報は省略しています。実際の利用時はプロジェクトの LICENSE を確認してください。

以上。必要であれば README にサンプル .env のテンプレート、起動例のログ出力サンプル、またはより詳細な運用手順（systemd サービス化、Docker 化等）を追加します。どの情報を追加しますか?