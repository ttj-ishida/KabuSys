KabuSys — 日本株向け自動売買プラットフォーム
=======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。  
主な責務は次のとおりです。

- 注文の生成・送信・状態管理（ExecutionEngine）
- リコンシリエーション（再起動後の自動復旧）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- モニタリング（システム状態、注文滞留、リスク検出、LINE 通知、Streamlit ダッシュボード）
- 研究（ファクター計算、特徴量解析）
- AI モジュール（ニュースの NLP によるセンチメント付与、マーケットレジーム判定）
- ツール（Paper Trading 検証レポート生成 等）

主な設計方針:
- DuckDB / SQLite を中心としたオンプレ DB 利用
- 実運用（live）と Paper Trading を分離（paper_trading は専用 SQLite を使用）
- OpenAI（gpt-4o-mini）を用いた NLP コンポーネント（オプション）
- 自動 .env ロード（プロジェクトルートの .env / .env.local）

機能一覧
--------
- Execution
  - Broker クライアント抽象化（本番 / モック切替）
  - OrderManager による注文状態遷移管理
  - Reconciler による起動時リコンシリエーション
  - RiskManager（発注前リスクチェック, レート制限等）
- Portfolio Construction
  - 候補選定（スコア順）、等配分 / スコア配分、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数適用
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存 / データ鮮度）
  - TradeMonitor（滞留注文 / 約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止シグナル）
  - AlertManager（LINE Push によるアラート送信）
  - Streamlit ベースの監視ダッシュボード
  - Monitoring DB（SQLite）への永続化レイヤ
- Research
  - momentum / volatility / value などのファクター計算（DuckDB 上の prices_daily / raw_financials）
  - 将来リターン計算、IC（スピアマン）などの統計ツール
- AI
  - news_nlp: ニュースを集約し OpenAI で銘柄ごとのセンチメントを生成して ai_scores テーブルへ保存
  - regime_detector: ETF 200MA とマクロニュースを合成して日次レジームを算出
- Tools
  - paper_verification_report: Paper Trading 用 DB を解析して各種指標（稼働率、成功率、レイテンシ等）を表示

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>
   - 本ドキュメントは src/kabusys 以下のコードに対応します。

2. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際の requirements.txt がある場合はそれを利用してください。

4. 環境変数 / .env
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に .env / .env.local を置くと自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=<token>
     - KABU_API_PASSWORD=<password>
     - OPENAI_API_KEY=<key>  (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN=<token>（LINE 通知を使う場合）
     - LINE_USER_ID=<user id>
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60（秒、監視ループ）
     - LOG_LEVEL=INFO

5. データベース初期化
   - Monitoring / Execution の起動スクリプト（下記）で自動的に監視用テーブルを作成します（init_monitoring_db は冪等）。
   - DuckDB（prices_daily 等テーブル）は別途データ投入スクリプトを用意してください（本リポジトリに含まれていない場合があります）。

使い方（実行例）
----------------

- ExecutionEngine を起動（本番は env=live、Paper Trading は env=paper_trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を利用し、data/paper_trading.db（デフォルト）へ記録します。
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring（ポーリングループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

注意点 / 運用メモ
----------------
- Settings（kabusys.config）は自動で .env を読み込みますが、OS 環境変数が優先されます。.env.local は上書き用です。
- KABUSYS_ENV の有効値は development / paper_trading / live。値が不正だと Settings が例外を投げます。
- run_monitoring.run と run_execution.main は起動時に set_process_priority("high") を呼びます。権限がない場合は警告ログが出ますが処理は継続します。
- Paper Trading は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する AI コンポーネントは API キー必須。ネットワークエラー・レート制限は内部でリトライ処理がありますが、API が利用できない場合はフォールバック（例: macro_sentiment=0.0）する設計です。
- kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送ります（KillSwitch が作成）。
- MonitoringDB のスキーマは init_monitoring_db で管理され、軽微なマイグレーション（カラム追加）処理も含まれています。

ディレクトリ構成（抜粋）
----------------------
src/
  kabusys/
    __init__.py                -- パッケージ定義（バージョン等）
    config.py                  -- 環境変数 / 設定管理
    run_execution.py           -- ExecutionEngine 起動スクリプト
    run_monitoring.py          -- SystemMonitor ポーリング起動
    tools/
      __init__.py
      paper_verification_report.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ... (OrderRepository, broker_factory, execution_engine 等)
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    data/
      (データパイプライン用モジュールがある想定)
    utils/
      process_priority.py
      __init__.py

主要ファイルの目的（早見）
- config.py: .env 自動読み込みと Settings API を提供
- run_execution.py: ExecutionEngine を組み立てて起動（paper_trading でのモック挙動あり）
- run_monitoring.py: SystemMonitor をループで実行して監視ログを蓄積
- monitoring_db.py: monitoring 用 SQLite スキーマと永続化 API
- news_nlp.py / regime_detector.py: OpenAI API を用いた自然言語スコアリング
- portfolio/*: ポートフォリオ構築ロジック（純粋関数群）
- tools/paper_verification_report.py: Paper Trading DB の集計と PASS/FAIL 判定レポート

トラブルシューティング
---------------------
- DB ファイルが開けない:
  - パスや権限を確認。streamlit は読み取り専用 URI（?mode=ro）で接続します。
- OpenAI キー未設定:
  - AI 機能を呼ぶと ValueError が発生します。OPENAI_API_KEY を設定してください。
- set_process_priority に失敗する:
  - 権限不足や未対応 OS の場合、警告ログのみ出力してスキップされます（動作には影響しません）。
- MONITOR_POLL_INTERVAL が不正な値:
  - 1 未満や整数でない値が渡された場合、デフォルト（60 秒）にフォールバックします。

開発者向けメモ
--------------
- pure function（副作用なし）で実装されているモジュール（portfolio/*、research/*）はユニットテストが容易です。
- DuckDB 接続を引数で受ける設計のため、テスト時にメモリ上の DuckDB を使って検証できます。
- OpenAI 呼び出しはモック可能（各モジュールで _call_openai_api を分離しているため patch が容易）。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を追記してください）

以上。README の追加修正（依存関係の pin、実行例のスクリーンショットや DB 初期ロード手順など）をご希望であれば、その用途に合わせて補足します。