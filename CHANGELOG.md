CHANGELOG
=========
すべての変更は Keep a Changelog 規約に準拠して記載しています。  
セマンティックバージョニングを想定しています。

Unreleased
----------
### Added
- .env 読み込みの堅牢化
  - .env/.env.local の自動ロードをプロジェクトルート（.git または pyproject.toml）から行う仕組みを追加。
  - .env 行パーサで `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動ロード時に OS 環境変数を保護する protected オプションを導入（.env.local は上書き可能だが OS 環境変数は保護）。

- Settings の拡張・入力検証
  - 各種設定プロパティ（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）に妥当性チェックを追加。
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH 等の Path 解決（expanduser）を整備。
  - PID / kill フラグや閾値（CPU/MEM/DISK）など監視関連設定を Settings 経由で取得可能に。

- 実行スクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。paper_trading 環境では専用 SQLite（data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と完全分離。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（無効値はデフォルトにフォールバック）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- プロセス管理ユーティリティ
  - utils.process_priority.set_process_priority(level) を追加。Windows / POSIX を吸収してプロセス優先度を設定（失敗時は警告で安全にフォールバック）。
  - utils.process_priority.set_cpu_affinity(cpu_count) を追加。プロセスの CPU affinity を最初の N コアに固定する機能を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、ログ出力を考慮。
  - portfolio.position_sizing: position size 算出（risk_based / equal / score 対応）、単元株（lot_size）丸め、per-stock 上限や aggregate cap（available_cash）でのスケーリング処理、cost_buffer（スリッページ/手数料考慮）を実装。スケーリング時の残差処理（lot 単位での再配分）も実装。

- リサーチ / ファクター計算
  - research.factor_research: Momentum, Volatility, Value ファクター計算関数を実装（DuckDB を用いた SQL 実装）。MA200 や ATR、出来高/売買代金集計等に対応し、データ不足時は安全に None を返す。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリで実装。

- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で記事を集約。
    - 1チャンク最大 20 銘柄、article/char 制限でトークン膨張対策。
    - 429/ネットワーク/5xx などは指数バックオフでリトライ（最大回数設定）。
    - レスポンスを JSON モードでバリデーション、スコアを ±1.0 にクリップ。
    - 部分失敗時でも他コードの既存スコアを保護するために該当コードのみ DELETE→INSERT する更新方式。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数を集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、OperationalError による堅牢なフェールセーフを実装。
    - 判定閾値（稼働率 99%、成功率 90% 等）は定数として明示。

### Changed
- パッケージ初期化
  - kabusys.__init__ に __version__ = "0.1.0" を定義（バージョン管理）。

- DB 接続の明示化
  - run_monitoring/run_execution で sqlite3 と DuckDB の両方を使用するように統一。monitoring テーブルの初期化イニシャライズ関数（init_monitoring_db）を呼び、冪等性を保証。

Fixed
-----
- 環境変数パースの堅牢化により、一部の .env の誤パース（クォートやエスケープ、コメント誤判定）を回避。

[0.1.0] - 2026-04-12
---------------------
初回リリース。上記「Added」に記載した機能群を含む包括的な初期実装。

Added
- コア機能
  - ExecutionEngine / OrderManager / RiskManager / Reconciler / OrderRepository 等、注文執行フローの主要コンポーネント（スクリプト起動フローを含む）。
  - SystemMonitor と監視ループの起動スクリプト。
  - DuckDB ベースのファクター計算（momentum, volatility, value）および研究向けユーティリティ（forward returns, IC, summary）。
  - ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイジング）。
  - AI ニュース NLP による銘柄ごとのセンチメントスコアリング（OpenAI 経由）。
  - paper_trading 用の専用 DB 分離と MockBroker のサポート。
  - paper_verification_report による検証レポート出力。

- 設定・運用
  - 自動 .env ロード（.env / .env.local）と Settings による一元管理。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。
  - PID ファイル / kill flag 等の監視関連設定が Settings で指定可能。

Changed
- ドキュメント的補助（docstrings, module-level comments）を充実化し、設計思想や注意点（例: look-ahead バイアス回避、DuckDB の制約、単元株丸め挙動）を明記。

Notes / Breaking Changes
------------------------
- KABUSYS_ENV の取り扱い:
  - run_monitoring は「監視」用途のため環境にかかわらず本番 sqlite_path を参照する設計になっています。運用時は意図せぬデータ上書きを避けるため注意してください。
- PAPER_TRADING_SQLITE_PATH を用いた paper_trading の完全分離を想定しています。テスト/検証時は環境変数を適切に設定してください。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされます。パッケージ配布後の環境では明示的に環境変数を設定することを推奨します。

開発者向けメモ
---------------
- DuckDB クエリは prices_daily/raw_financials 等のテーブル構造を前提にしています。実行環境のスキーマを合わせてください。
- OpenAI API 利用部分は API キーが必須（引数または OPENAI_API_KEY 環境変数）。API 呼び出し失敗時はフェイルセーフでスキップする設計ですが、スコア取得に失敗した銘柄が存在する可能性があります。
- position_sizing の lot_size 現状はグローバル共通（デフォルト 100）。将来的な拡張で銘柄別 lot_map を導入予定。

-------------- 
（以降のリリースでは Unreleased → バージョンの移行、各項目の詳細なコミット参照を推奨します。）