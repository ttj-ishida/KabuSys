# KabuSys — 日本株自動売買システム

簡潔な説明:
KabuSys は日本株向けの自動売買フレームワークです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード）、監視・アラート、LLM を使ったニュースセンチメント集計などの機能を備えています。本リポジトリはモジュール化されており、スクリプトから実行する運用部分と、ライブラリ的に利用できる研究／ポートフォリオ関数群を含みます。

主な特徴
- ExecutionEngine（発注エンジン）: live / paper_trading を切り替え可能（paper_trading は mock broker を使用、DB 分離）
- Monitoring: システム状態・データ鮮度・取引状況・リスクを定期ポーリングしてログ・アラート、Kill Switch を管理
- Portfolio 建設ロジック: 候補選定、等重・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出
- Research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン・IC 計算、統計サマリ
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄ごとのセンチメント）と市場レジーム判定（ETF + マクロニュースの組合せ）
- 運用ユーティリティ: .env ウィザード、設定検証、Paper Trading 検証レポート生成、ログ設定、プロセス優先度設定

動作要件（概略）
- Python 3.10+
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証にのみ必要）
- ネットワーク接続（本番で kabuAPI / J-Quants / OpenAI を使う場合）

セットアップ手順

1. リポジトリをクローン / 配布物を配置
   - ソースは `src/kabusys` 配下に配置されています。

2. Python 仮想環境作成 & 依存インストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
   - requirements.txt がない場合は上記必須パッケージを個別にインストールしてください（duckdb, psutil, openai, PyYAML など）。

3. .env の作成（推奨: 対話式ウィザード）
   - ウィザードを使って初期 .env を作成:
     python -m kabusys.config_setup
   - 生成された `.env` を編集して必要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定してください。

4. 設定検証
   - 自動検証を実行して不足点を確認:
     python -m kabusys.validate_config
   - 警告を厳密に扱う場合は `--strict` を付与します。

5. データディレクトリ / DB の準備
   - デフォルトはプロジェクトルート下の `data/`：
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (監視): `data/monitoring.db`
     - Paper Trading SQLite (ペーパートレード用): `data/paper_trading.db`
   - 必要に応じて .env の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を上書きしてください。
   - 監視 DB の初期化は起動スクリプトが自動で行います（冪等）。

基本的な使い方（運用スクリプト）

- ExecutionEngine（発注エンジン）を起動
  - 通常:
    python -m kabusys.run_execution
  - 実行挙動:
    - KABUSYS_ENV によって本番/ペーパートレードを切替。`paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード専用 DB (`PAPER_TRADING_SQLITE_PATH`) に記録します。
    - 起動時に `data/execution.pid`（デフォルト）を利用してプロセス管理。
    - 停止指示は `data/stop_requested.flag` を作成することで行います（スクリプト内で監視して停止）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境にかかわらず本番用の sqlite_path を使って監視ログを記録します（監視は監視専用のテーブルを初期化）。
    - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書きできます（秒）。
    - 停止は `data/stop_requested.flag` を作成または `KeyboardInterrupt`。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH または `--db` で DB を指定できます。
  - 稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を出力します。

ライブラリ / モジュールの利用例（簡単）
- 研究用関数（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - results = calc_momentum(duckdb_conn, date(2026, 4, 1))

- ポートフォリオ関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

- AI スコアリング（ニュース）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで必要）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1、production では 0 推奨)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env をロードしない（テスト時に便利）

ログ
- ルートで logs ディレクトリを作成し、アプリごとに日次ローテーションされたログファイルを出力します（例: logs/execution.log, logs/monitoring.log）。
- 出力先は環境変数 LOG_DIR、または setup_logging の引数で変更可能。
- setup_logging は標準出力（stdout）にもログを出力します。

Kill Switch / 停止フラグの仕組み
- kill.flag: 実際の ExecutionEngine を停止させるためのフラグ。KillSwitch（監視側）が書き込みます。
- stop_requested.flag: 起動スクリプト（run_execution / run_monitoring）が終了するためのローカル停止フラグ（プロセス監視用）。
- 起動時設定 `KILL_FLAG_CLEAR_ON_START=1` にすると自動で kill.flag を削除しますが、本番では危険のため 0 を推奨します。

ディレクトリ構成（主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 統合
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化含む）
    - system_monitor.py       — プロセス・リソース・データ鮮度監視
    - trade_monitor.py        — （取引監視ロジック）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/ (DB 関連)
  - その他: execution/*（発注関連）、data/*（実行時ファイル） など

補足 / 運用上の注意
- paper_trading モードは本番 API に対する発注を行わず、専用の DB に記録します。必ず `KABUSYS_ENV=paper_trading` を設定してください。
- 本番 (`KABUSYS_ENV=live`) 時は LINE 通知設定や kill flag 設定等を十分に確認してください。validate_config はライブ環境用のガードチェックを含みます。
- OpenAI など外部 API のレート制限や障害に対してはモジュール内でリトライやフェイルセーフを組み込んでいますが、運用時は API キー管理やコスト管理を行ってください。
- 自動で .env を読み込む機能があります（config.py）。CI / テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- ローカルでの開発・テスト時は LOG_LEVEL=DEBUG を使うと詳細ログが得られます。

よく使うコマンド早見
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上が README の要点です。セットアップや実行で不明な点があれば、実行時のログ出力（logs/ 以下）や validate_config の出力を確認してください。必要であれば README をさらに展開して、各モジュールの API 使用例や開発向けのテスト手順も追加できます。