# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

なお本履歴はコードベース（src/ 配下）の内容から推測して作成しています。実際のコミット履歴とは差分がある場合があります。

## [Unreleased]

### Added
- run_monitoring/run_execution 起動スクリプトを追加／整理
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告を出してデフォルトにフォールバックするロジックを追加。
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を監視用 DB として使用する挙動を明確化。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用する分離を実装。
  - 起動時にプロセス優先度を "high" に設定する処理を両スクリプトで実行（utils.process_priority.set_process_priority 呼び出し）。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）を実装。OS 環境変数を保護する override ロジックを導入。
  - .env パース処理を強化（export プレフィックス対応、クォートされた値中のバックスラッシュエスケープ処理、行内コメント処理のルール）。
  - 各種設定プロパティを追加・バリデーション実装:
    - PAPER_FILL_MODE 検証（instant/partial/never/reject）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
    - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等のパス解決
    - CPU/MEM/DISK 閾値、ログレベル、KABUSYS_ENV 検証（development/paper_trading/live）

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄候補選定と重み計算関数を追加:
    - select_candidates: スコア降順で上位 N 件を選択（score 同順位は signal_rank でブレーク）
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
  - リスク調整ロジック:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外（unknown セクターは除外対象外）
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）
  - ポジションサイジング:
    - calc_position_sizes: risk_based / equal / score の各配分方式をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に合わせたスケーリング）、cost_buffer を使った保守的見積り、残差を lot 単位で再配分するロジックを実装。

- リサーチ（kabusys.research）
  - DuckDB を用いたファクター計算を実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率
    - calc_volatility: ATR(20), ATR/price, 20日平均売買代金、出来高比
    - calc_value: EPS から PER、ROE 取得（raw_financials の最新レコードを target_date 以前で選択）
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: target_date から指定ホライズン後までの将来リターン（複数ホライズンを一回のクエリで取得）
    - calc_ic: スピアマン（ランク相関）による IC 計算（有効レコード 3 件未満は None）
    - factor_summary, rank: 基本統計量 / ランク変換

- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装:
    - ニュース収集時間ウィンドウの計算（JST 基準／UTC 変換）
    - 銘柄ごとに記事集約（記事数・文字数の上限でトリム）
    - 最大 20 銘柄単位でバッチ送信、JSON Mode 出力の厳密バリデーション
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンススコアは ±1.0 でクリップ
    - API キーの引数優先解決（api_key 引数または OPENAI_API_KEY 環境変数）

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成 CLI を追加:
    - --from / --to / --db オプションで期間と DB パスを指定可能
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定（閾値はソース内定数で可変）
    - P95 計算、各種 NULL 安全性、DB ファイル未発見時のエラーメッセージ

- ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差を吸収したプロセス優先度設定と CPU affinity 設定を追加:
    - Windows の優先度定数対応、POSIX 系の nice 値対応、サポート OS 判定、失敗時は警告を出してスキップ
    - set_cpu_affinity: 最初の N コアに固定する機能（引数チェック、失敗時に警告）

### Changed
- DB 接続や監視テーブルの初期化を冪等に: init_monitoring_db を実行して監視テーブルの存在を保証。
- run_execution の DB パス解決ロジックを明確化（paper_trading と production を分離）。
- duckdb 接続を各種モジュールで受け渡し、SQL を用いた集計処理に統一（research / ai / tools 等）。
- .env 自動ロードの挙動: OS 環境変数優先、.env.local は .env を上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを追加。

### Fixed
- 不正な MONITOR_POLL_INTERVAL 値（0 以下や非数）の扱いを改善し、time.sleep に渡す前にデフォルトにフォールバックして例外を防止。
- Paper Trading レポートでデータ欠損時にクラッシュしないよう各クエリ呼び出しを sqlite3.OperationalError で保護。
- calc_score_weights で全スコアが 0 の場合に 0 除算や不正な重みになる問題を解消（等配分にフォールバック）。
- calc_position_sizes のスケーリング処理で残余配分の安定性を向上（lot 単位での再配分、上限チェック）。
- news_nlp の API 呼び出し失敗時に全処理が止まらないようフェイルセーフ化（スキップ継続）。

## [0.1.0] - 2026-04-13

### Added
- 初期リリース: KabuSys の基盤機能を実装。
  - 自動売買実行基盤（ExecutionEngine 起動スクリプト、Broker クライアントファクトリ、OrderManager/Reconciler/RiskManager 等の雛形）。
  - 監視（SystemMonitor 起動スクリプト、監視 DB 初期化ユーティリティ）。
  - ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群。
  - DuckDB を利用したリサーチ（ファクター計算・将来リターン・IC 計算など）。
  - OpenAI を用いたニュース NLP スコアリングの基礎実装。
  - Paper Trading 用検証レポート生成ツール（CLI）。
  - 環境変数管理ユーティリティ（.env パーサ・自動ロード）、設定ラッパー（Settings クラス）。
  - プロセス優先度・CPU affinity を設定するユーティリティ。
  - パッケージバージョン: __version__ = "0.1.0"

### Changed
- プロジェクト構成をパッケージ化し、各モジュール（portfolio, research, ai, monitoring, execution, tools, utils）を整備。

### Fixed
- （当初リリースに含まれる軽微なバグ修正や安全対策を適用）

---

注: 実際のリリースに際してはコミット単位での詳細な CHANGELOG を作成することを推奨します。本ファイルは現在のソースコードから推測した機能追加・設計意図・安全対策をまとめたものです。