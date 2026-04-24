README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視フレームワークです。  
このリポジトリには以下の主要機能が含まれており、ローカル開発からペーパートレード、本番運用までを想定しています。

主な特徴
--------
- Execution エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行環境
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて paper_trading DB に記録（本番 DB と分離）
- Monitoring: システム状態、注文ログ、リスク指標をポーリングして監視・アラート・Kill Switch を制御
- Portfolio 構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出、セクター上限・レジーム乗数
- Research モジュール: DuckDB を使ったファクター計算（Momentum / Volatility / Value）や特徴量解析（IC 等）
- AI モジュール: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定
- ユーティリティ: 設定ウィザード・設定検証・ロギング設定・プロセス優先度制御 等
- ペーパートレード検証レポート生成ツール

インストールとセットアップ
-------------------------

前提
- Python 3.9+（コードは型ヒントに依存）
- 任意の仮想環境（venv, pyenv など）を推奨

1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要依存: duckdb, psutil, openai
   - 任意（YAML 検証を行う場合）: PyYAML
   例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合:
     pip install -r requirements.txt

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成・更新します（.env は Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

環境変数（主要）
----------------
主に .env に記載する想定のキー（抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI モジュールで使用）
- LOG_DIR（ログの出力先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする: 0/1）

起動・使い方
------------

主要スクリプトはモジュールとして実行します（パッケージを PYTHONPATH に含めている前提）。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 注意: Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます
  - 実行はデーモンスレッドで行われます。停止は data/stop_requested.flag を作成するか、kill.flag による停止シグナルを監視して行われます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db オプションで DB パスを指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI / Research の利用例（ライブラリ関数）
  - news スコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  - Research ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    calc_momentum(duckdb_conn, target_date)

ログと PID / フラグファイル
---------------------------
- ログ:
  - デフォルト出力先: logs/<app_name>.log（app_name は "execution" や "monitoring" 等）
  - 標準出力にもログを出します（stdout）。ログは日次ローテーション・30日保持。

- フラグ / PID:
  - data/kill.flag: KillSwitch が作成する停止フラグ（ExecutionEngine に停止指示を送る）
  - data/stop_requested.flag: run_monitoring / run_execution の手動停止フラグ（存在するとループを終了）
  - data/execution.pid: ExecutionEngine の PID（実行時に使用）

注意点 / 運用上のヒント
-----------------------
- Monitoring は常に Settings.sqlite_path（監視 DB）を使用します。Execution は KABUSYS_ENV により別 DB を使うため、本番とペーパーが分離されます。
- OpenAI を使う機能は OPENAI_API_KEY が必要です。API 呼び出しはリトライ等の保護が入っていますが、API キーの管理に注意してください。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- validate_config を実行して起動前に設定不備を検出することを推奨します（本番では --strict 推奨）。
- process_priority モジュールでプロセス優先度を"high"に設定しますが、権限不足などで設定できない場合は警告ログが出ます。

ディレクトリ構成（主なファイル）
------------------------------

src/kabusys/
  __init__.py
  config.py                 — 環境変数・設定管理（.env 自動読み込み含む）
  config_setup.py           — .env 対話式ウィザード
  validate_config.py        — 設定検証 CLI
  run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  run_execution.py          — ExecutionEngine 起動スクリプト

  ai/
    news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント集計
    regime_detector.py      — マーケットレジーム判定（ma200 + マクロニュース）

  monitoring/
    monitoring_db.py        — SQLite 監視 DB の初期化・永続化 API
    system_monitor.py       — システム状態・データ鮮度監視
    trade_monitor.py        — （注文）トレード監視（滞留・約定異常など）
    risk_monitor.py         — ドローダウン・ポジション上限監視
    kill_switch.py          — Kill Switch 制御（kill.flag）
    monitoring_engine.py    — 各 monitor を束ねたエンジン
    alert_manager.py        — （アラート管理：LINE 等へ送信）※実装参照

  execution/
    (Execution 関連コンポーネント: broker_factory, execution_engine, order_manager, risk_manager, reconciler, order_repository)

  portfolio/
    portfolio_builder.py    — 候補選定・重み算出
    position_sizing.py      — 発注株数計算（ロット丸め・リスク/上限考慮）
    risk_adjustment.py      — セクターキャップ・レジーム乗数

  research/
    factor_research.py      — Momentum/Volatility/Value の計算（DuckDB）
    feature_exploration.py  — 将来リターン・IC・統計サマリー

  tools/
    paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  utils/
    logging_setup.py        — ログ設定ユーティリティ
    process_priority.py     — プロセス優先度 / CPU affinity 設定

付録: よく使うコマンドまとめ
----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution
- ペーパートレードレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
-------------------
コードやドキュメントの改善、バグ修正はプルリクエスト歓迎です。運用中は設定・シークレット管理と kill/stop フラグの扱いに十分ご注意ください。

以上。必要であれば各モジュールの API 仕様（関数引数/戻り値）や例を追加で記載します。どの部分を詳しく書いてほしいか教えてください。