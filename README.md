KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買／研究／監視を目的とした軽量なフレームワーク実装です。  
以下はコードベース（src/kabusys 配下）に基づく README です。

概要
----
KabuSys は以下の主要コンポーネントを含みます。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文を作成/管理します。KABUSYS_ENV によって paper_trading / live 動作を切り替え可能（paper_trading では MockBrokerClient を使用し、専用の SQLite に記録）。
- Monitoring（監視）: システム稼働状況、注文ログ、リスク指標を定期ポーリングして SQLite に永続化し、必要に応じて Kill Switch（停止フラグ）を発動します。
- Portfolio モジュール: 銘柄選定、重み計算、ポジションサイズ算出、セクター制約などの純粋関数群（DB 参照なし）。
- Research（ファクター・探索）: DuckDB を使ったファクター計算・将来リターン・IC 計算などの研究用ユーティリティ。
- AI（ニュース NLP / レジーム検出）: OpenAI（gpt-4o-mini 等）を使ってニュースのセンチメント評価や市場レジーム判定を行い、DB に書き込みます。
- CLI ツール: .env 対話ウィザード、設定検証、Paper Trading 検証レポート生成など。

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）による .env の対話式作成
- 設定検証 CLI（python -m kabusys.validate_config）で起動前チェック
- ExecutionEngine の本番／ペーパー切替（KABUSYS_ENV）
- 監視ループ（System / Trade / Risk）と Kill Switch による自動停止
- ログ設定ユーティリティ（stdout + 日次ローテートファイル）
- DuckDB ベースの研究用ファクター計算モジュール
- OpenAI を用いたニュースセンチメント評価 / レジーム判定（失敗耐性・リトライ実装）
- Paper Trading 検証レポート生成スクリプト（注文成功率・レイテンシ・稼働率等の判定）

前提・依存
-----------
推奨 Python バージョン: 3.10 以上（PEP 604 の Union 構文 を使用）  
主な Python パッケージ（コードから必須ないし推奨と判断されるもの）:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の中身検証を行いたい場合）
その他は標準ライブラリ（sqlite3, threading, logging など）。

インストール例（例示）
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージのインストール（例）:
  pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリを src の親にする:
   git clone <repo>
   cd <repo>

2. 仮想環境作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate

3. 依存ライブラリのインストール:
   pip install duckdb psutil openai PyYAML

4. 環境変数の初期設定:
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動で用意（.env.example ベース）。

   最小で必須:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（監視 DB）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LOG_LEVEL / LOG_DIR
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の fill モード）

   自動 .env ロード:
   - プロジェクトルートに .env, .env.local があると自動でロードされます。
   - OS 環境変数 > .env.local > .env の優先度。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前推奨）:
   python -m kabusys.validate_config
   --strict オプションで警告も失敗扱いにできます。

6. ディレクトリ作成（必要に応じて）:
   mkdir -p data logs

使い方
-----
- ExecutionEngine（エンジン）を起動:
  python -m kabusys.run_execution

  動作概要:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に取引ログを保存します。
  - 実行中は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag を置くか、Kill Switch（監視コンポーネントが data/kill.flag を書き込む）で行います。

- Monitoring（監視）を起動:
  python -m kabusys.run_monitoring

  オプション/環境変数:
  - MONITOR_POLL_INTERVAL（秒）で監視ポーリング間隔を上書き（デフォルト 60）。
  - 監視は Settings.sqlite_path（本番 sqlite_path）を常に使用します。
  - 監視も data/stop_requested.flag を検知すると終了します。

- 設定ウィザード:
  python -m kabusys.config_setup
  .env の初期作成・更新を対話式に行えます。

- 設定検証:
  python -m kabusys.validate_config
  --strict をつけると警告もエラー扱いになります。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 機能（Python API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    DuckDB 接続・日付を与えると raw_news を集約して OpenAI に投げ、ai_scores テーブルに書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    レジーム判定を行い market_regime テーブルに冪等書き込みします。
  注意: OpenAI API キー（引数 or OPENAI_API_KEY 環境変数）が必要です。

