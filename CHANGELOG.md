CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」初版を追加。
- 基本パッケージ情報
  - パッケージ定義とバージョン: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境・設定管理
  - .env 自動読み込み機能（プロジェクトルートの .git または pyproject.toml を探索）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（src/kabusys/config.py）。
  - .env パーサの実装: export プレフィックス、クォート文字列、インラインコメント、エスケープ処理に対応（src/kabusys/config.py）。
  - 設定クラス Settings を提供し、各種環境変数（DBパス、APIトークン、監視閾値、環境種別等）を型変換付きで取得可能（src/kabusys/config.py）。
  - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
- 実行 / 監視スクリプト
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し MockBrokerClient を利用する設計（src/kabusys/run_execution.py）。
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照する（src/kabusys/run_monitoring.py）。
- データベース初期化
  - 監視テーブルを保証する init_monitoring_db 呼び出しを実行フローに組み込み（run_execution/run_monitoring）。
- プロセス制御ユーティリティ
  - プロセス優先度設定ユーティリティを追加。Windows / POSIX の差分を吸収し、set_process_priority("high"|"normal"|"low") を提供。CPU affinity 設定機能も実装（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限（apply_sector_cap）と市場レジームによる乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - 株数決定ロジック（リスクベース／等分配／スコアベース）、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮を実装（src/kabusys/portfolio/position_sizing.py）。
  - ポートフォリオ API をパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。
- 研究（Research）機能
  - ファクター計算モジュール：モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高等）、バリュー（PER/ROE）を DuckDB ベースで実装（src/kabusys/research/factor_research.py）。
  - 特徴量探索モジュール：将来リターン計算、IC（Spearmanランク相関）計算、ファクター統計サマリー、ランク関数を実装（src/kabusys/research/feature_exploration.py）。
  - research パッケージの公開 API を定義（src/kabusys/research/__init__.py）。
- ニュース NLP（AI）モジュール
  - raw_news テーブルを読み、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを ±1.0 範囲で算出し ai_scores テーブルへ書き込む機能を実装。バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策、再試行（指数バックオフ）、レスポンス検証、部分的な DB 更新戦略を備える（src/kabusys/ai/news_nlp.py）。
  - ニュース時間ウィンドウ計算ユーティリティを実装（target_date に対し前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲を生成）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を算出して標準出力へ出力（src/kabusys/tools/paper_verification_report.py）。閾値を設けた PASS/FAIL 判定を行う。
- DB ドライバ
  - duckdb と sqlite3 を組み合わせた運用を前提とした接続コードを多数のモジュールで利用（run scripts、research、ai 等）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から取得し、未設定時は安全にエラーを返すように実装（src/kabusys/ai/news_nlp.py）。

Notes / Implementation details
- 多くのアルゴリズム（ポジションサイジング、セクター制限、ファクター計算等）は純粋関数として実装され、DB 参照を限定しているためユニットテストが容易な設計。
- DuckDB は分析処理（prices_daily / raw_financials 等）用、SQLite はモニタリングや取引ログ保持用に使い分ける想定。
- 実行スクリプトは起動時にプロセス優先度を高く設定しようと試みるが、権限がない場合は警告を出してスキップするフェイルセーフを備える。
- .env パーサは細かなケース（クォート、エスケープ、コメント）に対応しており、既存の OS 環境変数の保護機能を持つ。

今後の予定（例）
- 単体テストの追加および CI パイプライン整備
- BrokerClient の実装差し替え／抽象化とモックの充実
- 銘柄別 lot_size の対応（現状は全銘柄共通の lot_size）
- ニュース NLP のレスポンスキャッシュやトークン最適化

以上。