# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
注: 以下は提供されたコードから推測して作成した変更履歴です。実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-16
初回公開リリース。

### Added
- 基本パッケージとバージョン番号を追加（kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。  
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、paper_trading 用に分離された SQLite（data/paper_trading.db）を利用する動作をサポート。
    - 停止フラグ（data/stop_requested.flag）/ PID ファイル（data/execution.pid）による起動制御・シャットダウン対応。
    - スレッドでエンジンを起動し、停止フラグ検出時にエンジン停止を行う安全な終了処理を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）と初期ポートフォリオ値を broker.get_available_cash() から取得する設定を追加。
- 監視系
  - SystemMonitor ポーリング起動スクリプトを追加（src/kabusys/run_monitoring.py）。  
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する挙動を明記。
    - 停止フラグ検出、例外発生時のロギングと継続処理、リソース（DB 接続）の確実なクローズを実装。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数（.env / .env.local の自動ロード含む）から各種設定を提供。
    - .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - export KEY=val 形式、クォート文字列、インラインコメントの扱いなど堅牢な .env パースを実装。
    - 各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種しきい値等）を提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）を行う。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・同点は signal_rank でタイブレーク）
    - calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有によるセクター上限の除外ロジック、unknown セクターは除外対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数を実装、未知レジームは警告とフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）丸め、per-position の上限、aggregate cap によるスケーリング（余剰キャッシュを考慮して lot 単位で再配分）、cost_buffer（手数料/スリッページ見積り）対応。
    - 入力検証とログ出力を含む堅牢な計算ロジック。
- 研究用モジュール（DuckDB ベース）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials を参照しモメンタム・ボラティリティ・バリューを算出。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターン計算、horizons のバリデーション）
    - calc_ic（Spearman ランク相関（IC）算出。データ不足時は None を返す）
    - rank, factor_summary（ランク付け・統計サマリー）
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。
- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/Mac 等の差分を吸収。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - 権限不足や未対応 OS の場合は警告を出し安全にスキップ。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs テーブルを集計し、稼働率・注文成功率・送信率・レイテンシ等を評価。デフォルトの合格基準（稼働率>=99%、成功率>=90%、P95<=200ms 等）を設定し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from / --to / --db をサポート。
- AI ニュース NLP（部分実装）
  - ニュースのセンチメントを OpenAI API（gpt-4o-mini）でスコアリングするモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）やバッチ処理、最大記事長・記事数のトリム、API リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、ai_scores への書き込み手順を設計。ただしファイル末尾が切れているため実装は部分的（_fetch_articles 呼び出し付近で中断）であることに注意。

### Changed
- 実行・監視スクリプトでプロセス優先度を最初に High に設定するよう統一（run_execution.py, run_monitoring.py）。
- Execution 起動時に監視テーブルが存在することを保証するため init_monitoring_db を呼び出すように変更（冪等性確保）。これにより Paper Trading 用 DB でも監視テーブルが存在することを保証。

### Fixed
- .env パーサーの堅牢性向上（export プレフィックス対応、クォート内のエスケープ、コメント処理の改善など）により自動環境読み込み時の誤設定リスクを低減（src/kabusys/config.py）。
- 設定値の検証追加により不正な環境変数（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）での起動失敗を早期に検出。

### Known issues / TODO
- news_nlp モジュールの実装が途中で切れており、記事取得部分（_fetch_articles）以降が未完。完全な API 呼び出し → テーブル更新の実装が必要。
- position_sizing.apply_sector_cap の価格欠損時のフォールバック（TODO コメントあり）：現在 price_map に 0.0 がある場合にエクスポージャーが過小評価される恐れがある。前日終値や取得原価を用いるフォールバック実装を検討する必要がある。
- 将来的には個別銘柄ごとの lot_size を導入する（現在はグローバル lot_size を想定）。（position_sizing.py に TODO）
- duckdb executemany の制約（params が空でないこと）に留意する必要あり（news_nlp の設計メモに記載）。

### Security
- 外部 API キー（OpenAI など）は環境変数経由で供給する設計。コード中でのハードコーディングは行っていないが、運用時の環境変数管理に注意。

---

以上がコードベースから推測して作成した CHANGELOG.md です。必要であれば各項目をコミット単位や担当者付きで分解した詳細な履歴案を作成します。