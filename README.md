# KabuSys

日本株自動売買システムの軽量実装リポジトリ。  
ポートフォリオ構築、ポジション算出、リスク制御、監視、Paper Trading 検証、ニュース NLP/レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 必要パッケージ
- セットアップ手順
- 簡単な使い方（主要スクリプト）
- 重要な環境変数
- ファイル・ディレクトリ構成

---

プロジェクト概要
- DuckDB / SQLite を用いたデータ分析・監視基盤と、発注エンジン（ExecutionEngine）の骨格を備えた日本株自動売買システムのコードベース。
- 本リポジトリは「実装の骨組み（純粋関数群・DB 操作・監視・AI インタフェース）」を中心に提供します。実際のブローカ接続や戦略ロジックは工夫して拡張する想定です。

機能一覧
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め・aggregate cap）
- 研究（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）連携
  - ニュース NLP による銘柄別センチメント（ai_scores へ書込）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（market_regime へ書込）
  - API 呼び出しは冗長性（リトライ・フォールバック）を考慮
- 実行エンジン / 発注周り
  - ExecutionEngine（起動スクリプトあり）。paper_trading 環境では MockBrokerClient を使用し DB を分離
  - 注文ログ・ポジション管理（SQLite）
  - リスクマネージャ、オーダー管理、差分整合（reconciler）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン・ポジション上限監視
  - Kill Switch（data/kill.flag）による ExecutionEngine の外部停止
  - MonitoringEngine: 各 Monitor を統合したポーリングループ
  - 監視ログの永続化（SQLite 用ユーティリティ monitoring_db）
- ユーティリティ
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 向け検証レポート生成スクリプト
  - ログ設定ユーティリティ（コンソール + 日次ローテーション）

前提条件 / 必要パッケージ
（実行する機能に応じて必要パッケージは増減します）

必須（一般的に推奨）
- Python 3.9+
- duckdb
- psutil

AI 機能を使う場合
- openai

YAML 検証（validate_config 内の YAML パースを有効にする場合）
- PyYAML

インストール例（仮想環境を使う）
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

（requirements.txt は本リポジトリに含まれていないため、上記を参考にしてください）

セットアップ手順（初期）
1. リポジトリをクローン／取得する
2. 仮想環境作成・依存ライブラリのインストール（上記参照）
3. data / logs ディレクトリを作成（多くのスクリプトが存在を期待）
   - mkdir -p data logs
4. 環境変数の準備
   - 対話式で .env を作成: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example がある場合はそれを参考に）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants API（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUSYS_ENV : 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading を指定すると発注は MockBrokerClient へ記録（SQLITE は data/paper_trading.db）
- OPENAI_API_KEY : OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL : ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、run_monitoring で利用。デフォルト 60）
- PAPER_FILL_MODE : paper_trading 時の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動削除するか（0/1）

使い方（主要スクリプトの実行例）
- 環境を読み込んだうえで起動スクリプトを直接実行できます（パッケージを PYTHONPATH に含めるか、src 配下で実行してください）。

1) .env の対話式作成
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- python -m kabusys.validate_config --strict

3) 監視ループ（Monitoring）
- 簡易起動（デフォルト間隔 60 秒、MONITOR_POLL_INTERVAL で上書き可）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止方法:
  - data/stop_requested.flag を作成すると run_monitoring は安全停止します
  - 実行中に Ctrl+C（KeyboardInterrupt）でも停止します

4) 実行エンジン（Execution）
- 本番/開発/ペーパートレード判定は KABUSYS_ENV に依存:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ExecutionEngine は data/execution.pid を生成（設定で変更可）
- 停止シグナル:
  - data/stop_requested.flag を置くとエンジンを停止します
  - 外部の Kill Switch（data/kill.flag）が書き込まれると発注機能を止める設計です

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

