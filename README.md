KabuSys — 日本株自動売買システム
================================

この README は、リポジトリ内の Python モジュール群（kabusys パッケージ）についての概要、機能、セットアップ方法、実行方法、ディレクトリ構成を日本語でまとめたものです。

簡単な紹介
----------
KabuSys は日本株の自動売買システムを構成するライブラリ／スクリプト群です。取引の実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）を用いたセンチメント分析、ペーパートレード向けの検証ツールなどを含みます。設計方針として、実運用での安全性（kill switch、監視、ログ）と、研究環境（DuckDB を用いたファクター計算・解析）の分離を重視しています。

主な機能一覧
--------------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV により本番 / ペーパートレード（MockBroker）を切り替え
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
  - PID ファイル（data/execution.pid）や停止フラグを監視
- 監視プロセス起動スクリプト（run_monitoring）
  - システム状態（CPU/メモリ/ディスク）・データ鮮度・プロセス生存などを定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化
  - kill.flag を書くことで ExecutionEngine に停止指示を出す Kill Switch を実装
- 監視永続化層（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
  - マイグレーションにより既存 DB の互換性を保つ実装
- リスク監視（risk_monitor）
  - ドローダウン／ポジション上限などを評価し、リスクログや kill.flag へ展開
- アラート管理（AlertManager は存在想定：monitoring_engine が依存）
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額・スコア加重、セクター上限適用、ポジションサイズ計算などの純粋関数群
- リサーチ（research）
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - forward returns、IC 計算、統計サマリー等
- AI/LLM 関連
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を作成
  - regime_detector: ETF（1321）MA200 とマクロニュースを使って市場レジーム判定
  - LLM 呼び出しはリトライ・バリデーション・スコアクリッピング等のフェイルセーフ実装
- ユーティリティ
  - config_setup: .env を対話式に作成/更新するウィザード
  - validate_config: .env と config/*.yaml の起動前チェック
  - tools/paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順（ローカル開発向け）
-----------------------------------
1. Python 環境
   - Python 3.9+ を推奨（使用している依存ライブラリに合わせて調整してください）。
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (macOS / Linux)
     - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - requirements.txt がある場合はそれを使う:
     - pip install -r requirements.txt
   - 主要な外部依存（最低限）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config が YAML 検証を行う場合のオプション）
   - 開発時は pip install -e . でパッケージを編集可能モードにしておくと便利です。

3. 初期ディレクトリ
   - data/ と logs/ ディレクトリを作成（多くのコードが自動作成しますが事前に用意しておくと良い）:
     - mkdir -p data logs

4. 環境変数 (.env) の準備
   - 対話式に .env を作る:
     - python -m kabusys.config_setup
   - 生成後に設定を検証:
     - python -m kabusys.validate_config
   - 自動ロード: package の config.py はプロジェクトルートの .env を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。

主要な環境変数（抜粋）
-----------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN … J-Quants API 用トークン
  - KABU_API_PASSWORD …… kabuステーション API パスワード
- 実行環境:
  - KABUSYS_ENV … development / paper_trading / live（デフォルト: development）
- DB/ログ:
  - DUCKDB_PATH … DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH … 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH … ペーパートレード専用 SQLite（paper_trading 時のみ使用、デフォルト data/paper_trading.db）
  - LOG_LEVEL … ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - LOG_DIR … ログ保存ディレクトリ（デフォルト logs/）
- ペーパートレード固有:
  - PAPER_FILL_MODE … instant / partial / never / reject（デフォルト instant）
- LLM:
  - OPENAI_API_KEY … OpenAI を使う機能（news_nlp / regime_detector）で必要
- 監視・停止関連:
  - KILL_FLAG_CLEAR_ON_START … Execution 起動時に kill.flag を自動クリアするか（"1" で有効。デフォルト "0" 推奨）
  - PID_FILE_PATH / KILL_FLAG_PATH … Settings クラスから参照可能（デフォルトは data/execution.pid, data/kill.flag）
- 監視のポーリング間隔:
  - MONITOR_POLL_INTERVAL … run_monitoring にてポーリング秒数を上書き（例: 30）

使い方（主要なコマンド）
-----------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
    - --strict を付けると警告も失敗扱い（exit(1)）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と完全分離）
    - 実行はスレッドで行われ、data/stop_requested.flag を置くと停止を検知します
    - PID ファイルを data/execution.pid に書きます

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は Monitoring DB（Settings.sqlite_path）にログを書きます（run_monitoring は環境に関係なく本番 sqlite_path を使用する点に注意）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
    - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 系（ニューススコア・レジーム判定）
  - news_nlp と regime_detector はそれぞれ関数呼び出し API（score_news / score_regime）として提供。
  - OpenAI API キー（OPENAI_API_KEY）が必要。コマンドラインラッパーは用意されていないため、スクリプトやバッチから呼び出して使用します。

停止フラグ / Kill Switch
------------------------
- run_execution と run_monitoring は data/stop_requested.flag を見て自身のループを終了します。
- KillSwitch（監視側）は条件を満たした際に data/kill.flag を書き込み、ExecutionEngine の停止を誘導します（Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアする挙動あり。production では 0 を推奨）。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging により標準化されています。
- 標準出力（stdout）と日次ローテートされるファイル（logs/<app_name>.log）へ出力します。
- ログディレクトリが作成できない場合は標準出力のみで継続します。

ディレクトリ構成（主なファイル）
--------------------------------
以下は本リポジトリ（src/kabusys 以下）に含まれる主なモジュールの一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py        (参照されるが省略)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       (参照されるが省略)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py

その他トップレベル（想定）
- config/                      — YAML 設定ファイル群（system_config.yaml 等）
- data/                        — SQLite DB、PID/flag ファイル、その他永続データ（デフォルト保存先）
- logs/                        — ログファイル（デフォルト）

設計上の注意点 / ベストプラクティス
-----------------------------------
- 本番環境（KABUSYS_ENV=live）では環境変数や .env を慎重に扱ってください。validate_config は live 時に警告を出します。
- ペーパートレードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を確認）。
- LLM（OpenAI）を使う機能は外部 API に依存するため、API キーや料金、応答の不安定性に注意してください。失敗時はフォールバック挙動が用意されていますが、実運用前に十分にテストしてください。
- ログ・監視・kill flag により安全にプロセスを停止できる仕組みがあります。運用時にはこれらを活用してください。
- config.py は自動で .env をロードしますが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを抑制できます。

追加情報 / 開発者向けヒント
---------------------------
- DuckDB を使ったデータ分析機能（research, ai）はデータスキーマ（prices_daily / raw_financials / raw_news 等）に依存します。実行前に該当データが存在するか確認してください。
- validate_config は PyYAML が無い場合は YAML 内容検証をスキップします（存在の有無は警告）。
- process_priority（高優先度設定）や CPU affinity は psutil を用いて OS 間の差分を吸収しています。権限や OS により設定に失敗する可能性がある点に注意してください（警告ログで通知されます）。

問い合わせ / 貢献
-----------------
- 本リポジトリの仕様変更やバグ修正、機能追加は Pull Request を通じて行ってください。
- 実運用での追加監視項目やアラート条件は kabusys.monitoring 以下に実装してください。

---

この README はコードベース内のドキュメンテーション文字列・コメントを基に作成しています。実際の環境依存設定や追加の外部ライブラリはプロジェクトの requirements.txt や運用ドキュメントに従ってください。必要であれば、実行例や設定テンプレート（.env.example）も追加で作成できます。