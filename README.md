README.md

プロジェクト概要
- KabuSys は日本株向けの自動売買 / 研究プラットフォームのコードベースです。
- 機能は以下の領域に分かれます: 発注実行 (ExecutionEngine)、監視 (Monitoring)、ポートフォリオ構築、リスク管理、リサーチ（ファクター計算・特徴量解析）、AI ベースのニュースセンチメント / レジーム判定、ペーパートレードの検証ツール 等。
- ローカル環境では .env を使った設定管理、DuckDB/SQLite をデータ保存に使用します。OpenAI 等外部 API を利用する機能は API キーを環境変数で与えます。

主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番／ペーパートレードを切替え（paper_trading は MockBrokerClient を使用し、データは data/paper_trading.db に分離）
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視ループ（run_monitoring）
  - システムリソース、データ鮮度、発注状態、リスク指標を定期チェック
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止（Kill Switch）
- 監視永続化（monitoring_db）
  - SQLite に system_status / trade_logs / positions / risk_logs / dashboard を格納
  - DB スキーマは init_monitoring_db で冪等的に作成／簡易マイグレーション実施
- ポートフォリオ構築（portfolio）
  - 候補選定、等分配・スコア加重、リスクベースのポジションサイズ計算、セクター上限制御、レジーム乗数
- リサーチ（research）
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算・IC（Information Coefficient）や統計サマリ
- AI モジュール（ai）
  - ニュースを OpenAI に送り銘柄ごとにセンチメントを算出して ai_scores に格納（news_nlp）
  - マクロニュース + ETF MA を組み合わせて市場レジーム判定を行い market_regime に書き込み（regime_detector）
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）
- CLI ヘルパー
  - .env を対話式で生成・更新するウィザード（config_setup）
  - .env と config/*.yaml の検証ツール（validate_config）

セットアップ手順（ローカル）
1. リポジトリのルートをクローン／チェックアウト
2. Python 環境の準備
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化
     - 例: python -m venv .venv && source .venv/bin/activate
3. 必要パッケージをインストール
   - 主要依存（必須）
     - duckdb, psutil, openai
   - オプション
     - PyYAML（config/*.yaml の構文チェックに使用）
   - 例: pip install -r requirements.txt
     - requirements.txt が無い場合は手動で pip install duckdb psutil openai
4. ディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動作成されることが多いですが、明示的に作る場合:
     - mkdir -p data logs
5. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 自動ロード: 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local の順で自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. 設定検証（実行前推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗にする）: python -m kabusys.validate_config --strict
7. 起動（下記「使い方」を参照）

主要環境変数（概要）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（必須で妥当な値をセット）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- LOG_LEVEL / LOG_DIR / PID_FILE_PATH / KILL_FLAG_CLEAR_ON_START 等は Settings クラスで参照

使い方（起動例）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB に書き込みます
  - ExecutionEngine は data/stop_requested.flag（および data/execution.pid）を監視して停止します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアできますが、本番（live）では 0 を推奨
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）
- .env の作成／更新（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict フラグで警告もエラー扱い
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI スコアリング／レジーム判定（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が設定されている必要あり（api_key を引数で渡すことも可能）
  - AI 呼び出しはリトライ・フェイルセーフロジックを備え、失敗時はスコアを保守的に扱います

停止・Kill Switch の仕組み
- KillSwitch はデータディレクトリに kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込み、ExecutionEngine に外部停止シグナルを送ります
- Monitoring 側でリスクやドローダウンなどの条件を満たすと kill.flag を作成し、必要に応じてアラート送信
- ExecutionEngine は起動前に kill.flag の有無を確認し、存在する場合は起動をスキップします。実行中は stop_requested.flag や kill.flag を検査して停止処理を行います
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を消去する動作があります（本番環境では注意）

ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を用いて統一されています
- デフォルトログディレクトリ: logs/
- 各アプリ名（execution / monitoring 等）ごとに日次ローテーションでログファイルが作成されます（例: logs/execution.log）
- LOG_LEVEL と LOG_DIR は環境変数で上書き可能

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py                  — パッケージ定義（__version__ 等）
  - config.py                    — Settings クラス（環境変数 / .env の読み込みロジック）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
  - execution/                   — 発注周りの実装（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル定義・操作）
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文滞留や約定異常監視（実装ファイルあり）
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — kill.flag の作成・判定
    - monitoring_engine.py       — 各 Monitor を束ねるループ
    - alert_manager.py           — アラート送信（LINE 等） ※実装に依存
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数決定・投下金額制限
    - risk_adjustment.py         — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py         — モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                — ニュースセンチメント取得・ai_scores への書き込み
    - regime_detector.py         — マクロ + MA による市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成スクリプト

補足（設計上の注意点）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト環境で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH / mock broker）。
- DuckDB は分析用途（prices_daily / raw_financials 等）に使われ、AI/リサーチ関数は DuckDB 接続を受け取って SQL を実行します。DuckDB ファイルは DUCKDB_PATH で指定します。
- 監視・マイグレーション: init_monitoring_db は既存 DB にカラムを追加する簡易マイグレーションを実施します（冪等）。

よくある起動手順（推奨順）
1. 仮想環境を作成して依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定チェック
4. python -m kabusys.run_execution を起動（もしくはデーモン化 / systemd 等で管理）
5. python -m kabusys.run_monitoring を別プロセスで起動して常時監視

問題の切り分け
- ログを確認: logs/<app_name>.log に詳細情報
- 設定検証で警告やエラーが出た場合は .env の値やパス（data/ ディレクトリの存在）を確認
- AI 機能の実行失敗は OPENAI_API_KEY の未設定やネットワーク、API クォータ（429）等をチェック

ライセンス・バージョン
- パッケージバージョンは kabusys.__version__（現在 0.1.0）
- ライセンス情報はリポジトリルートの LICENSE ファイル等を参照してください（本 README には含みません）

以上。運用時は KABUSYS_ENV の値と kill/stop フラグの扱いに特に注意してください。