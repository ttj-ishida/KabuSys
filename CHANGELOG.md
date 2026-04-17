# CHANGELOG

すべての変更は「Keep a Changelog」準拠の形式で記載しています。  
バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回リリース。システム監視・実行エンジン・ポートフォリオ構築・リサーチ・ニュースNLP・ユーティリティ類を含む基本機能を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 実行系スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動する一連のフローを実装。
    - エンジンはスレッドで実行し、プロセス内の停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを提供。
    - 実行用 PID ファイルを data/execution.pid に書き込む想定（設定経由）。

- 監視系スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）の場合はデフォルトへフォールバックして警告ログを出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用するように実装。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了する仕様。
    - duckdb を併用して処理を行うための接続確立をサポート。

- 設定／環境変数管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサを強化し、export 形式、クォート（シングル／ダブル）中のエスケープ、インラインコメントの取り扱いを実装。
    - 環境変数必須チェック用 `_require()` を提供。
    - Settings クラスを実装し、以下のプロパティ等を提供・検証:
      - J-Quants / kabu API / LINE 用設定プロパティ
      - duckdb_path, sqlite_path, paper_sqlite_path（paper trading 用 DB パス）
      - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）
      - 監視関連設定（pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk 閾値）
      - env/log_level の妥当性チェックと is_live/is_paper/is_dev の補助プロパティ

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告ログを出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有と指定の売却銘柄を考慮して候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score）。
    - 単元株丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮。
    - lot_size を考慮した残余配分ロジック（端数分の再配分）を実装。

  - package-level export を追加（kabusys.portfolio.* で主要関数を提供）。

- リサーチ／ファクター計算
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装。
    - データ不足時に None を返す等、堅牢性を確保。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman の ρ）計算、値のランク化（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部依存（pandas 等）を使わずに標準ライブラリで実装。

  - research パッケージのエクスポート設定を追加。

- ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news と news_symbols を基に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、トークン抑制（記事数・文字数上限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ、レスポンスの厳格なバリデーション、スコアのクリップ（±1.0）などフェイルセーフを実装。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（CLI: python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間指定（--from / --to）や DB パス（--db）を指定可能。
    - P95 の算出、各種閾値（稼働率 99%、成立率 90% 等）を定義している。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）を跨る抽象化関数 set_process_priority(level) を追加（high/normal/low をサポート）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加。
    - 権限不足や未対応 OS の場合は警告ログを出してフォールバックする実装。

- DB 初期化ユーティリティ（monitoring_db の init 関数呼び出しを各スクリプトで行うなど、監視テーブルの冪等初期化を確保）

### Changed
- 実行・監視プロセスの優先度設定
  - run_execution/run_monitoring の起動直後に set_process_priority("high") を呼び出してプロセス優先度を上げるようにし、実行中の安定性向上を図る。

- run_monitoring の DB 挙動
  - 監視プロセスは KABUSYS_ENV に関わらず本番 sqlite_path を使用する方針とした（紙トレード DB を使わない点に注意）。

### Fixed
- MONITOR_POLL_INTERVAL の取り扱い
  - 環境変数から読み取ったポーリング間隔が不正（非整数・0 以下など）の場合、警告を出してデフォルト（60 秒）にフォールバックするように修正。time.sleep に渡せない値でクラッシュしないように配慮。

- .env 読み込みの頑健化
  - .env のパース処理を改善し、引用符内のエスケープやコメント判定に対応。読み込みに失敗した際は警告（warnings.warn）を発するように改良。

### Notes / Breaking Changes
- 監視（run_monitoring）は paper_trading 環境でも本番用 sqlite_path を参照するため、paper_trading と監視 DB を完全に分離したい場合は設定を見直す必要があります。
- OpenAI API を用いる ai/news_nlp の score_news を使用する際は必ず OPENAI_API_KEY を設定してください。未設定時は例外を送出します。
- set_process_priority / set_cpu_affinity は実行環境（権限や OS）によって効果が無い場合があります。権限不足時は警告ログとなり処理は継続します。

### Security
- 特になし（本リリース時点で既知のセキュリティ脆弱性は報告されていません）。

---

今後の予定（例）
- news_nlp の API エラー時の部分更新ロールバックやトランザクション強化
- ポートフォリオ構築の lot_size を銘柄別に扱う拡張
- パフォーマンス改善（DuckDB クエリ最適化、並列化等）

もし特定ファイルごとの差分（追加・修正行など）や、リリースノートのフォーマット変更（英語併記、セクション分割の詳細化）をご希望でしたら指示してください。