KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ用ライブラリ兼実行フレームワークです。
主な目的は以下です。

- データ格納とリサーチ（DuckDB を利用したファクター算出）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 発注実行エンジン（本番 / ペーパートレード切替、リスク管理）
- 監視（プロセス・データ鮮度・リスク監視）と Kill Switch
- ニュース NLP（OpenAI を利用した銘柄センチメント評価）とレジーム判定
- 開発支援ツール（環境設定ウィザード、設定検証、検証レポート生成）

特徴（機能一覧）
----------------
- 設定管理
  - .env 自動ロード（.env / .env.local、OS 環境変数優先）
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - 起動前検証 CLI（python -m kabusys.validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し paper_trading.db を使用（本番 DB と分離）
  - Monitoring のポーリングループ（run_monitoring.py）
    - 環境に依らず本番 sqlite_path を監視 DB に使用
    - ポーリング間隔を MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）
  - Kill Switch（data/kill.flag）による安全停止
  - ログは標準出力と日次ローテーションファイル（logs/）に出力

- モニタリング永続化
  - SQLite ベースの monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - RiskMonitor：ドローダウン・ポジション上限チェック／リスクログ出力
  - MonitoringEngine：複数 Monitor を束ねてアラートや Kill Switch を評価

- ポートフォリオ構築（純粋関数群）
  - 候補選定（select_candidates）
  - 等金額 / スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、等分配など）、単元株処理、aggregate cap のスケーリング
  - セクターキャップ適用、レジーム乗数

- リサーチ
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）連携
  - ニュース NLP（gpt-4o-mini 想定）で銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - リトライ、レスポンス検証、スコアクリップ等の堅牢性対策
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率、レイテンシ等の集計と PASS/FAIL 判定

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo_url>
   - ここではプロジェクトルートに src/ 以下のパッケージが配置されている想定です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: requirements.txt がない場合は上のパッケージをインストールしてください。プロジェクトで使用する追加パッケージがあれば適宜追加します。

4. ディレクトリ作成
   - data/ と logs/ を作成（多くのパスは自動的に作成されますが、事前に作っておくと安心です）
     - mkdir -p data logs

5. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 必要に応じて OPENAI_API_KEY を設定（AI 機能を使用する場合）

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（主なコマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に環境や config/*.yaml の妥当性をチェックします（PyYAML があれば YAML のパースも検証）。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって paper_trading / live / development を切り替え
  - paper_trading の場合、MockBroker が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を使用します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は本番の sqlite_path（Settings.sqlite_path）を使用してログを記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 簡易的に稼働率、注文成功率、P95 レイテンシなどを算出して PASS/FAIL を出力します。

- AI スコアリング（ライブラリ呼び出し例）
  - Python API: kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、対象日、OpenAI API キーを渡して ai_scores を更新します。
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key)

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必要）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0:しない（推奨） / 1:する）

停止フラグ / PID
----------------
- data/stop_requested.flag — run_execution / run_monitoring がこのファイルを検知するとループを終了します（手動で作成して停止させる運用）。
- data/kill.flag — Kill Switch が発動すると ExecutionEngine 側の停止シグナルとして書き込まれます。
- data/execution.pid — ExecutionEngine が PID を書き込むファイル（設定から変更可）。

ディレクトリ構成（抜粋）
-----------------------

想定されるプロジェクトの主要ファイル/ディレクトリ構成（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定取得ユーティリティ
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py                — ニュース NLP スコアリング
      - regime_detector.py         — 市場レジーム判定
      - __init__.py
    - research/
      - factor_research.py         — Momentum/Value/Volatility 等のファクター計算
      - feature_exploration.py     — 将来リターン / IC / 統計サマリー
      - __init__.py
    - portfolio/
      - portfolio_builder.py       — 候補選定・重み計算
      - position_sizing.py         — 株数決定・スケーリング
      - risk_adjustment.py         — セクターキャップ・レジーム乗数
      - __init__.py
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層（テーブル定義・読み書き）
      - system_monitor.py          — システム・データ鮮度監視
      - trade_monitor.py           — 発注・履歴監視（略）
      - risk_monitor.py            — ドローダウン等の監視
      - kill_switch.py             — kill.flag 管理
      - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - utils/
      - logging_setup.py           — ロギング初期化（console + 日次ローテーション）
      - process_priority.py        — プロセス優先度 / CPU affinity 設定
      - __init__.py
    - execution/                    — Execution 関連（Engine, OrderManager など）
    - data/                         — データパイプライン / DuckDB スキーマ定義 等（省略）

（上記はコード内の構成を要約したものです。実際のソースツリーはリポジトリ参照ください。）

開発・運用上の注意
-----------------
- .env は機密情報を含みます。絶対にリポジトリへコミットしないでください。
- KABUSYS_ENV=live の場合は本番動作になります。LINE 通知等の設定を本番用に確認してください（validate_config で一部チェックあり）。
- OpenAI API を利用する処理は API キーが必要です。API 利用はコストやレイテンシを考慮してください。
- run_execution は起動時にプロセス優先度を high に設定しようとしますが、権限によって失敗することがあります（警告ログのみ）。

拡張ポイント
-------------
- order_manager / broker_factory を実装して実際のブローカ接続を行うことができます。
- ポートフォリオ構築・シグナル生成部分は純粋関数で分離されているため、独自戦略の差し替えが容易です。
- DuckDB スキーマや分析クエリは改良して追加ファクターや特徴量を導入できます。

トラブルシューティング
---------------------
- ログは logs/<app_name>.log に日次ローテーションで保存されます。起動してもログが作成されない場合は LOG_DIR/パーミッションを確認してください。
- .env の自動ロードが不要なテスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SQLite / DuckDB のパスが存在しない親ディレクトリの場合、validate_config は警告します。起動時に自動作成されることもありますが事前に作成すると安心です。

ライセンス / 問い合わせ
---------------------
（ここにプロジェクトのライセンス・問い合わせ先を記載してください）

以上が README の簡易版です。必要であれば各コマンドの実行例（具体的な環境変数設定例や systemd / supervisor 用の起動スクリプト例）を追加します。どの部分を詳しくしたいか教えてください。