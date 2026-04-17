Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Removed, Deprecated, Security）に記載します。
- バージョンはセマンティックバージョニングに従います。

Unreleased
----------

（現在の差分・保留中の変更はここに記載してください。）

0.1.0 - 2026-04-17
------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション起動（バックグラウンドスレッド）を実装。
    - Paper Trading モード (KABUSYS_ENV=paper_trading) では paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - 起動時に data/execution.pid へ PID を扱う仕組み（pid_file の注入）。
    - data/stop_requested.flag を用いた外部停止フラグ検出により安全停止をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、異常値は警告してデフォルトにフォールバック）。
    - 監視処理では環境にかかわらず本番 sqlite_path を使用する設計（監視データは常に本番 DB に記録）。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
    - .env パーサを実装: export KEY=val 形式、引用符（シングル／ダブル）とバックスラッシュエスケープ対応、行内コメント処理などをサポート。
    - Settings クラスを追加し、各種設定をプロパティ経由で取得可能に（DB パス、PID/kill フラグ、しきい値、環境判定、PAPER_FILL_MODE の検証等）。
    - 設定値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄を除外して既存エクスポージャーを計算、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知はフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じた算出（risk_based / equal / score）をサポート。
    - 単元株（lot_size）単位での丸め、1銘柄上限・aggregate cap（available_cash）でのスケーリング、スケーリング後の残余を fractional 残差に基づき lot 単位で再配分するロジックを実装。
    - 価格欠損時のスキップやコストバッファ（手数料・スリッページ見積り）を考慮。

- 監視・DB
  - monitoring.monitoring_db モジュール経由での監視テーブル初期化を起動時に行う（init_monitoring_db を呼出し、冪等にテーブル存在を保証）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し呼び出し側はプラットフォームを意識しない。
    - CPU affinity 設定関数 set_cpu_affinity を追加（利用可能なコア数より多い指定は全コア使用へフォールバック）。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - momentum, volatility, value などのファクター計算を DuckDB を用いて実装（prices_daily, raw_financials テーブル参照）。
    - MA200 乖離、ATR、出来高/売買代金指標、PER/ROE などを計算。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（calc_ic）、ファクター統計 summary（factor_summary）、ランク変換（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - research/__init__.py で主要ユーティリティを公開（zscore_normalize の re-export 等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなど主要指標を算出し PASS/FAIL を判定する閾値を定義。
    - DB 欠損やテーブル欠如に対して堅牢に N/A を返す。

- AI ニュース NLP（OpenAI）
  - ai/news_nlp.py
    - raw_news から銘柄ごとのテキストを集約し OpenAI（gpt-4o-mini）でセンチメントスコアを生成して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理、トークン膨張対策（1銘柄あたりの最大記事数・最大文字数）、最大 20 銘柄バッチ、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ等の設計方針を明記。
    - calc_news_window 関数により JST ウィンドウ->UTC 変換を実装。
    - （注）本コードベース内の score_news 実装は途中までの状態（トランケートあり）だが、設計方針と主要ロジックが盛り込まれている。

Changed
- .env の処理
  - 自動ロードを .env/.env.local に限定し、OS 環境変数は保護（上書き禁止）する動作を採用。
  - .env パーサの挙動を改善（export 句、引用符、エスケープ、インラインコメントの扱いの明確化）。

- 監視（設計）
  - run_monitoring は KABUSYS_ENV に依らず常に本番 sqlite_path を使用するように設計（監視データの一元化を優先）。

Fixed
- 環境変数パーサの改善
  - export KEY= 形式や引用符付き値のエスケープ処理、インラインコメント認識などで誤解釈する可能性を修正・改善。

- MONITOR_POLL_INTERVAL
  - MONITOR_POLL_INTERVAL に無効な値（非整数、0 以下など）が設定された場合、警告ログを出してデフォルト（60 秒）へフォールバックするように修正。time.sleep に渡せない値による例外回避。

- process_priority の堅牢化
  - 未対応 OS や権限不足時に例外を上げずログでスキップするように改善。

- calc_score_weights のフォールバック
  - 全スコア合計が 0 の場合に等金額配分へフォールバックして警告を出すように修正（ゼロ除算回避）。

- position sizing のスケーリング安全弁
  - aggregate cap によるスケールダウン後、lot_size 単位で再配分する際に上限（raw_shares / max_per_stock）を超えないチェックを追加して過剰発注を防止。

- レポート/ツールの堅牢化
  - paper_verification_report の各クエリでテーブル欠如（OperationalError）に対して N/A / 0 を返すフォールバックを追加。

Notes / Known limitations
- ai/news_nlp.score_news 実装はファイル末尾で途切れている（トランケートあり）。完全な API 呼び出しと DB 書込処理は実装完了が必要。
- 一部の TODO（例: position_sizing の銘柄別 lot_size サポート、価格フォールバック）が残存している。
- 外部依存: duckdb, psutil, openai（環境に応じてインストールと API キーの設定が必要）。

ライセンス、セキュリティ
- 特にセキュリティ関連の修正は本リリースには含まれていません。API キーや機密情報の取り扱いは .env / OS 環境変数で行い、権限管理とログ出力に注意してください。

-- End of changelog --