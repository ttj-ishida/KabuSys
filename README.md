KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリと起動スクリプト群を含みます。  
本READMEではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

※ 本ドキュメントはソースコード（src/kabusys 以下）を参照して作成しています。

プロジェクト概要
----------------
KabuSys は日本株を対象とした自動売買・リサーチ基盤です。主な要素は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（ペーパートレードとライブ両対応）
- Monitoring：システム状態・注文・リスクを監視し、必要なら Kill Switch を発動してエンジンを停止
- Portfolio Construction：銘柄選定・重み付け・ポジションサイズ計算の純粋関数群
- Research：DuckDB 上のデータに基づくファクター計算・特徴量解析ツール
- AI モジュール：ニュースセンチメント評価（OpenAI）や市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証など

特徴一覧
--------
- 開発 / ペーパートレード / 本番（live）を切り替え可能（KABUSYS_ENV）
- ペーパートレード時は本番 DB と分離された専用 SQLite を使用
- DuckDB を使った分析用データレイク（prices_daily, raw_financials 等を想定）
- OpenAI を用いたニュースセンチメント解析（gpt-4o-mini を想定）
- 監視コンポーネント（CPU/メモリ/ディスク/プロセス/データ鮮度）とリスク監視（ドローダウン・ポジション上限）
- Kill Switch（data/kill.flag 書き込み）で実行中の ExecutionEngine を安全に停止可能
- ロギングは統一設定（コンソール + 日次ローテートファイル）で管理

前提 / 必要条件
---------------
- Python 3.10 以上（ソースは│型注釈等を使用）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証で任意）
- SQLite（標準ライブラリで利用可）
- ネットワークアクセス（kabuステーション API / OpenAI 利用時）

セットアップ手順
----------------

1. リポジトリをクローンして移動
   - git clone ... && cd <repo>

2. 仮想環境を作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを設定します。
     - 生成されるファイル: .env（プロジェクトルート）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返します。

6. ディレクトリ（data / logs）自動作成
   - 起動時に必要ディレクトリは自動作成されることが多いですが、権限などに注意してください。

主な環境変数（重要）
-------------------
（config_setup で生成される主な項目の抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- KABUSYS_ENV — execution 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を利用する場合の API キー
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant / partial / never / reject）

使い方（起動スクリプト）
-----------------------

• 設定ウィザード
- python -m kabusys.config_setup
  - .env を対話的に作成・更新します。

• 設定検証
- python -m kabusys.validate_config
  - 起動前に環境と config/*.yaml の妥当性をチェックします。

• ExecutionEngine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。

• Monitoring を起動（監視ループ）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止は data/stop_requested.flag による監視ループ検出、あるいは KeyboardInterrupt。

• Paper Trading 検証レポート（ツール）
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB は data/paper_trading.db。--db でパスを指定可能。
  - 稼働率、注文成功率、送信率、P95レイテンシ等を計算して PASS/FAIL を表示します。

• AI / Research 関数の利用
- ai.score_news(conn, target_date, api_key=...) などはライブラリ関数として利用可能（DuckDB 接続を渡す）。
  - OpenAI を使う処理は環境変数 OPENAI_API_KEY、あるいは api_key 引数でキーを指定します。
  - LLM 呼び出し部分はリトライ・フォールバック処理が組み込まれています。

ログ / PID / フラグファイル
-------------------------
- ログ: デフォルト logs/<app_name>.log（TimedRotatingFileHandler 日次ローテート、30日保持）と stdout に出力
- PID ファイル: data/execution.pid（ExecutionEngine の pid を記録）
- 停止フラグ（外部からの停止要求）: data/stop_requested.flag
- Kill Switch を発動するファイル: data/kill.flag（KillSwitch が書き込む）

実運用ヒント
-------------
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（誤って Kill Switch をクリアしないようにするため）。
- ペーパートレード中は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）にログが分離されるため、本番データと混ざりません。
- OpenAI を利用する場合はレート制限や API 失敗を考慮してログやリトライ挙動を監視してください。
- UNIX 系では systemd / Supervisor / cron 等で起動・管理する場合、既存の stdout/stderr ログと整合させることを検討してください（setup_logging は stdout を使います）。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主要ファイル・パッケージの概要（本リポジトリ内の実ファイルに基づく抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — ペーパートレード検証レポート
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py      — システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - trade_monitor.py       — （コード中で参照される想定の監視処理）
      - kill_switch.py         — kill.flag 書き込みユーティリティ
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       — （アラート配信ロジックを含む想定）
    - execution/
      - execution_engine.py    — 実行エンジン本体（EngineConfig, 実行ループ等）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py   — 候補選別・重み付け
      - position_sizing.py     — 発注株数計算・キャップ・スケールダウン
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py     — Momentum/Volatility/Value などのファクター計算（DuckDB）
      - feature_exploration.py — 将来リターン計算・IC・統計サマリ
    - utils/
      - logging_setup.py       — ログ初期化ユーティリティ
      - process_priority.py    — プロセス優先度・CPU affinity
      - __init__.py

（上記はコード抜粋に基づく一覧であり、実際のリポジトリにはさらにファイルやドキュメントが含まれる場合があります）

開発・拡張の指針
----------------
- DuckDB は分析向けに設計されており、研究/バックテスト用の多数のテーブル（prices_daily, raw_financials, raw_news 等）を前提にしています。データパイプラインで DuckDB を適切に構築してください。
- AI 呼び出し周りはフェイルセーフ設計（リトライ・フォールバック）を施していますが、APIコストとレート制限に注意してください。
- 監視は本番運用の安全弁です。監視閾値（CPU / memory / disk / dd 閾値 等）は config や環境変数で調整してください。

よくある質問（FAQ）
------------------
Q: .env を自動で読み込んでくれますか？
A: はい。config.py がプロジェクトルート（.git または pyproject.toml を基準）を検出すると自動で .env をロードします。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

Q: ペーパートレードと本番は DB が分離されていますか？
A: はい。KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視は本番の sqlite_path を参照する設計になっています。

Q: OpenAI のキーはどこに入れますか？
A: OPENAI_API_KEY 環境変数（あるいは ai 関数の api_key 引数）で指定してください。

サポート・貢献
--------------
バグ報告、改善提案、プルリクエストはリポジトリの issue / PR を通じてお願いします。変更を加える場合はユニットテスト・スタイルの一貫性・ドキュメント更新を心がけてください。

以上が本コードベースの概要と利用方法です。必要があれば用途別の具体的な起動例（systemd ユニット定義、docker-compose、CI 用スクリプト等）も作成しますのでお知らせください。