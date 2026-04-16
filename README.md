README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディング・フレームワークです。
主に以下の機能群を持ち、発注エンジン（ExecutionEngine）、監視・アラート機能（Monitoring）、
ファクター・リサーチ、ポートフォリオ構築、LLM を使ったニュース NLP 等が含まれます。

主な特徴
--------
- 発注エンジン（ExecutionEngine）
  - ブローカー抽象化に基づく発注管理、リコンシリエーション、自動復旧
  - Paper Trading モード（本番 DB と分離された SQLite に記録）
- 監視（Monitoring）
  - システム状態 (CPU/Memory/Disk)、データ鮮度、注文滞留・約定異常、ドローダウン監視
  - LINE へのプッシュ通知、kill flag によるエンジン停止
  - Streamlit ダッシュボードでの可視化
- リサーチ（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC 計算、統計サマリー
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、セクター上限適用、ポジションサイズ算出（単元株丸め・キャップ適用）
- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースと ETF MA200 乖離を合成した市場レジーム判定

動作前提 / 依存
---------------
- Python 3.10+
- SQLite（標準ライブラリ）
- 必要な外部ライブラリ（一例）:
  - duckdb, psutil, requests, streamlit, openai
- （推奨）プロジェクトルートに data/ ディレクトリを用意

インストール例
--------------
1. リポジトリをクローン／取得
   - git clone … （省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 依存パッケージをインストール
   - requirements.txt がない場合は必要なパッケージを個別にインストールしてください:
     - pip install duckdb psutil requests streamlit openai

4. （任意）開発環境としてインストール
   - pip install -e .

5. data ディレクトリ作成
   - mkdir -p data

環境変数（主なもの）
--------------------
Settings クラスで管理されている主な環境変数（.env に記載して自動読み込みが可能）:

- KABUSYS_ENV: 起動モード
  - 値: development | paper_trading | live
  - paper_trading の場合、発注は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH へ記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら送信せずログのみ）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の Fill モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視関連設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env の自動ロード
- プロジェクトルートを .git または pyproject.toml から検出し、
  .env と .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効）。

基本的な使い方
--------------

1) ExecutionEngine 起動（発注エンジン）
- コマンド例:
  - PYTHONPATH=src python -m kabusys.run_execution
  - または、プロジェクトをインストール後: python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 起動前に data/stop_requested.flag が存在すると起動せず終了
  - 実行中は data/execution.pid に PID を書き、停止時に削除または stop flag により停止

2) Monitoring 起動（ポーリング監視）
- コマンド例:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は Settings.env にかかわらず本番の sqlite_path（SQLITE_PATH）を使用してログを永続化
  - data/stop_requested.flag を検出するとループを抜けて終了
  - 監視内容: system_status（CPU/Memory/Disk、プロセス生存）、trade_logs、risk_logs、dashboard 更新 など

3) Streamlit ダッシュボード（監視の可視化）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - Read-only モードで監視 DB を開き、Overview / Positions / Orders / System を表示

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ (P95) 等を集計して PASS/FAIL 判定を表示

5) AI 関連（ニュース NLP / レジーム判定）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
- これらは DuckDB 接続を受け取り DB 内の raw_news / prices_daily 等を参照して処理します。
- OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用

停止とフラグ
------------
- stop_requested.flag:
  - run_monitoring / run_execution は実行ループ内で data/stop_requested.flag を確認します。
  - このファイルを作成すると、プロセスは次のポーリングで安全に終了します。

- kill.flag:
  - KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト: data/kill.flag）に理由を書き込んで ExecutionEngine の停止を要求します。
  - ExecutionEngine 側は起動時に kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）を持っています。

設定と挙動（補足）
-----------------
- Paper Trading 分離:
  - KABUSYS_ENV=paper_trading の場合、発注は本番 DB を汚さないよう PAPER_TRADING_SQLITE_PATH に記録されます。
- process priority:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限がない場合は警告を出してスキップされます。
- DuckDB / prices_daily:
  - リサーチ・AI モジュールは DuckDB 内の prices_daily / raw_financials / raw_news 等を参照する設計です。
- DB マイグレーション:
  - monitoring DB の初期化関数 init_monitoring_db は既存 DB に対する簡単なマイグレーション（カラム追加）を行います。

ディレクトリ構成（主要ファイル）
-----------------------------
src/
  kabusys/
    __init__.py
    config.py                # 環境変数 / 設定管理
    run_monitoring.py        # Monitoring ポーリングループ起動スクリプト
    run_execution.py         # ExecutionEngine 起動スクリプト

    execution/               # 発注エンジン関連（一部抜粋）
      order_manager.py
      reconciler.py
      order_repository.py
      execution_engine.py
      broker_factory.py
      ...

    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py
      streamlit_dashboard.py

    research/
      factor_research.py
      feature_exploration.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    ai/
      news_nlp.py
      regime_detector.py

    tools/
      paper_verification_report.py

    utils/
      process_priority.py

注意事項 / 運用上のポイント
--------------------------
- 本番環境での運用前に必ず Paper Trading モードでの挙動確認を行ってください。
- OpenAI 等外部 API 呼び出しはレート制限や料金が発生するため注意してください。
- PID / flag ファイル（data/*.pid, data/*.flag）を使ってプロセスの起動停止を制御します。自動化や監視ツールと組み合わせる際はディレクトリ権限や所有権に注意してください。
- DuckDB や SQLite ファイルはバックアップやローテーションを検討してください（サイズ増加に注意）。

補足: 使い始めのチェックリスト
-----------------------------
- [ ] Python 仮想環境を作成・有効化した
- [ ] 必要な Python パッケージをインストールした（duckdb, psutil, requests, streamlit, openai 等）
- [ ] data/ ディレクトリを作成した
- [ ] .env (.env.local) を作成して必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定した
- [ ] PAPER_TRADING_SQLITE_PATH（paper_trading モードを使う場合）や DUCKDB_PATH 等を確認した
- [ ] まずは paper_trading モードや tools.paper_verification_report でデータ確認を行った

その他
-----
- コード中の docstring やコメントに設計方針・注意点が多く書かれています。詳細な挙動やアルゴリズムは該当モジュールの docstring を参照してください。
- 問題や拡張を行う場合は config.Settings や monitoring / execution のインターフェース設計に注意して変更してください。

以上。必要であればセットアップの手順をさらに詳しく（具体的なコマンド、推奨パッケージバージョン、.env のテンプレート）記載します。