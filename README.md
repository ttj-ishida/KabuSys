KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリです。
ポートフォリオ構築、シグナル研究、実行エンジン、監視、AI 補助モジュール等が含まれます。

主な特徴
-------
- ポートフォリオ構築（候補選定・重みづけ・ポジション決定）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 実行・システム監視（リスク監視、Kill Switch）
- DuckDB / SQLite を用いたデータ処理・永続化
- ニュース NLP（OpenAI を用いたセンチメント評価）と市場レジーム判定
- Research ツール（ファクター計算・IC 計算・特徴量探索）
- 開発支援ツール：対話式 .env ウィザード、設定検証、ペーパートレード検証レポート

必須外部ライブラリ（代表）
-------------------------
- python (推奨: 3.10+)
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
（実際には requirements.txt を用意の上 pip install を推奨します）

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストールします。
   - 例（リポジトリに requirements がある場合）:
     - pip install -r requirements.txt
   - ない場合は最低限 duckdb, psutil, openai をインストールしてください:
     - pip install duckdb psutil openai

3. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定例（.env のキー）
     - KABUSYS_ENV (development|paper_trading|live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール利用時）
     - LOG_LEVEL（DEBUG/INFO/...）

4. 設定の検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も FAIL 扱いになります。

主な使い方
--------

- 実行エンジン（ExecutionEngine）
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB とは分離。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中に data/stop_requested.flag を作成するとエンジンに停止要求が伝わります。
    - 実行時に PID ファイル（data/execution.pid など）を作成します。

- 監視（SystemMonitor 単体スクリプト）
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動:
    - 監視ループはデフォルト 60 秒間隔でポーリングします（環境変数 MONITOR_POLL_INTERVAL で上書き可）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します。
    - 監視停止は data/stop_requested.flag を作成することで行えます。

- ペーパートレード検証レポート
  - 生成:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - --from YYYY-MM-DD --to YYYY-MM-DD
    - DB 指定:
      - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が設定されていればそれが優先されます）

- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news と regime_detector.score_regime を提供
  - OpenAI API を利用するため OPENAI_API_KEY が必要
  - どちらも外部 API 呼び出しのエラーに対してフェイルセーフ（失敗時はスキップやデフォルト値で継続）する設計

注意事項・運用上のポイント
------------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を探索し、.env（→未設定キーのみ）および .env.local（→上書きあり）を自動読み込みします。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Kill Switch / stop フラグ:
  - KillSwitch は監視結果（ドローダウン・ポジション上限等）に従って data/kill.flag を書き込みます。ExecutionEngine は監視の kill.flag を検出して停止できます。
  - 手動停止用の stop フラグ: data/stop_requested.flag（run_* スクリプトはこれを見て起動/ループ停止を行います）。
- ログ:
  - デフォルトでは logs/<app_name>.log に日次ローテーションで出力されます（設定失敗時はコンソールのみ）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と簡単なスキーマ追加（マイグレーション）を行います。既存カラムがない場合は ALTER TABLE で追加します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの要約パスです（src/kabusys を想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・スケール/丸めロジック
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py      — マクロ + ETF MA を合成して市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化レイヤ（system_status 等）
    - system_monitor.py       — システム稼働・データ鮮度監視
    - trade_monitor.py        — （注文の滞留/約定異常監視：実装参照）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — フラグファイルによる停止シグナル
    - monitoring_engine.py    — 各モニタのまとめ実行ロジック
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

簡単なコマンド一覧
------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

さらに読むべきファイル
--------------------
- 各モジュールの docstring と関数コメントに設計方針、引数、戻り値、例外処理方針が詳細に記載されています。実装や挙動を変更する際は該当モジュールの docstring を参照してください。

サポート / 開発メモ
------------------
- 本リポジトリは各機能がモジュール化されています。ユニットテストやモック差し替えが容易にできる設計を心がけてあります（例: OpenAI 呼び出しは _call_openai_api をパッチしてテスト可能）。
- 本番運用時は KABUSYS_ENV=live に設定する前に validate_config のチェックを入念に行ってください（LINE 通知設定や Kill Switch の挙動等に注意）。

問題報告・プルリクエスト歓迎です。README に含めてほしい追加情報や導入手順の詳細が必要なら教えてください。