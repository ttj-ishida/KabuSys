CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠しています。  
日付はリリース／変更が反映された想定日付です。記載内容は提示されたコードベースの内容から推測してまとめています。

Unreleased
----------
（今後の変更やバグ修正をここに記載してください）

[0.1.0] - 2026-04-13
-------------------

初期リリース — 基本的な自動売買フレームワークと運用周りのユーティリティを実装しました。

Added
- コアパッケージの追加
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0" を定義。
- 実行／監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境に応じて paper_trading 用 DB を分離し、BrokerClientFactory 経由でブローカークライアントを生成。ExecutionEngine のセッション実行と関連コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理
  - config.py: .env 自動ロード機能（.env / .env.local）を実装。プロジェクトルート判定（.git または pyproject.toml）を行い、.env のパースロジックを実装（export 付き行対応、クォート内エスケープ、インラインコメント対応など）。必須環境変数取得ヘルパー _require と Settings クラスを提供。多数の設定プロパティ（DB パス、PID/KILL フラグ、各種閾値、環境判定、paper_trading 用設定等）を追加。
  - PAPER_FILL_MODE の検証実装（有効値: instant/partial/never/reject）。
- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run scripts に追加（冪等に監視テーブルを保証）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間指定 (--from / --to / --db) によるレポート出力、稼働率・注文成功率・送信率・レイテンシ（P95）等の集計と PASS/FAIL 判定を実装。デフォルト DB は data/paper_trading.db。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額にフォールバックする警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、レジーム乗数を返す calc_regime_multiplier（bull/neutral/bear）を追加。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、max position / aggregate cap、スケーリングと残差処理、cost_buffer による保守見積り等を実装。
- 研究（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算を実装（DuckDB を用いた SQL ベース）。calc_momentum, calc_volatility, calc_value を提供。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）や rank、統計サマリー（factor_summary）を実装。外部依存を最小にした純粋な実装。
  - research/__init__.py で主要関数群を公開。
- ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news と news_symbols を元に OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ書き込むロジックを追加。処理はチャンク（最大 20 銘柄）でバッチ送信し、429/ネットワーク/5xx などは指数バックオフでリトライ。API キー未設定時の ValueError、レスポンス検証、スコアの ±1.0 クリップ等を実装。ニュース収集ウィンドウ計算（JST→UTC 変換）を提供。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX（Linux/Mac/FreeBSD）をサポートし、失敗時は警告を出してスキップする安全設計。
- データベース関連
  - DuckDB / SQLite 接続を多くのモジュールで使用（research, ai, run scripts, tools 等）。

Changed
- デフォルト設定
  - デフォルトのデータパスや PID ファイルパスなどの既定値を定義（例: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db, PID_FILE_PATH=data/execution.pid）。
- 安全性／堅牢性の向上
  - run_monitoring のポーリングループで check_once() の例外をキャッチしてログに出力し、次ポーリングへ継続するフェイルセーフを実装。
  - init_monitoring_db の呼出しにより監視テーブルが存在しない環境でも起動可能に（冪等性を担保）。
  - Paper verification ツールは DB 未存在時に明示的なエラーメッセージを出す。

Fixed
- .env 読み込みの堅牢化
  - config._parse_env_line にて export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等を正しく処理するように実装。
  - .env 自動ロードはプロジェクトルートが特定できない場合にスキップするようにして、パッケージ配布後の安全性を考慮。
- ポジションサイズ算出の保守的処理
  - position_sizing.calc_position_sizes に aggregate cap スケーリングと残差処理を実装し、残余キャッシュがある場合に lot_size 単位で追加配分するロジックを追加（再現性を確保するため安定ソートを使用）。

Notes / Known limitations
- news_nlp の OpenAI 呼び出しは API キーが必要。API のレスポンスフォーマットに厳密に依存しているため、外部仕様変更時は調整が必要。
- 一部の価格欠損時の扱い（apply_sector_cap 内の price が 0 の場合の挙動など）は将来的な改善（前日終値や取得原価のフォールバック）を想定しているが現状は簡潔化されている。
- calc_forward_returns / factor 計算は DuckDB のテーブル（prices_daily / raw_financials 等）に依存する。対象テーブルの整備が前提。
- process_priority の設定は OS 権限に依存し、権限不足時は警告を出してスキップする設計です。

参考
- 各モジュールは "pure function" の設計方針が明記されている箇所があり、テスト容易性を意識した実装になっています。
- ログレベルや動作環境は Settings を通して環境変数で制御できます（KABUSYS_ENV, LOG_LEVEL 等）。

--- 
（以降のバージョンでは Unreleased に記載した項目を移動し、リリース日を明記してください。）