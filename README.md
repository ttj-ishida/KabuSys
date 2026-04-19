KabuSys — 日本株自動売買システム README
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。  
主な機能は取引エンジン（ExecutionEngine）、システム監視（Monitoring）、ポートフォリオ構築、ファクター／リサーチ、ニュース NLP（LLM 順評価）などで構成されています。  
設計方針として、運用／ペーパートレードを環境変数で切り替え可能にし、DuckDB/SQLite を用いた分析・監視データの永続化や、OpenAI（gpt-4o-mini）を使ったニュース評価機能を備えています。

主な特徴
-----------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（完全分離された DB）に対応
  - Broker クライアントは環境に応じて実装切替（MockBroker をサポート）
  - PID / 停止フラグ監視による安全停止
- Monitoring（監視）
  - CPU / メモリ / ディスク使用率、Execution プロセス存在、データ鮮度等を定期記録
  - RiskMonitor によるドローダウンやポジション上限監視 → Kill Switch（kill.flag）発動
  - AlertManager 経由で通知（LINE 等の設定を利用可能）
- Portfolio モジュール
  - 候補選定（スコア・ランク）、重み計算（等金額・スコア比率）
  - ポジションサイズ決定（リスクベース、単元株丸め、aggregate cap 調整）
  - セクター上限、レジームによる乗数適用
- Research / Factor 計算
  - Momentum / Volatility / Value 等のファクターを DuckDB データから計算
  - 将来リターン、IC（Spearman）など解析ユーティリティ
- AI（ニュース NLP / レジーム判定）
  - raw_news テーブルのニュースを LLM でセンチメント化し ai_scores に格納
  - マクロニュース＋ETF MA200 乖離で日次レジーム判定（bull/neutral/bear）
  - OpenAI API との堅牢なリトライ・バリデーション処理を備える
- ユーティリティ
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト

前提・依存
-----------
（本リポジトリに requirements.txt は含まれていません。実行環境に応じて必要パッケージを導入してください）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（設定ファイルの YAML 検証は任意。未インストール時は警告によりスキップされます）

セットアップ手順
----------------
1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

3. .env 作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants / kabuAPI の必須トークンや KABUSYS_ENV（development / paper_trading / live）等を設定します。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにするには --strict を付ける

5. データディレクトリ等（多くはコードが自動生成）
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時)
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて data/ および logs/ ディレクトリのアクセス権を確認

環境変数（主要なもの）
----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — AI 機能を使う場合に必要
- PAPER_FILL_MODE — paper_trading の MockBroker の fill モード。 instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60（0以下や不正値は無視されデフォルトにフォールバック）
- KILL_FLAG_CLEAR_ON_START — 本番環境で Kill Flag の自動クリアを行うか（0/1）

実行方法（主要スクリプト）
---------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 実行時: KABUSYS_ENV=paper_trading のときは MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
  - 停止: run_execution は data/stop_requested.flag の存在を監視します。停止したい場合はファイルを作成してください（例: touch data/stop_requested.flag）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

AI / レジーム判定（プログラム的利用）
-------------------------------------
- ニュース NLP スコア付け（ai.news_nlp.score_news）
  - DuckDB 接続と target_date を渡して実行（OPENAI_API_KEY 必須）
- レジーム判定（ai.regime_detector.score_regime）
  - DuckDB 接続と target_date を渡して実行（OPENAI_API_KEY 必須）
- これらは CLI ラッパーはありませんが、Python からインポートして実行できます。

停止 / Kill Switch の動作
-------------------------
- RiskMonitor がドローダウンやポジション上限アラートを検知すると、KillSwitch が data/kill.flag を書き込みます。
- ExecutionEngine は kill.flag を参照し、発動時に安全に停止できます（KillSwitch は冪等的に動作します）。
- 管理者が手動で停止させる場合は data/stop_requested.flag を作成（両スクリプトとも検知して終了します）。
- kill.flag を ExecutionEngine 起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 に設定（本番では非推奨）。

ログ
----
- ログは stdout に出力され、ファイル出力は logs/<app_name>.log に日次ローテーションで保存されます（デフォルト logs/、最大保持 30 日）。
- setup_logging() がルートロガーを統一設定するため、起動スクリプトから必ず呼ばれます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要な構成（抜粋）です：

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード機構含む）
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル初期化・読み書き）
    - system_monitor.py        — システム状態監視
    - trade_monitor.py         — 発注ログ監視（stale orders, anomaly fills 等）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書込ロジック
    - monitoring_engine.py     — 複数 Monitor を束ねて動かす
    - alert_manager.py         — （アラート送信ラッパー: LINE 等）※実装参照
  - execution/
    - execution_engine.py      — ExecutionEngine（メインロジック）
    - broker_factory.py        — BrokerClient の生成（実際の接続 or Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — prices_daily 等の取得ユーティリティ（DuckDB）
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/monitoring_db.py (上記に含む)

注意事項 / トラブルシューティング
---------------------------------
- .env は絶対に Git にコミットしないでください（config_setup は警告付きで生成します）。
- OpenAI API を利用するモジュールは API キーが必要です。OPENAI_API_KEY 環境変数で設定してください。
- psutil によるプロセス優先度設定は権限（特に nice 値の低い設定）により失敗する場合があります。失敗時は警告が出て動作は継続します。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は一部警告が出ますが、多くはコード内で自動生成されます（log ディレクトリなどは手動で権限を調整してください）。
- validate_config の YAML 検証は PyYAML に依存します。未インストールならスキップされます。

開発者向けメモ
---------------
- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を基点）にある .env / .env.local を自動で読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルにカラムがない場合の簡易マイグレーションを行います（例: latency_ms, peak_value の追加）。
- LLM のレスポンスは JSON mode を基本としていますが、フォールバックのために文字列内の最外側の JSON を抽出してパースする処理があります。

貢献・ライセンス
----------------
- この README に記載の内容はコードベースから抽出した主要な使用法・設定に関する説明です。実運用に際しては、各モジュールのドキュメントや設定ファイル（config/*.yaml）を合わせて確認してください。

必要であれば、README に具体的なコマンド・ユースケース（デプロイ・systemd サービス化・Docker 化など）を追記します。どのトピックを優先して詳述しますか？