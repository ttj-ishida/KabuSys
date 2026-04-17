CHANGELOG
=========

全般
-----
この CHANGELOG は「Keep a Changelog」仕様に準拠しています。
日付はリポジトリのコード内容から推測して付与しています。実際のリリース日やバージョン運用方針に合わせて適宜修正してください。

[Unreleased]
------------

- ドキュメント化や軽微な内部改善、テスト向けの環境変数制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）などを追加予定。

[0.1.0] - 2026-04-17
-------------------

Added
-----
- 基本パッケージ情報を追加
  - kabusys パッケージのバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。

- 実行/監視エントリポイント
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 環境に応じて paper_trading と本番を切り分け、paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド実行・停止フローを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視処理は環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグでループを終了し、例外でもループを継続するフェイルセーフ実装。

- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml で検出して自動で .env / .env.local を読み込む機能。
    - 読み込み順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサは export 形式やクォート、インラインコメント、エスケープ文字に対応。
    - 各種設定プロパティ（DB パス、API トークン、監視しきい値、PAPER_FILL_MODE 等）を提供。
    - env 値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と等金額・スコア加重（calc_equal_weights, calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクターエクスポージャーを計算して、閾値超過セクターの候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の配分方式）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、残差処理の実装。
    - cost_buffer を使った保守的見積り（手数料・スリッページ考慮）。

- 研究用モジュール (Research)
  - research/factor_research.py
    - モメンタム (1m/3m/6m), MA200 乖離、ATR20、流動性指標、バリュー（PER/ROE）計算を DuckDB 上の prices_daily/raw_financials を参照して実装。
    - データ不足時の None 設定やウィンドウ計算のバッファ処理を考慮。
  - research/feature_exploration.py
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ（count/mean/std/min/max/median）、ランク関数を実装。
    - 外部依存を抑え、標準ライブラリのみで実装。
  - research/__init__.py で主要 API をエクスポート（zscore_normalize を data.stats から再エクスポート）。

- ニュース NLP / AI 統合（下地実装）
  - ai/news_nlp.py
    - raw_news テーブルを集約して OpenAI API（gpt-4o-mini + JSON Mode）へ送信し、銘柄別にセンチメントスコアを ai_scores テーブルへ書き込むための処理フローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）計算、記事集約、バッチ送信（最大 20 銘柄）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアのクリップを設計。
    - API キー解決と未設定時の明示エラーを実装。
    - （実装途中でファイル末端が切れている箇所あり。fetch_articles 等の補助実装が続く想定）

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）を実装。
    - Windows / POSIX(Linux, Darwin, FreeBSD) に対応し、失敗時は警告を出してスキップ。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加（指定 None で無効化、範囲チェックあり）。
  - utils パッケージ初期化ファイルを追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から各種検証指標（稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等）を集計して標準出力にレポート出力するスクリプトを追加。
    - CLI オプション --from / --to / --db をサポート。日付は YYYY-MM-DD。
    - パス存在チェック、SQL の欠損（テーブル無し）を想定したフォールバック処理を実装。
    - 判定基準（閾値）を定数化し、PASS/FAIL を判定して出力。

- DB/監視関連
  - monitoring.monitoring_db.init_monitoring_db が各起動スクリプトから利用され、監視テーブルの存在を冪等で保証する仕組みを導入。
  - DuckDB 接続を複数コンポーネントで利用する設計（research/ai 等で共通利用を想定）。

Changed
-------
- （初回リリースのため変更履歴はなし）

Fixed
-----
- （初回リリースのため修正履歴はなし）

Security
--------
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY を要求する実装。未設定では ValueError を送出し安全性を高める。

Deprecated
----------
- なし

Removed
-------
- なし

Compatibility / Migration Notes
------------------------------
- データベース:
  - paper_trading 環境は本番 DB と明確に分離される（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。paper_trading の実行では専用 SQLite を使用するため、既存の本番 monitoring.db を誤って操作する心配は少なくなっています。
- 環境変数自動読み込み:
  - プロジェクトルートが検出できない場合は .env 自動ロードをスキップします。配布環境や CI で CWD に依存しない挙動を確認してください。
- OpenAI 統合:
  - API 利用には OPENAI_API_KEY が必要です。レート制限や 5xx などを考慮したリトライ実装を行っていますが、実運用前にキー・コール上限・課金条件を確認してください。

既知の問題 / 注意点
------------------
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）が含まれる場合、エクスポージャーが過少見積になりブロックが外れる可能性がある旨の TODO コメントがあります。将来的には前日終値や取得原価でのフォールバックが推奨されています。
- ai/news_nlp.py:
  - ファイル末尾で処理が途切れており、_fetch_articles 等の補助関数や最終的な DB 書き込みロジックの続きが必要です。現状でも API キー解決やウィンドウ計算などの堅牢な下地は実装済み。
- DuckDB executemany の制約に関する注意書きがあり（空パラメータの扱いなど）、バルク書き込み前に params が空でないことを確認する実装が設計に組み込まれている点に留意してください。
- utils/process_priority:
  - OS 権限不足や非対応プラットフォームでは設定に失敗し警告でスキップします。サービス起動ユーザーの権限によっては期待どおりに優先度が上がらない場合があります。
- run_monitoring / run_execution:
  - stop フラグや PID ファイルを使ったプロセス制御を行います。運用スクリプト側で data ディレクトリやフラグファイル操作の取り扱いを明確にしてください。

Contributing
------------
バグや改善提案は issue を立ててください。将来的にリリースごとにセマンティックバージョニングを適用することを推奨します。