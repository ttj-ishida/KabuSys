# CHANGELOG

すべての重要な変更点は Keep a Changelog 準拠で記載します。
このリポジトリはセマンティックバージョニングを使用します。

## [Unreleased]

### Added
- ドキュメントコメント・CLI の整備・ユーティリティ追加
  - 各モジュールに詳細な docstring を追加。使用方法、設計方針、想定入力値・出力値が明記されています。
  - コマンドライン実行用スクリプトを追加:
    - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、デフォルト 60 秒。監視は本番 sqlite_path を常に使用）。
    - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 環境時に MockBroker を使用し paper_trading.db に記録する仕組みを実装）。
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成ツールを追加（期間フィルタ、DB パス指定オプション、稼働率/成功率/レイテンシ等の判定基準を搭載）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分／スコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用。既存保有のセクター・エクスポージャ計算を行い、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジックを実装。単元（lot_size）で丸め、per-position 上限／aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、端数調整ロジックを実装。
- 研究・分析用モジュール
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを参照してファクターを計算（MA200、ATR20、リターン等）。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得する効率的クエリ実装（入力の horizons 検証あり）。
    - calc_ic / rank / factor_summary: スピアマン IC の計算、ランク付け、ファクター統計サマリを提供（外部ライブラリ非依存で実装）。
- utils/process_priority.py
  - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice 値を吸収）および CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS のときは警告を出力して安全にスキップ。
- ai/news_nlp.py（ニュース NLP スコアリング基盤）
  - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む設計を実装。バッチ処理、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx の再試行（指数バックオフ）、レスポンス validation、スコアの ±1.0 クリップ、部分更新（コード絞り込み）を想定した安全設計を導入。

### Changed
- 環境変数の自動読み込み挙動（config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動で読み込む仕組みを導入（テストなどで無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
  - .env ファイルのパースは export KEY=val、クォートやエスケープ、インラインコメントの取り扱いに対応。override / protected オプションにより OS 環境変数の保護を実現。
- 設定検証の強化（Settings）
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値を検証して不正値時に ValueError を送出するように変更。
  - DB パスや各種閾値等（duckdb_path, sqlite_path, paper_sqlite_path, cpu/memory/disk thresholds 等）を Settings 経由で一元管理。
- 実行フローの安定化
  - run_monitoring.py / run_execution.py 起動時にプロセス優先度を "high" に設定する呼び出しを追加（最初に実行）。
  - run_execution: paper_trading 環境時は専用の paper_trading.db を使用して本番 DB と完全に分離するように変更。ExecutionEngine の起動前に停止フラグファイルの存在チェックを行い、安全に起動を回避できる。
  - run_monitoring: 監視ループ内で停止フラグファイルを検知すると安全にループを終了。check_once の例外はログ出力して次ポーリングに進むフェイルセーフ実装。
- RiskManager / Engine の初期設定（run_execution）
  - RiskConfig のデフォルト値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を明示的に設定。initial_portfolio_value は broker.get_available_cash() を利用して初期化。

### Fixed
- SQL/DB 周りの堅牢化
  - tools/paper_verification_report.py: DB が存在しない場合のメッセージを明確化し、sqlite3.OperationalError 発生時に個別クエリを安全にデフォルト値へフォールバックする処理を追加。
  - research & tools の DuckDB/SQLite クエリで NULL 値やデータ不足に対する保護処理（COUNT/CASE/NULL チェック等）を強化。
- 数値処理の安定化
  - feature_exploration.rank: 浮動小数丸め（round(..., 12)）による ties 検出の安定化を追加。
  - position_sizing: 価格が欠損（0.0/None）の場合はスキップしてログ出力するようにして、安全性を向上。

### Security
- ai/news_nlp.py と settings:
  - OpenAI API キーの取り扱いは引数優先、引数未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗させる（キーが意図せず漏れるリスクを低減）。
  - .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI での誤読み込みを防止）。

### Known issues / TODO
- ai/news_nlp.py の実装は大部分が記載されていますが、ファイル末尾が未完であり一部関数（記事取得・API 呼び出しループ等）の実装が途中で切れています。完全な動作には追加実装が必要です。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合はエクスポージャが過少見積もられてしまう旨の TODO コメントが残っています。将来的には前日終値や取得原価のフォールバックを検討。
- position_sizing:
  - 将来的な拡張として銘柄別 lot_size を持つデザイン（lot_map）への対応が示唆されています。

---

## [0.1.0] - 2026-04-17

初回リリース:
- 上記 Unreleased に記載の主要機能をパッケージ化して公開。
- パッケージバージョンは __version__ = "0.1.0" を設定。

(注: 実際のリリース時には Unreleased の内容を適宜 0.1.0 へ移動してください。)