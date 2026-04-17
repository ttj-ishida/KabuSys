CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています（https://keepachangelog.com/ja/）。


Unreleased
----------

（現在のスナップショットでは未リリースの変更はありません）


0.1.0 - 2026-04-17
-----------------

初回リリース。リポジトリに含まれる主要機能・ユーティリティを追加しました。

Added
- 全体
  - パッケージ初期化: kabusys パッケージ（__version__ = 0.1.0）。
  - settings シングルトン（kabusys.config.Settings）を追加。環境変数／.env/.env.local の自動読み込みロジックと、各種設定プロパティを提供。
    - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われ、OS 環境変数が優先されます。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサは export プレフィックス、クォート（バックスラッシュエスケープ対応）、インラインコメント判定などに対応。

- 実行／監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行ループを実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。実行用 PID ファイル（data/execution.pid）を扱う。
    - RiskManager の設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトでセット。

  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。例外発生時はログを残して次回ポーリングへ継続。

- 環境・プロセスユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定 set_process_priority(level) を実装（Windows / POSIX を吸収）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（psutil 使用、権限不足等は警告でスキップ）。
    - 無効引数や未対応 OS に対するバリデーションと警告ログを追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバックして警告を出す。

  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックして警告。

  - portfolio.position_sizing:
    - calc_position_sizes: weight / equal / score / risk_based の各方式で発注株数を計算。単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）を考慮。
    - cost_buffer による手数料・スリッページ考慮、スケールダウン時の残差配分アルゴリズム（lot 単位での再配分）を実装。

  - portfolio パッケージの __all__ をエクスポート。

- リサーチ（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、売買代金、PER/ROE 等）を計算。
    - データ不足時に None を返すなど安全設計。

  - research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズンをまとめて取得）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。有効レコードが 3 件未満の場合は None を返す。
    - rank / factor_summary: ランク変換および基本統計量（count/mean/std/min/max/median）を計算。

  - research パッケージで zscore_normalize（kabusys.data.stats から）と上記関数をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを -1.0〜1.0 のスコアに変換して ai_scores に書き込む設計を追加。
    - バッチ（最大 20 銘柄）送信、JSON Mode 出力期待、429・ネットワーク断・5xx に対する指数バックオフ再試行、結果のバリデーション、スコアの ±1.0 クリップ、部分更新（対象コードの置換）などを想定した堅牢なフローを実装。
    - calc_news_window(target_date) を提供（前日 15:00 JST 〜 当日 08:30 JST に対応する UTC の窓を返す）。
    - API キー未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加。SQLite（デフォルト data/paper_trading.db）から各種指標を集計して標準出力へ整形レポートを出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、DB 存在チェック、DB のスキーマが無い場合のフォールバックを実装。

Changed
- 設定管理
  - .env 読み込みの優先順位を明確化: OS > .env.local > .env。読み込み時に OS 環境変数を保護する protected キー集合を導入。

Fixed
- 入力検証
  - Settings の各プロパティで許容値の検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。無効値は ValueError を送出し、早期に誤設定を検出可能に。

- 安全停止
  - run_execution/run_monitoring の両スクリプトで stop flag をポーリングし、安全に停止する処理を整備。

Notes / Known issues / TODO
- ai/news_nlp.py は全体設計と多くの実装（ウィンドウ計算、バッチ化、再試行など）を備えていますが、スニペットの末尾で記事取得部分が途中で切れているため（コード断片が不完全）、実行前に未実装箇所の補完が必要です。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でフォールバックする改善が必要。
- position_sizing:
  - 単元株 lot_size が全銘柄共通で固定になっている。将来的には銘柄別 lot_map を受け取る拡張を検討中（TODO コメント）。
- DuckDB 対象クエリは prices_daily / raw_financials 等のテーブル存在を前提とする。DB スキーマやデータがない環境では一部関数がエラーを投げる可能性があるため、呼び出し側での存在チェックや例外ハンドリングを推奨。

Security
- OpenAI API キーや各種シークレットは環境変数で提供する前提です。Settings._require により未設定時は ValueError を送出して明示的に失敗させます。シークレットのログ出力等は行わない方針です。

Removed / Deprecated
- なし（初回リリース）

Acknowledgements
- psutil, duckdb, openai 等の外部ライブラリを利用しています。実行環境に応じた依存関係のインストールが必要です。