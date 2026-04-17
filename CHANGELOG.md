# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

なお下記は提供されたコードの実装内容から推測して作成した変更履歴です（コミット差分ではなくコードベースの機能一覧を反映しています）。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys パッケージの主要コンポーネントを追加。
- 実行 / 監視起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - ストップフラグ（data/stop_requested.flag）検出による安全な停止処理を実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成に BrokerClientFactory を利用。
    - OrderRepository, OrderManager, Reconciler, RiskManager（デフォルト設定含む）を組み立てて ExecutionEngine を開始。
    - 実行中の PID 管理用ファイル（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用する仕様。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次ポーリングへ継続。
- 設定 / 環境変数管理
  - src/kabusys/config.py を導入。
    - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を基準）。
    - export 付き行やクォート・エスケープ、インラインコメント等を考慮した .env パーサ実装。
    - Settings クラスを提供し、主要設定プロパティ（J-Quants トークン、kabuAPI パスワード、DB パス、PID/kill flag パス、閾値、環境判定など）を取得する API を追加。
    - PAPER_FILL_MODE の検証（valid 値: instant, partial, never, reject）や PAPER_TRADING_SQLITE_PATH のサポート。
    - KABUSYS_ENV と LOG_LEVEL の検証。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの選別 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
  - portfolio/risk_adjustment.py
    - セクター上限 (apply_sector_cap) と市場レジームに基づく乗数 (calc_regime_multiplier) を追加。
    - 未知レジーム時のフォールバックや "unknown" セクターの扱いに関する方針を実装。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した株数算出ロジックを追加。
    - 単元株（lot_size）、最大ポジション上限、利用可能現金に基づくスケールダウン（aggregate cap）ロジック、端数処理（lot 単位）を実装。
    - cost_buffer（コスト見積り）を考慮した保守的見積りをサポート。
  - portfolio/__init__.py で上記関数をエクスポート。
- 研究 / リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB の prices_daily/raw_financials テーブルを参照し、ウィンドウや欠損処理を考慮した SQL を生成。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary（factor_summary）、ランク付け util（rank）を実装。
    - pandas 等に依存せず標準ライブラリのみで統計処理を実装（再現性・軽量設計）。
  - research/__init__.py でエクスポート（zscore_normalize は data.stats から参照）。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py を追加（OpenAI API 使用のニュースセンチメントスコアリング）。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を実装。
    - 記事集約、銘柄ごとのトリミング（最大記事数 / 最大文字数）、最大バッチサイズ、API へのバッチ送信（gpt-4o-mini）を想定。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライの方針、レスポンスバリデーション、スコアを ±1.0 にクリップする実装方針を記載。
    - score_news 関数は OPENAI_API_KEY の存在チェックを行い、未設定時は ValueError を送出。
    - （注）提供ファイルは途中で切れているため、記事取得部分（_fetch_articles 等）は続き実装が必要。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows/POSIX（Linux/Mac/FreeBSD）の対応、例外時のフォールバックログ、set_cpu_affinity の実装を含む（アクセス権限エラー等はログで警告してスキップ）。
- 監視・検証用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。CLI 引数で期間指定可（--from / --to / --db）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等の集計・閾値判定を実装。既定閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms。
    - DB が存在しない場合のエラーメッセージ、テーブル未存在時の保守的ハンドリング（OperationalError 捕捉）を備える。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースにつき新規追加が中心）

Fixed
- なし（初回リリースにつき新規追加が中心）

Security
- OpenAI / 各種 API キーは環境変数経由で取得する仕様（未設定時は例外を返す関数があるため、運用時に API キーの管理が必要）。

Notes / Known issues
- ai/news_nlp.py の記事取得処理周り（ファイル中の _fetch_articles 呼び出し以降）が途中で切れており、完全な動作には残り実装が必要。score_news の冒頭は API キー検証やウィンドウ計算まで実装済み。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布先で .git / pyproject.toml が無い場合は自動ロードがスキップされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- position_sizing の価格欠損時（price が 0.0 等）における挙動はログ出力でスキップする設計だが、将来的に前日終値等のフォールバックを導入する余地あり（TODO コメントあり）。

----

注: 上記は提供されたコードファイル群の内容から機能・設定・挙動を要約して CHANGELOG 風に整理したものです。実際のリリース履歴やコミット単位の変更ログと差異がある可能性があります。必要であれば、個別機能ごとの詳細な変更点（該当ファイル・関数ごとの API 仕様や例）も追記します。