運用上の制御ファイル
------------------
- data/stop_requested.flag : 実行スクリプト（run_execution / run_monitoring）が存在を検知すると安全に停止します。
- data/kill.flag : KillSwitch が判定して記述することで Execution を停止させる「強制停止」フラグ。
- data/execution.pid : 実行エンジンの PID（デバッグ / 管理用）。
これらは Settings でパスを上書きできます（PID_FILE_PATH, KILL_FLAG_PATH 等）。

注意点・実装上の挙動
-------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml による検出）から行います。テスト時等に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードは本番 DB と完全分離して挙動を模擬します（専用 SQLite を使用）。
- AI 関連は外部 API に依存するため、API の失敗やレスポンス異常に対してリトライ・フェイルセーフ設計（失敗時はスキップやデフォルト値）になっています。
- ログは stdout に出力するとともに logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。LOG_DIR 環境変数で上書き可能。

主なディレクトリ構成
-------------------
（root: src/kabusys/ 以下。主要ファイルを抜粋）

- kabusys/
  - __init__.py                    — パッケージ定義（__version__ 等）
  - config.py                       — Settings クラス（環境変数読み込み・バリデーション・自動 .env ロード）
  - config_setup.py                 — .env 対話式ウィザード CLI
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring 起動スクリプト

- kabusys/execution/
  - execution_engine.py             — ExecutionEngine（発注ループ）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    — 発注・注文管理・リスク管理関連（実装の詳細は各モジュール）

- kabusys/monitoring/
  - monitoring_db.py                — SQLite 用永続化層（テーブル作成・CRUD）
  - system_monitor.py               — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py                — 注文滞留・約定異常検出（存在）
  - risk_monitor.py                 — ドローダウン / ポジション上限の監視
  - monitoring_engine.py            — 各 Monitor を束ねるエンジン
  - kill_switch.py                  — kill.flag の管理
  - alert_manager.py                — 通知（LINE 等）管理（実装想定）

- kabusys/portfolio/
  - portfolio_builder.py            — 候補選定・スコアソート
  - position_sizing.py              — 発注株数計算・単元切り捨て・スケーリング
  - risk_adjustment.py              — セクター制約・レジーム乗数

- kabusys/research/
  - factor_research.py              — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py          — 将来リターン・IC 計算・統計サマリー

- kabusys/ai/
  - news_nlp.py                     — ニュース NLP（OpenAI）による銘柄スコアリング
  - regime_detector.py              — マクロ + ETF MA による市場レジーム判定

- kabusys/tools/
  - paper_verification_report.py    — Paper Trading 検証レポート生成 CLI

- kabusys/utils/
  - logging_setup.py                — ロギング統一設定（stdout + 日次ファイル）
  - process_priority.py             — プロセス優先度 / CPU affinity 設定ユーティリティ

履歴・バージョン
----------------
パッケージバージョンは kabusys.__version__ で管理（現状: 0.1.0）。

トラブルシューティング
---------------------
- .env の読み込みに想定外の値がある場合、validate_config や Settings のプロパティで ValueError が出ます。まず python -m kabusys.validate_config を実行して警告/エラーを確認してください。
- OpenAI 関連が動作しない場合は OPENAI_API_KEY の設定とネットワーク接続を確認。API レート制限や一時エラーは自動リトライしますが、最終的にスキップされることがあります。
- ログファイルが生成されない場合は LOG_DIR の作成権限を確認してください。logging_setup はファイル作成に失敗した場合、自動的にコンソールのみ出力にフォールバックします。

ライセンス / セキュリティ
------------------------
- .env や API キーは決して Git リポジトリにコミットしないでください（config_setup でも注意書きあり）。
- 実際の運用での責任は運用者にあります。本 README はコードベースの説明を目的としており、運用上のチェック・バックアップ・監査は別途設計してください。

付録 — よく使うコマンド例
------------------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動（フォアグラウンド）:
  python -m kabusys.run_execution

- Monitoring 起動（フォアグラウンド）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要に応じて、この README をベースに運用手順書（デプロイ・監視・ロールバック手順等）を作成してください。質問や追加で README に含めたい情報があれば教えてください。