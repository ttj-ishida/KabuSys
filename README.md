KabuSys — 日本株自動売買システム
================================

以下は、与えられたコードベースに基づく README（日本語）です。プロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成などをまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なシステム群です。主な機能は次のとおりです。

- 注文実行エンジン（ExecutionEngine）：実際のブローカー/モックブローカー経由での注文処理、リスク管理、約定の再整合化。
- 監視（Monitoring）：システム状態、注文ログ、リスク指標を定期的にチェックし、Kill Switch（停止フラグ）やアラートを発行。
- ポートフォリオ構築：候補選定、配分（等金額・スコア加重）、ポジションサイズ計算、セクター制約、レジーム調整。
- 研究/リサーチ：ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量解析、IC計算。
- AI支援モジュール：ニュースを LLM（OpenAI）でスコアリングして銘柄・マクロセンチメントを算出する機能。
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証、運用用レポート生成ツール等。

主要な機能一覧
----------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパーを切替）
  - BrokerClientFactory により実ブローカー or MockBroker を選択
  - リスク管理（RiskManager）、OrderManager、Reconciler を組み合わせて実行

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine：System / Trade / Risk モニタを束ねてアラート・Kill Switch を実行
  - monitoring_db: SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
  - KillSwitch: データディレクトリへ kill.flag を書き、ExecutionEngine を停止させる仕組み
  - stop_requested.flag による手動停止（起動スクリプトで参照）

- ポートフォリオ/ポジション
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数決定、上限・利用率・lot 単位で丸め等
  - portfolio.risk_adjustment: セクター上限・レジーム乗数

- 研究（Research）
  - research.factor_research: モメンタム/バリュー/ボラティリティ等のファクター計算（DuckDB を使用）
  - research.feature_exploration: 将来リターン、IC、統計サマリ等

- AI（OpenAI 経由）
  - ai.news_nlp: ニュース記事を集約して LLM に投げ、銘柄別スコアを ai_scores に書込
  - ai.regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定、market_regime テーブルへ書込

- ツール
  - tools.paper_verification_report.py: ペーパートレード結果の検証レポート生成（PAPER_TRADING_SQLITE_PATH を参照）
  - config_setup.py: .env の対話的生成ウィザード
  - validate_config.py: 起動前設定検証 CLI

セットアップ手順
----------------
前提: Python 3.9+（コードで typing | None の使い方があるため 3.9 以上を想定）

1. リポジトリをクローン / 展開
   - プロジェクトルートに移動する（.git または pyproject.toml がある位置が自動検出されます）。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイルチェックのため任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （実際の requirements.txt があれば pip install -r requirements.txt）

4. 初期設定（.env）
   - 簡易ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - ウィザードで必要なキーを入力（下記「重要な環境変数」参照）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データ / ログディレクトリ作成（通常は起動時に自動作成されるが確認推奨）
   - data/ と logs/ への書き込み権限を確認

重要な環境変数（Settings に定義されている主なもの）
--------------------------------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 運用モード
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker + PAPER_TRADING_SQLITE_PATH を使用（本番 DB とは完全分離）
    - live: 実ブローカーを使う（慎重に）

- DB / パス関連
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）

- ロギング / その他
  - LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動 kill.flag クリアを避けるためデフォルト 0

使い方（実行例）
-----------------

- Execution Engine（注文実行）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag の存在をチェックしあれば起動を中止
    - 実行中に data/stop_requested.flag が作成されると安全に停止する
    - PID ファイルを data/execution.pid（Settings.pid_file_path で制御）に書込

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を定期ポーリングし system_status / risk_logs / trade_logs / dashboard を更新
    - デフォルトのポーリング間隔は 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 停止は data/stop_requested.flag を作るか Ctrl-C

- Kill Switch（自動停止）
  - KillSwitch は RiskMonitor 等の結果に基づき data/kill.flag を作成することで ExecutionEngine 側に停止シグナルを与える
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動削除する（危険性あり）

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール利用
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数）
  - 例（外部スクリプト等から）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key None の場合は環境変数参照

ロギング
--------
- ログはルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定
- デフォルトのログファイル: logs/<app_name>.log（app_name は "execution" / "monitoring" 等）
- ログディレクトリは環境変数 LOG_DIR、ログレベルは LOG_LEVEL で制御

停止・監視フラグ
----------------
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を参照して安全に停止
- KillSwitch は data/kill.flag を書き、ExecutionEngine 側で検出して停止する運用フローを想定

ディレクトリ構成（主要ファイル）
------------------------------
以下はコードベースの主要ファイルと簡単な説明（与えられたファイル群に基づく）：

- src/kabusys/
  - __init__.py : パッケージ定義、バージョン
  - config.py : 環境変数/.env の自動ロードと Settings クラス（各種設定の集中管理）
  - config_setup.py : .env の対話式ウィザード
  - validate_config.py : 設定検証 CLI
  - run_execution.py : ExecutionEngine 起動スクリプト
  - run_monitoring.py : SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py : 共通のロギング設定ユーティリティ
    - process_priority.py : プロセス優先度 / CPU affinity の設定ユーティリティ
  - monitoring/
    - monitoring_db.py : SQLite ベースの監視ログ永続層
    - monitoring_engine.py : 各モニタを束ねるエンジン
    - system_monitor.py : システム状態・データ鮮度監視
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag 管理
    -（trade_monitor 等の他のモジュールは省略）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算
    - position_sizing.py : 株数決定・資金配分・丸めロジック
    - risk_adjustment.py : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py : 各種ファクター計算（DuckDB 利用）
    - feature_exploration.py : 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py : ニュース -> LLM による銘柄別スコアリング
    - regime_detector.py : ETF + マクロニュース -> レジーム判定
  - monitoring/、execution/、research/ 等、さらに細かいモジュール群が存在

運用上の注意
--------------
- KABUSYS_ENV を "live" に設定する際は必須環境変数（特に KABU_API_PASSWORD や通貨/資金設定等）を十分に確認してください。validate_config の --strict モードでチェックを厳密化できます。
- 本番では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルト 0 を推奨します。
- OpenAI の呼び出しは課金対象となるため、API キーの管理と呼び出し頻度に注意してください。AI モジュールはフェイルセーフ（API 失敗時に 0.0 でフォールバック等）を実装していますが、コストに影響します。
- DuckDB / SQLite ファイルはパスを .env で分離可能です（本番とペーパーの DB を分けることを推奨）。

トラブルシューティング
--------------------
- 起動時にファイル・ディレクトリ作成エラーが出る場合は data/ logs/ ディレクトリのパーミッションを確認してください。
- psutil による優先度設定や CPU affinity は権限により失敗する場合があります（警告ログが出ますが処理継続します）。
- DuckDB/SQLite のクエリでエラーが出る場合、対象テーブルが存在するか init_monitoring_db 等の初期化手順が走っているか確認してください。

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。リポジトリに LICENSE がある場合はそちらを参照してください。）

以上が本コードベースの概要と運用に必要な基本情報です。追加で「起動シェルスクリプト例」「systemd ユニットファイル」「より詳しいデータベーススキーマ説明」などが必要であれば、用途に応じて追記します。