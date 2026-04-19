README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を行う小規模なシステム群です。本リポジトリは次の領域を含みます:

- 実行エンジン（ExecutionEngine）: 発注ロジック、ブローカー抽象、注文管理、リスク制御
- 監視（Monitoring）: システム稼働監視、取引ログ監視、リスク監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム調整
- 研究（Research）: ファクター計算、将来リターン/IC などの統計解析
- AI 支援: ニュースの NLP によるセンチメント評価、市場レジーム判定（OpenAI を利用）
- ツール群: Paper Trading 検証レポート生成、設定ウィザード、設定検証 CLI 等

主な設計方針:
- DuckDB / SQLite を用いたローカルデータ処理
- 環境変数 / .env による設定管理（config モジュール）
- Paper Trading は本番 DB と分離（data/paper_trading.db がデフォルト）
- OpenAI 呼び出しはフェイルセーフ（失敗時はスキップまたはデフォルト値で継続）
- ルックアヘッドバイアス対策のため、日付参照は明示的な target_date を受け取る設計

機能一覧
--------
主な機能（抜粋）:

- 設定管理
  - .env の自動読み込みと config.Settings による型安全な取得
  - 対話式の .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution）
  - paper_trading モードでは MockBrokerClient を使用し DB を分離
  - リスクマネージャ、オーダーマネージャ、リコンサイラ等の組立て

- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン、ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる
  - 監視用 DB（SQLite）スキーマと簡易永続化層（monitoring_db）

- 研究 / 特徴量
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI / ニュース
  - news_nlp.score_news: OpenAI を用いたニュース記事の銘柄別センチメント計算と ai_scores への書込み
  - regime_detector.score_regime: MA200 とマクロニュースを合成した市場レジーム判定（bull/neutral/bear）

- ツール
  - paper_verification_report: ペーパートレード DB の検証レポート生成

セットアップ手順
----------------

1. ソースをチェックアウト
   - 例: git clone <repo>

2. Python 環境を準備
   - 推奨: Python 3.9+（プロジェクト要件に従う）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt が存在する場合:
     - pip install -r requirements.txt
   - 手動例（主要依存）:
     - pip install duckdb psutil openai
   - オプション:
     - PyYAML（config/*.yaml の検証を行う場合）: pip install pyyaml

4. .env を作成する
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（最低で必須環境変数を設定）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OpenAI を使う場合: OPENAI_API_KEY を環境変数で設定
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DB パス等: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（任意）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告をエラー扱いにできます

6. データディレクトリ（logs / data 等）の作成（多くは自動作成されますが手動で用意しておくと権限系トラブルを回避できます）
   - mkdir -p data logs

使い方
------

起動スクリプト
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用（monitoring は本番 DB を参照）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db にログを残します
  - 起動中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか kill.flag を監視します

停止 / Kill Switch
- KillSwitch はリスク条件（例: ドローダウン、ポジション上限）を満たした場合 data/kill.flag を作成します
- ExecutionEngine は起動時やポーリングで kill.flag / stop_requested.flag を検出すると安全に停止します
- kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）

Paper Trading レポート
- ペーパートレード DB の検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使用可能（デフォルト: data/paper_trading.db）

AI 機能
- ニュース NLP は OpenAI API キーを必要とします（OPENAI_API_KEY 環境変数または関数引数）
- score_news / score_regime は DuckDB 接続と target_date を受け取り、結果を DB に永続化します
- API レート制限・一時的な失敗は内部でリトライし、失敗しても例外を投げずフォールバックする設計です（ただし API キー未設定時は例外）

環境変数の主な一覧（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか)

ディレクトリ構成
----------------
主要なファイル/ディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py                      — パッケージ定義（__version__）
  - config.py                         — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py                     — ニュース NLP / OpenAI 呼び出しロジック
    - regime_detector.py              — 市場レジーム判定（MA200 + マクロニュース）
    - __init__.py

  - monitoring/
    - monitoring_db.py                — SQLite スキーマ初期化と永続化 API
    - system_monitor.py               — システム・プロセス・データ鮮度監視
    - risk_monitor.py                 — ドローダウン・ポジション数監視
    - trade_monitor.py                — （trade 関連監視）※（コード全体を参照）
    - kill_switch.py                  — Kill Switch 実装
    - monitoring_engine.py            — 各モニタ束ねたポーリング実行
    - alert_manager.py                — アラート通知（LINE など）※（実装参照）
  
  - execution/
    - execution_engine.py             — ExecutionEngine（セッション実行）
    - order_manager.py                 — OrderManager
    - order_repository.py              — 発注ログ永続化
    - broker_factory.py                — ブローカークライアント生成（Mock/実ブローカーの切替）
    - reconciler.py, risk_manager.py   — その他実行系コンポーネント

  - portfolio/
    - portfolio_builder.py            — 候補選定、重み計算
    - position_sizing.py              — 株数計算、集約制限（lot / cost buffer）
    - risk_adjustment.py               — セクターキャップ、レジーム乗数
    - __init__.py

  - research/
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py           — 将来リターン / IC / 統計
    - __init__.py

  - data/                              — データ読み書き用ユーティリティ群（pipeline 等）
  - tools/
    - paper_verification_report.py     — ペーパートレード検証レポート
    - __init__.py

  - utils/
    - logging_setup.py                 — 共通ログ設定ユーティリティ
    - process_priority.py              — プロセス優先度 / CPU affinity 設定
    - __init__.py

運用上の注意 / トラブルシューティング
-----------------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup 生成時にも明示されています）
- validate_config を使って起動前に設定をチェックしてください。特に本番では KABUSYS_ENV=live の設定を慎重に行ってください
- OpenAI を利用する機能は API キーが必須です。キーが未設定の場合、score_news / score_regime は ValueError を送出します
- PyYAML がインストールされていない場合、validate_config は config/*.yaml の検証をスキップします（警告）
- ログディレクトリ作成に失敗するとファイル出力が無効化され、コンソールのみの出力になります（ログ設定は警告を出します）
- Monitoring は production sqlite_path（SQLITE_PATH）を使用します。監視対象 DB と実行用 DB の分離を意図している場合はパス設定に注意してください
- Paper Trading（KABUSYS_ENV=paper_trading）は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録するため本番 DB とは分離されます

開発／拡張メモ
---------------
- DuckDB 接続を受け取り SQL と Python を組合せて処理を行うモジュール（research, ai など）は、テスト容易性のため外部状態をほとんど参照しません。target_date を明示して呼び出すことでルックアヘッドバイアスを防止しています。
- OpenAI の呼び出しは個別モジュール内のラッパー関数で行っており、テスト時に差し替え可能（unittest.mock.patch を使用）。
- 将来的拡張: lot_size を銘柄毎に持たせる、より詳細な手数料/スリッページモデルの導入、バックテスト機能の追加などを想定しています。

ライセンス / コントリビュート
------------------------------
- （ここにプロジェクトのライセンスとコントリビュート方法を記載してください）

以上。必要があれば README に記載するコマンド例や環境変数のサンプル .env 内容を追記します。どの程度の詳細を追加したいか（例: サンプル .env、起動・停止手順のスクリプト化、システム依存の注意点 など）を教えてください。