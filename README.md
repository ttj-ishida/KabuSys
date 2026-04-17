KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルな日本株自動売買フレームワーク「KabuSys」のコア実装です。  
注文実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ、AI を使ったニュース評価などのコンポーネントを含みます。以下はコードベース（src/kabusys）に基づく README です。

要点（サマリ）
--------------
- 本番 / ペーパー（ペーパートレード）を切替可能な ExecutionEngine（KABUSYS_ENV）
- 監視用プロセス（System / Trade / Risk Monitor）と Kill Switch による安全停止機構
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクターキャップ等）
- リサーチ機能（モメンタム / ボラティリティ / バリュー等のファクター計算、IC 等）
- AI モジュール（OpenAI を使ったニュースセンチメント・市場レジーム判定）
- ペーパートレード用検証レポート生成ツール

機能一覧
--------
- 環境設定ウィザード（.env 作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
  - 必須 env の未設定や config/*.yaml の存在をチェック（PyYAML が無い場合は YAML チェックをスキップ）
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite (data/paper_trading.db) に記録して本番 DB と分離
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用して監視ログを書き込む
- MonitoringEngine（System / Trade / Risk Monitor を束ねる）:
  - プロセス生存確認、データ鮮度、滞留注文、約定価格異常、ドローダウン・ポジション上限監視
  - KillSwitch による停止フラグ（data/kill.flag）作成
  - AlertManager 経由で外部通知（LINE トークン設定で通知可能）
- Portfolio モジュール:
  - 候補抽出（select_candidates）
  - 等重・スコア重み付け（calc_equal_weights / calc_score_weights）
  - ポジション数算出（calc_position_sizes: risk_based / equal / score）
  - セクター制約（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
- Research モジュール:
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン・IC 計算・統計サマリ（calc_forward_returns / calc_ic / factor_summary）
- AI モジュール:
  - ニュース NLP（news_nlp.score_news）: raw_news から銘柄別センチメントを OpenAI に問い合わせて ai_scores に書き込み
  - レジーム判定（regime_detector.score_regime）: ETF 1321 の MA200 とマクロニュース LLM センチメントを合成して 'bull'/'neutral'/'bear' を判定
- ツール:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python の準備
   - 推奨: Python 3.9+（お使いの環境に合わせてください）

2. 必要ライブラリをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実プロダクションでは requirements.txt / Poetry / pip-tools 等で依存管理してください。

3. プロジェクトルートに移動し .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env は絶対に git にコミットしないこと）

4. 主要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN — 必須
   - KABU_API_PASSWORD — 必須
   - KABUSYS_ENV — デフォルト: development（有効値: development, paper_trading, live）
   - OPENAI_API_KEY — AI 機能を使う場合に必須
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — paper トレード用 DB（PAPER_TRADING 時に使用、デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE — ペーパー発注時のフィルモード（instant|partial|never|reject、デフォルト instant）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

5. ディレクトリ作成（必要に応じて）
   - data/ ディレクトリ（DB・PID・フラグファイル保存先）を作る:
     - mkdir -p data

使い方（実行例）
----------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い data/paper_trading.db に記録します
  - 実行時、data/execution.pid に PID が書き出されます
  - 停止: data/stop_requested.flag を作成（run_execution は起動時とループ中にこのフラグを監視）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は常に sqlite_path（監視 DB）を使用してログを記録
  - 停止フラグ: data/stop_requested.flag を検知すると停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム的利用）
  - ニューススコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="…")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="…")
  - OPENAI_API_KEY が設定されていない場合、各関数は ValueError を出します

監視・停止フラグ（Kill Switch / Stop）
-------------------------------------
- 実行停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が監視している停止フラグ（外部から作成して停止を要求）
  - data/kill.flag — KillSwitch が作成するフラグ（重大なリスクトリガー発動時）。ExecutionEngine は kill.flag の存在を検出して停止します
- PID ファイル:
  - data/execution.pid — ExecutionEngine が自身の PID を書き込みます。SystemMonitor はこの PID を使って実行中プロセスの有無を確認します

設定関連の詳細
---------------
- 環境変数の自動ロード:
  - プロジェクトルートに .env / .env.local がある場合、自動的に読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- .env 中の特殊設定:
  - PAPER_FILL_MODE: instant|partial|never|reject
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- config/*.yaml:
  - validator は config ディレクトリの YAML ファイル群（system_config.yaml 等）をチェックしようとします。存在しない場合は警告が出ます（scripts/generate_config.py で生成可能な旨のメッセージあり）

依存関係の注意
--------------
- openai: AI 周りの機能で必要。API キーは OPENAI_API_KEY で指定
- duckdb: リサーチ／AI のデータアクセス用
- psutil: プロセス / リソース監視（priority / cpu_affinity / cpu_percent 等）
- PyYAML: validate_config で YAML を検証する場合に必要（無くてもスクリプトは動きますが YAML 検証はスキップされます）

ディレクトリ構成（主要ファイル）
-------------------------------

以下は src/kabusys 以下の主要ファイル・モジュール一覧（本 README 作成時点のコードを基にしています）。

- kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - execution/                       —（実行関連コンポーネント、OrderManager 等が存在）
    - (複数ファイル: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, ...)
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン・ポジション数監視
    - monitoring_engine.py          — 各 Monitor を束ねる
    - kill_switch.py                — Kill Switch 実装（kill.flag）
    - alert_manager.py              — アラート送信管理（LINE 等のラッパー想定）
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数算出・キャップ・丸め
    - risk_adjustment.py            — セクター制約・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI で銘柄別スコア）
    - regime_detector.py            — レジーム判定（MA200 + LLM）
    - __init__.py
  - monitoring/
    - ... (上記)
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data/                           — 実行時に使用するデータディレクトリ（DB・PID・フラグ等）

注意事項・運用上のポイント
-------------------------
- .env は決して Git にコミットしないでください（シークレットを含むため）。
- KABUSYS_ENV=live を使う場合は通知設定（LINE 等）や KILL_FLAG 設定を十分に確認してください。validate_config は live 時に追加の警告を出します。
- AI 呼び出し（OpenAI）はレート制限・エラーを考慮したリトライ実装がありますが、API キー管理・コストには注意してください。
- run_monitoring は監視用 DB（sqlite_path）に書き込みます。Monitoring は環境にかかわらず sqlite_path を使用します（ただし run_execution は paper_trading 時に別 DB を使う）。
- Process 優先度設定や CPU affinity は psutil の権限に依存します（設定に失敗した場合は警告が出ます）。

開発・拡張メモ
----------------
- Portfolio / Research / Execution の各モジュールは DB を直接叩く箇所と純粋関数群が混在しています。ユニットテストは純粋関数群を中心に書きやすい設計です。
- AI 部分は外部 API 依存のため、テストは _call_openai_api を patch/モックして行います（コメントにもその旨が記載されています）。
- DuckDB をデータ分析用ストレージとして利用しています。prices_daily / raw_financials / raw_news 等のスキーマに依存するため、データ投入スクリプトや ETL パイプラインを整備してください。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに含めてください（本コードには明示的なライセンスファイルは含まれていません）。

お問い合わせ・貢献
-----------------
- バグ報告や機能改善の提案は Issue を立ててください。Pull Request での貢献歓迎です。
- 大きな変更（API/スキーマの互換性が壊れるもの）は事前に Issue で相談してください。

以上。README の内容はコードベース（src/kabusys）に基づいて作成しています。必要であれば環境変数のテンプレートや example .env のサンプルを追記しますか？