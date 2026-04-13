# Changelog

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

現在の日付: 2026-04-13

## [Unreleased]

- なし

## [0.1.0] - 2026-04-13

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報を src/kabusys/__init__.py に追加。

- 環境設定・.env ローダー（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env/.env.local を読み込む自動ロード機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートの有無に応じた適切な取り扱い）
  - 環境変数取得ヘルパーと必須チェック（_require）、Settings クラスを実装して各種設定（DB パス、API トークン、監視閾値、環境判定等）を提供。
  - PAPER_FILL_MODE のバリデーション、Paper Trading 用 SQLite パス、PID/KILL フラグ、しきい値（CPU/MEM/DISK）などの設定を提供。

- 実行系起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を立ち上げる CLI 用エントリポイントを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB（data/paper_trading.db）を使用し本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てと ExecutionEngine の run_session 呼び出しを実装。
  - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - プロセス優先度を起動時に "high" に設定。

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
  - 監視は環境に関わらず本番 sqlite_path を使用する設計。
  - 起動時にプロセス優先度を "high" に設定、KeyboardInterrupt 対応、例外発生時はログ出力して次ポーリングへ継続する堅牢化を実装。

- 監視 DB 初期化ユーティリティ（import 経由で使用: init_monitoring_db）
  - run_* スクリプトで監視用テーブルを冪等に初期化する処理を呼び出し。

- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows と POSIX 系 (Linux/Mac/FreeBSD) を吸収する set_process_priority(level) を実装。
  - set_cpu_affinity(cpu_count) により最初の N コアに固定可能（None はスキップ）。
  - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップする挙動を実装。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順＋タイブレークで上位 N 銘柄を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計 0 の場合は等配分へフォールバック）を提供。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックの実装（売却予定銘柄を除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0/0.7/0.3）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の allocation_method（"risk_based","equal","score"）をサポートした発注株数算出を実装。
    - lot_size（単元株）丸め、risk_pct, stop_loss_pct に基づく risk_based 計算、per-position 上限・aggregate cap（available_cash）に基づくスケーリングと端数配分ロジックを実装。
    - cost_buffer を考慮した保守的見積りをサポート。
    - 価格欠損（<=0）時のスキップやログ出力を実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を計算（DuckDB の prices_daily を使用）。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う設計。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。target_date 以前の最新レコードを取得する実装。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon の将来リターン（LEAD を使用）を一度のクエリで取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を実装。レコードが少ない/分散が 0 の場合は None を返す。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリーを提供。
  - research パッケージの __init__ に zscore_normalize のエクスポートを含めた公開 API を定義。

- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に書き込む機能を実装。
  - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）計算ユーティリティ calc_news_window を提供。
  - 1 銘柄あたり最大記事数／文字数でトリム、最大 20 銘柄バッチで API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング（±1.0）を実装。
  - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - CLI から paper_trading DB を解析して検証レポートを出力するスクリプトを追加。
  - システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算するクエリを実装。
  - P95 計算関数、日付フィルタの組立、エラー時のフォールバック（テーブル未存在時）を備える。
  - CLI 引数: --from, --to, --db。環境変数 PAPER_TRADING_SQLITE_PATH とデフォルトパスをサポート。
  - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- DB アクセス:
  - 実稼働データは SQLite（monitoring.db / paper_trading.db）および DuckDB（kabusys.duckdb）で扱う前提。
  - monitoring 初期化は冪等（init_monitoring_db を呼ぶことで既存テーブルがなくても安全に起動可能）。

- フェイルセーフ設計:
  - long-running な監視ループや API 呼び出しでの例外を捕捉してログ出力し、プロセスが停止しないようにしている。
  - プラットフォーム差（プロセス優先度や CPU affinity）による失敗は警告ログでスキップする。

- TODO / 注意点（今後の改善候補としてコード中に注記）
  - apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小見積りされる問題を改善するためにフォールバック価格（前日終値や取得原価）を導入検討。
  - position_sizing: 将来的に銘柄別 lot_size を導入するための拡張（stocks マスタに lot_size を持たせる等）。

---

今後のバージョンでは、既存モジュールのテスト追加、エラー監視の強化、AI スコアリングのバッチ失敗時の部分ロールバック戦略などを予定しています。変更履歴の補足や日付修正が必要であればお知らせください。