6) AI 関連（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定し、各モジュールのパブリック関数を呼ぶ:
  - kabusys.ai.score_news(conn, target_date, api_key=None) など
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 実行は DuckDB 接続を用意して行います（DuckDB に raw_news / prices_daily 等のテーブルが必要）。

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト logs ディレクトリ）。
- 起動時に kabusys.utils.logging_setup.setup_logging(app_name="execution" 等) を呼び出して初期化します。

kill / stop フラグ
- data/kill.flag : Kill Switch が ExecutionEngine に対して停止命令を出す用途（KillSwitch が書込）
  - ExecutionEngine はこのファイルを検知して適切に停止するよう設計されています
- data/stop_requested.flag : run_monitoring / run_execution の外部停止用フラグ（起動ループはこれを見て終了）

ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数読み込み・Settings クラス
    - config_setup.py           # .env 作成ウィザード CLI
    - validate_config.py        # 設定検証 CLI
    - run_monitoring.py         # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - portfolio/
      - portfolio_builder.py    # 候補選定・重み計算
      - position_sizing.py      # 株数算出ロジック
      - risk_adjustment.py      # セクター上限・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py      # momentum/volatility/value ファクター
      - feature_exploration.py  # 将来リターン / IC / 統計
      - __init__.py
    - ai/
      - news_nlp.py             # ニュース NLP -> ai_scores 書込
      - regime_detector.py      # レジーム判定
      - __init__.py
    - monitoring/
      - monitoring_db.py        # SQLite 監視用 DB 層
      - system_monitor.py       # システム状態監視
      - risk_monitor.py         # ドローダウン等の監視
      - trade_monitor.py        # （存在している想定の）注文監視ロジック
      - kill_switch.py          # kill.flag 書込ユーティリティ
      - monitoring_engine.py    # 各モニタを束ねるエンジン
    - execution/
      - (ExecutionEngine 関連モジュール: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など)
    - monitoring/
      - (上に記載済)
    - utils/
      - logging_setup.py        # ログ設定ユーティリティ
      - process_priority.py     # プロセス優先度設定ユーティリティ
    - tools/
      - paper_verification_report.py  # Paper Trading レポート生成
    - data/                      # 実行時生成想定: SQLite / DuckDB / flag / pid 等

設計上の注意点
- データベース（monitoring DB 等）はデフォルトで data/ 配下のファイルを使用します。運用時は環境変数でパスを明示してください。
- AI（OpenAI）呼び出しはネットワーク障害やレート制限を考慮してリトライ・フォールバックを実装していますが、API キーの管理と呼び出しコストに注意してください。
- KABUSYS_ENV=live の場合は本番発注が行われます。実稼働前に validate_config によるチェックと入念な確認を行ってください。
- run_monitoring は MONITOR_POLL_INTERVAL によってポーリング間隔を変更できます（0 以下・無効値はデフォルト 60 秒にフォールバックします）。

トラブルシューティング
- ログファイルが作成されない: logs ディレクトリに書き込み権があるか確認。setup_logging は書き込み失敗時にコンソールのみ出力します。
- SQLite / DuckDB のパスに問題がある: validate_config がパス関連の警告を出します。必要であれば事前にディレクトリを作成してください。
- OpenAI の呼び出しで JSON パースエラーが出る場合: LLM 応答のフォーマットが期待と異なるため、API レスポンスや SYSTEM_PROMPT を見直してください（既定では JSON mode と厳密パースの両方に対応する工夫があります）。

ライセンス・貢献
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（本 README には含めていません）。

---

簡単な開始手順のサンプル
1. 仮想環境作成・依存インストール
   - python -m venv .venv && source .venv/bin/activate
   - pip install duckdb psutil openai PyYAML
2. .env 作成
   - python -m kabusys.config_setup
3. 設定検証
   - python -m kabusys.validate_config
4. 監視起動（バックグラウンドで動かす場合は systemd / Supervisor 等を利用）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
5. 実行エンジン（ペーパートレード）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

以上。README の補足・改善点や、特定モジュール（例: ExecutionEngine の内部挙動・ブローカー接続方法）について詳細ドキュメントが必要であれば、必要箇所を指定していただければ追加します。