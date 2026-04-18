KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。主な機能は次のとおりです。
- 発注実行（ExecutionEngine）とペーパートレードの分離
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を用いた研究モジュール）
- ニュース NLP を用いた銘柄センチメント算出（OpenAI）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定等）
- ペーパートレード検証レポート生成ツール

設計の要点
- 環境ごとの DB 分離：paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離します。
- フェイルセーフ：LLM や外部 API エラーはフォールバックして処理継続する設計です。
- ローカル運用重視：DuckDB / SQLite をローカルファイルで利用し、外部サーバに依存しない構成です。
- フラグファイルによる停止制御（data/kill.flag / data/stop_requested.flag）を採用しています。

主な機能一覧
---------------
- 実行エンジン起動: run_execution.py（KABUSYS_ENV により本番／ペーパートレード切替）
- 監視ループ起動: run_monitoring.py（システム・注文・リスク監視・Kill Switch 評価）
- 設定ウィザード: config_setup.py（対話式で .env を作成）
- 設定検証 CLI: validate_config.py（起動前に環境変数・設定ファイルをチェック）
- ポートフォリオ構築: kabusys.portfolio（候補選定 / 重み計算 / ポジションサイズ）
- 研究モジュール: kabusys.research（ファクター計算 / forward returns / IC）
- AI モジュール: kabusys.ai（news_nlp, regime_detector）
- 監視 DB（永続化）: kabusys.monitoring.monitoring_db
- ペーパートレード検証レポート: tools/paper_verification_report.py
- 共通ユーティリティ: kabusys.utils（logging_setup, process_priority）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子等を使用）
- Git リポジトリをクローンして、プロジェクトルートに移動

1) 仮想環境の作成（推奨）
    python -m venv .venv
    source .venv/bin/activate  # Unix/macOS
    .venv\Scripts\activate     # Windows

2) 必要パッケージをインストール
（requirements.txt が無い場合の参考）
    pip install duckdb psutil openai

- オプション（設定検証で YAML を検証したい場合）
    pip install pyyaml

3) ディレクトリ作成（デフォルトファイル保存先）
    mkdir -p data logs

4) .env を作成
- 対話式ウィザードを使う:
    python -m kabusys.config_setup
  ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。
- 手動で環境変数を設定する場合は .env を作り、以下の必須キーを設定してください:
    JQUANTS_REFRESH_TOKEN
    KABU_API_PASSWORD

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB path（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境で使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- LOG_LEVEL / LOG_DIR 等（ログ設定）

注意:
- .env はセキュア情報を含むため決してリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）で KILL_FLAG_CLEAR_ON_START=1 は危険です。0 を推奨します。

使い方
-------

設定検証（起動前チェック）
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict  # 警告を失敗扱いに

監視ループの起動
- 監視プロセスを起動します（system / trade / risk を定期チェック）
    python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

発注エンジンの起動
- ExecutionEngine を起動（KABUSYS_ENV により本番／ペーパートレードが切替）
    python -m kabusys.run_execution
- 実行中の停止: data/stop_requested.flag を作成すると起動中のスクリプトが検知して終了します。

Kill Switch（自動停止）
- RiskMonitor が条件を満たすと kill.flag（デフォルト: data/kill.flag）を書き込み、ExecutionEngine に停止シグナルを送ります。
- Kill Switch をクリアするには（手動）:
    rm data/kill.flag
  またはコードの提供する API を利用して clear() を呼ぶ運用が可能です。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定している場合、自動で kill.flag をクリアする挙動を有効化できます（本番では推奨しません）。

ペーパートレード検証レポート
- ペーパートレード用 SQLite（既定: data/paper_trading.db）からレポートを生成します:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で別パスを指定できます。

AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定してください。
- ニューススコア生成（ライブラリ API）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  （api_key None の場合は環境変数 OPENAI_API_KEY を使用）
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)

ログ
- デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリ）。
- コンソール出力は stdout に行われます（cron / systemd と相性良く設計）。

ディレクトリ構成（主要ファイル）
----------------------------------
（プロジェクトの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

  - execution/                 — 発注周り（BrokerClientFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化レイヤ
    - system_monitor.py        — システム・データ鮮度監視
    - trade_monitor.py         — 注文ログ監視（滞留・約定異常等）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — Kill Switch フラグ管理
    - monitoring_engine.py     — 各 Monitor を束ねる実行エンジン
    - alert_manager.py         — アラート通知（LINE 等）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数決定ロジック
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum / volatility / value）
    - feature_exploration.py   — forward returns / IC / summary
  - ai/
    - news_nlp.py              — ニュースセンチメント算出（OpenAI 呼び出し）
    - regime_detector.py       — マクロ+ETF(ma200) による市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

運用上の注意
------------
- 本番（live）での運用時は必ず validate_config を実行して設定を確認してください。
- kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は誤操作のリスクが高いため、本番では 0 を推奨します。
- .env に含まれる機密情報（APIキー等）は厳重に管理してください。
- OpenAI 等外部 API の呼び出しはレート制限やエラー処理に備えていますが、APIキー管理とコスト監視は必須です。
- ログディレクトリ（logs/）とデータディレクトリ（data/）は適切なバックアップ/ローテーションを行ってください。

開発者向けメモ
---------------
- DB スキーマ初期化は init_monitoring_db が担います。run_monitoring/run_execution は起動時に自動で初期化します。
- DuckDB 接続は分析・研究用途で広く使われます。prices_daily, raw_financials, raw_news 等のテーブルを前提としています。
- テスト時には外部 API コール（OpenAI など）をモックすることを推奨します（コード内に差し替えポイントあり）。

ライセンス / 貢献
-----------------
- この README に記載のコードベースに関するライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING を参照してください。

問い合わせ
----------
- 実行や設定について問題があれば、リポジトリの issue または担当者にお問い合わせください。

以上。必要であれば README にサンプル .env テンプレートや systemd ユニット例、デバッグ手順（ログの見方）などの追記も作成します。どの情報を追加しますか？