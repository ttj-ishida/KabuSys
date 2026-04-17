CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

### Added
- プロジェクトの初期公開準備用の CHANGELOG を追加。

### Notes
- マイナーなドキュメント調整やメタ情報の更新のみ。

0.1.0 - 2026-04-17
------------------

初回リリース。以下の主要機能と実装を含みます。

### Added
- コアパッケージとバージョン情報
  - パッケージメタ: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 設定管理
  - .env ファイル自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を探索）。(src/kabusys/config.py)
  - .env のパース機能を強化（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理）。(src/kabusys/config.py)
  - OS 環境変数保護機能（.env 読み込み時に既存の OS 環境変数を保護）。(src/kabusys/config.py)
  - 各種設定プロパティを提供（DB パス、Paper Trading 用設定、監視閾値、PID / フラグパス、環境種別チェックなど）。(src/kabusys/config.py)
  - PAPER_FILL_MODE 等の入力バリデーションを実装（不正な値は ValueError）。(src/kabusys/config.py)

- 実行系起動スクリプト
  - 実取引/ペーパートレーディング向けの起動スクリプトを実装:
    - run_execution: ExecutionEngine を起動。Paper Trading 環境時は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。停止フラグ・PID 管理・thread ベースのセッション実行を実装。(src/kabusys/run_execution.py)
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用する旨を明記。（src/kabusys/run_monitoring.py）

- 監視関連
  - 監視 DB 初期化ユーティリティを使用して monitoring 用テーブルを保証（init_monitoring_db 呼び出し）。(src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)

- Execution 系コンポーネント（組み立て済み）
  - Broker クライアントファクトリ利用によるブローカー抽象化。OrderRepository, OrderManager, RiskManager（RiskConfig含む）, Reconciler, ExecutionEngine の組立てと起動制御。(src/kabusys/run_execution.py)
  - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装し、RiskManager に注入。(src/kabusys/run_execution.py)

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み付け:
    - select_candidates（スコア降順・signal_rank をタイブレーク）(src/kabusys/portfolio/portfolio_builder.py)
    - calc_equal_weights, calc_score_weights（スコア合計 0 の場合は等金額にフォールバック）(src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中抑制・レジーム乗数:
    - apply_sector_cap（既存保有のセクター割合を計算し上限超過セクターの候補除外）(src/kabusys/portfolio/risk_adjustment.py)
    - calc_regime_multiplier（bull/neutral/bear に対応し未定義はフォールバック）(src/kabusys/portfolio/risk_adjustment.py)
  - ポジションサイジング:
    - calc_position_sizes（risk_based / equal / score に対応、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）(src/kabusys/portfolio/position_sizing.py)
  - パブリックエクスポートを整理（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - calc_momentum, calc_volatility, calc_value（DuckDB を使った prices_daily / raw_financials に基づくファクター計算）。(src/kabusys/research/factor_research.py)
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、rank ユーティリティを実装（依存: DuckDB、標準ライブラリのみ）。(src/kabusys/research/feature_exploration.py)
  - research パッケージの公開 API を定義（src/kabusys/research/__init__.py）。

- AI ニュース NLP（設計と部分実装）
  - news_nlp モジュールを追加。OpenAI（gpt-4o-mini）を用いて raw_news を銘柄ごとに集約・バッチ送信しセンチメント（-1.0〜1.0）を ai_scores テーブルへ書込む設計を導入。バッチサイズ、トークン肥大対策、リトライ（指数バックオフ）等を仕様化。出力 JSON フォーマット厳格化。(src/kabusys/ai/news_nlp.py)
  - calc_news_window、score_news の初期実装（API キー検証・ウィンドウ計算・記事集約呼び出しの枠組みを実装）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（Windows と POSIX を吸収）。set_process_priority と set_cpu_affinity を提供。アクセス権限不足や未サポート OS は警告でスキップする実装。（src/kabusys/utils/process_priority.py）
  - utils パッケージ初期化ファイルを追加。

- ツール
  - Paper Trading 検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH を参照し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を表示。P95 計算、閾値の定義、コマンドライン引数（--from, --to, --db）をサポート。（src/kabusys/tools/paper_verification_report.py）

### Changed
- DB の使い分けに関する明確化
  - run_monitoring は「環境にかかわらず本番 sqlite_path を使用」する旨を明示（監視は本番 DB を対象の想定）。(src/kabusys/run_monitoring.py)
  - run_execution は Paper Trading 環境時に data/paper_trading.db を使用して完全に分離する挙動を実装。(src/kabusys/run_execution.py)

### Fixed
- .env 読み込みでのエラー耐性向上（ファイル読み込み失敗時に警告を出してスキップ）。(src/kabusys/config.py)
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対するフォールバック処理を実装。(src/kabusys/run_monitoring.py)
- calc_score_weights において全スコアが 0 の場合は等金額配分にフォールバックするよう修正（警告ログ出力追加）。(src/kabusys/portfolio/portfolio_builder.py)
- position_sizing のスケールダウンロジックで残余キャッシュを使った lot_size 単位の再配分を実装（資金不足時のフェアな割当てを改善）。(src/kabusys/portfolio/position_sizing.py)
- research/feature_exploration の calc_forward_returns は horizons 検証（正の整数かつ ≤252）を追加し不正な引数を拒否。(src/kabusys/research/feature_exploration.py)

### Known issues / Notes
- AI ニュース NLP の score_news 実装がコード断片の末尾で中断している（提供ソースでは _fetch_articles 呼び出し以降が未完）。完全な記事取得・API 呼び出し・レスポンス検証・テーブル更新処理は未完の可能性があるため、本番利用前に確認が必要。 (src/kabusys/ai/news_nlp.py)
- position_sizing 内に price が欠損（0.0）の場合のエクスポージャー過小見積りに関する TODO コメントあり。将来的に前日終値や取得原価をフォールバックする実装が想定されている。(src/kabusys/portfolio/risk_adjustment.py)
- lot_size を銘柄ごとに持たせる拡張（stocks マスタ参照）は未実装（TODO）。(src/kabusys/portfolio/position_sizing.py)
- DuckDB の executemany に関する注意（空 params の扱い）や一部 SQL が大量データ想定のためパフォーマンス考慮が必要。 (src/kabusys/ai/news_nlp.py, src/kabusys/research/*)

Security
--------
- 環境変数に API キーなどの機密情報を直接要求する箇所があります（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。運用時は適切な環境変数管理（シークレットストアや CI/CD シークレット管理）を推奨。

Contributing
------------
- バグや改善提案がある場合は issue を立ててください。AI ニュース NLP の未完部分や価格フォールバック、銘柄ごとの lot_size 拡張は優先度の高い改善候補です。

---