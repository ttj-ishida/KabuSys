# Changelog

すべての非互換性のある変更はアリましたら明記します。
このファイルは Keep a Changelog 準拠で書かれています。

## [Unreleased]

（現在のリポジトリ状態は 0.1.0 をベースにしています。今後の変更はここに記載してください。）

---

## [0.1.0] - 2026-04-17

初回リリース。本リリースでは自動売買システム「KabuSys」のコアコンポーネント、ユーティリティ、分析・検証ツール群を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 強化された .env パーサ（export 形式サポート、クォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - 必須環境変数取得ヘルパ `_require()`、各種設定プロパティ（DB パス、Paper Trading の設定、監視閾値、環境判定等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

- 実行 / 監視用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - エンジンを別スレッドで実行し、data/stop_requested.flag により安全停止。
    - 監視テーブル初期化（init_monitoring_db の冪等呼び出し）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - data/stop_requested.flag によるループ停止、例外時のログ保護、KeyboardInterrupt 対応。
    - 起動直後にプロセス優先度を "high" に設定。

- プロセス管理ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - 権限不足や未サポート環境での安全なフォールバック（警告ログ）。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート + タイブレーク。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコアに基づく重み（合計 0 の場合は等配分にフォールバックして警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を元にセクター別上限を判定し、上限を超えるセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知レジームは警告のうえ 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウンを実装。
    - cost_buffer を考慮した保守的見積り、スケールダウン後の残余キャッシュを用いた端数（lot 単位）配分ロジックを実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（200 行未満は None）を DuckDB で高速集計。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）計算（有効レコード 3 件未満は None）。
    - rank / factor_summary: ランク付けおよびファクター統計要約（count/mean/std/min/max/median）。
  - src/kabusys/research/__init__.py に API をエクスポート。

- AI ニュース NLP（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数上限、文字数上限、JSON レスポンスバリデーション、スコアクリップ、リトライ戦略（指数バックオフ）などを設計。
    - API キー未設定時は ValueError。

- 検証 / ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 算出ユーティリティ、期間フィルタ、閾値（PASS/FAIL）判定ロジック、コマンドライン引数 --from/--to/--db を提供。

- DB 初期化ユーティリティ呼び出し
  - run 実行スクリプトで init_monitoring_db を呼んで監視用テーブルの存在を保証（冪等）。

### Changed
- なし（初回リリースのため主要な変更は追加のみ）。

### Fixed / Robustness
- .env 読み込みでのファイル読み込み失敗時に警告を出してスキップするように改善。
- MONITOR_POLL_INTERVAL のパースで不正値（0 や負数、非整数）を検出してデフォルトにフォールバックし、警告ログを出力。
- run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループ継続するように例外捕捉とログ出力を追加。
- run_execution/run_monitoring での DB 接続および DuckDB 接続を finally/終了処理で確実にクローズ。
- calc_score_weights で全スコアが 0 の場合に等配分へフォールバックして警告ログを出すように修正。
- calc_forward_returns で horizons の入力バリデーションを追加（正の整数かつ <=252）。
- factor_summary / calc_ic など統計処理で None や非有限値を排除する堅牢化。
- news_nlp の設計で API 失敗時に処理をスキップして他のコードへ影響を与えないフェイルセーフ動作を明記。
- process_priority/set_cpu_affinity で権限不足や未サポート環境を警告ログによりフォールバック。

### Notes / TODOs
- portfolio/position_sizing.py:
  - price が欠損（0.0）の場合にエクスポージャーやサイズ計算が過少見積りされる点を注記。将来的に前日終値や取得原価でのフォールバックを検討。
  - lot_size の将来的な拡張（銘柄別単元対応）についてコメントあり。
- news_nlp:
  - 実際の OpenAI 呼び出し実装の続き（_fetch_articles 以降の処理）が途中までの状態であるため、実装の継続が必要（現在の設計と入力検証は記載済み）。
- DuckDB の executemany 周りの互換性制約を踏まえ、空パラメータを渡さないチェック等を考慮。

### Security
- OpenAI API キーおよび各種シークレットは環境変数経由で取得。未設定時は明示的なエラーを投げる箇所あり（例: news_nlp.score_news、config._require）。

---

今後のリリースでは以下を想定しています:
- news_nlp の API 呼び出し・DB 書き込みの完成、単体テスト充実
- Execution / Monitoring の監視アラート・再起動戦略
- ポートフォリオ構築の追加アルゴリズム、lot_size マスタの導入
- パフォーマンス改善・ DuckDB クエリの最適化

変更や不具合の報告、改善提案は issue を作成してください。