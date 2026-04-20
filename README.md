KabuSys
=======

日本株向け自動売買システムのコードベース（ライブラリ＋起動スクリプト）。  
このリポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI（ニュースセンチメント／レジーム判定）、および運用ツール群を含みます。

主な目的
- 日次の取引セッションを自動化する ExecutionEngine
- システム状態・注文・リスクを監視してアラート／Kill Switch を動かす Monitoring
- DuckDB を使ったファクター計算・研究モジュール
- OpenAI を使ったニュースセンチメント評価と市場レジーム判定（任意）
- ペーパートレード用の分離された DB と検証レポート生成ツール

主な機能一覧
- Execution
  - 実売買 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（実口座 or Mock）
  - 注文管理・リスク管理・約定整合（reconciler）
- Monitoring
  - システム資源（CPU/メモリ/ディスク）とプロセス生存の監視
  - 注文ログ / リスクログ / ダッシュボード永続化（SQLite）
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）
  - ポーリングエンジン（interval 可変、MONITOR_POLL_INTERVAL）
- Portfolio
  - 候補選定・重み計算（等配分・スコア加重）
  - セクターキャップ・レジーム乗数の適用
  - 株数決定（lot 単位丸め、リスク制限、aggregate cap）
- Research
  - DuckDB を用いたモメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン・IC 計算・統計サマリ
- AI（任意）
  - ニュース記事を OpenAI でスコアリングして ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（regime_detector）
- Tools
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提・依存
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML の検証を行う場合に便利だが必須ではない）
- SQLite（標準ライブラリで利用）
- 任意で OpenAI API キー（OPENAI_API_KEY 環境変数）

セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン＆仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

   ※プロジェクトに requirements.txt が無い場合は上のように個別インストールしてください。

3. .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定してください。
   - KABUSYS_ENV（development / paper_trading / live）を選択。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合は表示されるエラー／警告に従って修正してください。
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルト DB やログはプロジェクト配下の data/、logs/ に格納されます。
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を上書きしてください。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: "1" または "0"。本番は 0 推奨）

使い方（起動・運用）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に従います（paper_trading の場合は MockBrokerClient）。

  停止方法:
  - data/stop_requested.flag を作成すると run_execution は安全に終了します（run_execution も監視フラグを見て停止します）。
  - Kill Switch（監視が条件を検出したとき）は data/kill.flag を作成して Execution を停止させます。
  - Execution は起動時に kill.flag を自動クリアする挙動は KILL_FLAG_CLEAR_ON_START で制御します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - Monitoring は .env の KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを永続化します。
  - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可）

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - ライブラリ関数を呼んで利用します（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。
  - ネットワークや API エラーはリトライ・フォールバック動作を組み込んでいますが、API 利用量に注意してください。

ログ
- ログはデフォルトで logs/ に日次ローテーションで出力されます（kabusys.utils.logging_setup.setup_logging）。
- 各アプリ名（execution, monitoring 等）ごとに <app_name>.log が生成されます。
- ログ出力は stdout にも流れます（監督下での運用ログ収集がしやすいように設定）。

運用に関する注意
- 本番モード（KABUSYS_ENV=live）では設定ミスが大きなリスクになります。validate_config のワーニングを必ず確認してください。
- Kill Switch 周り（KILL_FLAG_CLEAR_ON_START）は本番で 1 にしないでください（危険）。
- Paper Trading は本番 DB と完全分離されるよう設計されています。環境変数を正しく設定してください。
- PID ファイル（data/execution.pid）や stop_requested.flag / kill.flag の存在を運用スクリプトで管理してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — 対話式 .env ウィザード（CLI）
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート（CLI）
  - execution/                      — 発注関連コンポーネント（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py
  - data/ (実行時に作成されることがある）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (出力先、デフォルト)

開発者向けメモ
- DuckDB 接続を稼働データベースとして使用し、research モジュールは SQL を活用して高速に集計します。
- 多くの処理は副作用を持たない純関数で実装されており、単体テストが書きやすい設計です。
- OpenAI 呼び出し部分はリトライやレスポンス検証を行い、不正レスポンスは安全に扱うように作られています。
- logging_setup と process_priority ユーティリティを起動スクリプトで統一して利用してください。

よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
- バージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報はリポジトリのルート（LICENSE 等）を参照してください（本 README には含みません）。

問題や質問
- 実行時に問題が発生した場合はログ（logs/）と validate_config の出力をまず確認してください。AI 系の問題は OPENAI_API_KEY の設定とネットワークを確認してください。

（以上）