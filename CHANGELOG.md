CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。

Unreleased
----------

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用するなど、本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定/環境変数周り
  - Settings クラスを追加し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU/MEM/DISK 閾値など）をプロパティとして取得できるようにした。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。優先順位は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
- ユーティリティ
  - process_priority モジュールを追加。Windows / POSIX（Linux/Mac/FreeBSD）に対してプロセス優先度（high/normal/low）を設定し、CPU affinity を最初 N コアに固定する機能を提供。権限不足や未対応プラットフォームでは警告を出して安全にスキップする。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコアが 0 の場合は等金額配分へフォールバック）を追加。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームは警告を出して 1.0 でフォールバック。
  - position_sizing: 株数決定ロジックを追加（risk_based / equal / score に対応）。単元株（lot_size）丸め、1 銘柄上限・総額上限、cost_buffer を考慮した保守的見積り、aggregate cap によるスケールダウンと残差処理（lot 単位で再配分）を実装。
- リサーチ / ファクター計算
  - research.factor_research: Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB（prices_daily / raw_financials）から計算する関数を追加。データ不足時の None ハンドリングを実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ランク相関による IC 計算（calc_ic）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
- ニュース NLP（AI）
  - ai/news_nlp.py: raw_news / news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0～1.0）を算出し ai_scores テーブルへ書き込む処理を追加。特徴:
    - タイムウィンドウ計算（JST 基準から UTC に変換）を提供（calc_news_window）。
    - 1 銘柄あたり記事数・文字数上限でトリム（トークン肥大対策）。
    - 最大バッチサイズ、JSON Mode の利用、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分成功時の DB 保護（対象コードに絞って置換）などを設計方針としている。
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率・注文成功率・送信率・レイテンシ等の指標を集計して標準出力にレポートを出す CLI スクリプトを追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定する。期間指定（--from/--to）と --db オプションに対応。DB が存在しない場合のエラーメッセージを備える。

### Changed
- DB ハンドリングのポリシーを明確化
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB へ）。
  - 実行（run_execution）は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用し、本番 DB と完全分離する。
- ログ/エラーハンドリング改善
  - run_monitoring のポーリングで check_once() 実行時の例外はログに例外情報を出力して次のポーリングまで継続する（フェイルセーフ）。
  - process_priority の設定失敗時や CPU affinity 設定失敗時に詳細な警告ログを出すようにした。

### Fixed
- 環境変数パースの堅牢化
  - .env の値に引用符付き文字列やバックスラッシュエスケープを正しく扱うようにした。インラインコメントの判定ルールも改善。
- ポジションサイズ計算の安定化
  - weight が全 0 の場合に calc_score_weights で等分配へフォールバックすることで、ゼロ除算や不適切な配分を防止。
  - aggregate cap スケーリングで残余キャッシュを有効利用するための端数処理（lot 単位の再配分）を実装し、合計投下額が available_cash を超えた場合に合理的にスケールダウンする挙動を修正。

0.1.0 - 2026-04-17
------------------
(初回リリース — 本バージョンで上記の機能群を導入)

- コア機能
  - 自動売買システムの基本モジュール群を初期実装:
    - 実行エンジン起動、監視用ポーリング、環境設定、プロセス優先度制御、ポートフォリオ構築（シグナル選定、重み算出、ポジションサイズ決定）、リスク調整（セクターキャップ・レジーム乗数）、リサーチ（ファクター計算、将来リターン、IC、統計サマリ）、ニュース NLP スコアリング、紙トレード検証レポート等。
- 設定/運用
  - .env 自動ロードと豊富な環境変数オプションを提供。デフォルトパスや制御フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD 等）を定義。
- 安全性/堅牢性
  - 外部 API 呼び出しや DB 操作でのフォールバック、例外キャッチ、ログ出力を多用し本番運用上の安全弁を多数実装。

注記
----
- 上記はソースコードの内容から推測して記載した変更履歴です。実際のリリースノートに記載する際は、コミット履歴や PR、担当者コメント等と照合してください。