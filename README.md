# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買・リサーチ向けの小規模フレームワークです。市場リサーチ（ファクター計算）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を用いたニュースセンチメント評価などのユーティリティを含みます。

以下はこのリポジトリの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - 実行（ExecutionEngine）
  - 監視（Monitoring）
  - ツール（Paper Trading レポート 等）
  - ライブラリとしての利用例
- ディレクトリ構成
- 重要な挙動・運用メモ

---

プロジェクト概要
- 日本株自動売買システムの構成要素（リサーチ / ポートフォリオ構築 / 発注 / 監視 / AI 支援）を含むモジュール群。
- DuckDB / SQLite によるデータ管理、OpenAI によるニュース NLP（任意）やレジーム判定機能を備えます。
- 実行スクリプトは Python モジュールとして提供され、CLI から起動できます。

機能一覧
- 環境設定ウィザード（kabusys.config_setup）: 対話式に .env を作成/更新
- 設定検証 CLI（kabusys.validate_config）: .env や config/*.yaml の基本チェック
- ExecutionEngine 起動スクリプト（kabusys.run_execution）:
  - 本番 / ペーパートレード（KABUSYS_ENV）に応じて DB / ブローカークライアントを選択
  - 停止フラグ（data/kill.flag, data/stop_requested.flag）により安全停止
- Monitoring 起動スクリプト（kabusys.run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてログ・アラート評価
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（settings.sqlite_path）へ保存（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite を参照）
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ（kabusys.portfolio）:
  - 候補選定 / 等配分・スコア配分 / ポジションサイズ計算 / セクター制約 等
- リサーチ機能（kabusys.research）:
  - モメンタム / ボラティリティ / バリューファクター計算、将来リターン、IC 計算など
- AI モジュール（kabusys.ai）:
  - news_nlp: ニュース記事を集約して OpenAI へ送り、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュースを組み合わせて市場レジームを判定
- ユーティリティ:
  - ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（kabusys.utils.process_priority）
  - 監視 DB 永続化層（kabusys.monitoring.monitoring_db）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repository-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 任意で: pip install pyyaml  (validate_config が YAML 検証を行う場合)
   - （実運用時は requirements.txt を用意している場合はそれを利用してください）
4. .env を作成
   - 対話式ウィザードを利用するのが簡単です（下記参照）

必須 / 主要な環境変数（例・デフォルト）
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUSYS_ENV : 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（paper_trading.db）パス（paper_trading 実行時に使用）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector を使う場合に必須）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（開発用） "0" or "1"

使い方

1) 環境設定ウィザード（.env 作成）
- 対話式に .env ファイルを作成できます:
  - python -m kabusys.config_setup
  - オプション: --env-file <path> で保存先を変更

2) 設定検証
- .env や config/*.yaml の存在・基本値をチェックします:
  - python -m kabusys.validate_config
  - 警告もエラー扱いにしたい場合:
    - python -m kabusys.validate_config --strict
- validate_config は必須環境変数の未設定・KABUSYS_ENV の整合性・DB パスの親ディレクトリ存在などをチェックします。
  - PyYAML がインストールされている場合は config/*.yaml のパース検証も行います。

3) ExecutionEngine を起動（リアル / ペーパー）
- 本番/ペーパーは KABUSYS_ENV に依存します。
- 起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、data/paper_trading.db を使用して本番 DB と分離します。
  - 起動時に data/stop_requested.flag（または settings.kill_flag_path による kill.flag）を検知した場合は起動を停止します。
  - 実行中に stop flag が置かれたら Engine.stop() を呼んで安全終了します。
- PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path で指定可）
- Kill Switch: KillSwitch が data/kill.flag を書くことで外部から発注エンジンを停止させることができます。

4) Monitoring を起動
- 監視ループを起動します:
  - python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
- 監視は MonitoringDB（SQLite）にログを永続化します（init_monitoring_db がテーブル作成を行います）。
- 監視スクリプトは KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 sqlite）を使用します（注意）。

5) Paper Trading 検証レポート
- ペーパートレード結果を簡易に評価するレポートを生成します:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- 出力は各種指標（稼働率 / 成功率 / レイテンシ 等）を表示し、PASS/FAIL を判定します。

6) ライブラリとしての利用（例）
- リサーチ関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - result = calc_momentum(duckdb_conn, target_date)
- AI スコアリング:
  - from kabusys.ai import score_news
  - written = score_news(duckdb_conn, target_date, api_key="sk-...")
- ポートフォリオ:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- これらの関数は DuckDB 接続や候補リスト等を受け取り、純粋関数的に結果を返す設計が多いです。

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite 永続化層
    - system_monitor.py     — システム状態 / データ鮮度監視
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - trade_monitor.py      — （実装あり）取引監視ロジック
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - alert_manager.py      — （実装あり）通知管理
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（起動スクリプトから使用）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記はコードベースから抜粋した主要ファイル。完全な一覧はリポジトリを参照してください。）

重要な運用メモ / 注意点
- Monitoring は明示的に Settings.sqlite_path（通常 data/monitoring.db）を使用します。KABUSYS_ENV が paper_trading の場合でも monitoring は本番監視 DB を参照する設計になっています。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使用して、本番 DB と分離します。
- Stop / Kill の仕組み:
  - data/stop_requested.flag: run_monitoring / run_execution のスクリプト内ループ終了確認に使用（存在すると停止処理）
  - data/kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine は起動時や稼働中にこのフラグを検知して停止するように設計されています。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアする（本番では 0 推奨）。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトで呼び出して統一的なログ管理を行います。デフォルトは logs/<app_name>.log を日次ローテーションで保存（30 日保持）。
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能。
- OpenAI 関連:
  - news_nlp / regime_detector は OpenAI API を呼び出します。テストやオフライン利用時は api_key を渡さないでください（例外が発生します）。
  - API 呼び出しはリトライやフォールバック（失敗時 0.0 など）を備えていますが、API キーと使用料に注意してください。

トラブルシュート
- DB やログディレクトリの親ディレクトリが存在しないと警告が出ます。必要に応じて手動で作成してください（設定検証で警告）。
- psutil の機能は OS に依存するため、一部の優先度設定や CPU affinity 設定が失敗する可能性があります（警告が出ますが処理は継続します）。
- DuckDB / SQLite のバージョンや executemany の挙動により空パラメータの扱いで注意が必要な箇所があります（コード中に注記あり）。

ライセンス / コントリビューション
- この README にはライセンス情報は含みません。リポジトリのルートに LICENSE ファイルがあればそちらを参照してください。
- 貢献する場合は Pull Request を送る前にコードスタイルやテストを整えてください。

---

この README はコードのコメント・仕様に基づいて作成しています。実際の運用や追加機能に合わせて .env / config/*.yaml / スクリプト起動オプションを適宜更新してください。必要であれば、README に起動例や systemd / supervisor 用のユニットファイルのテンプレートなども追加できます。