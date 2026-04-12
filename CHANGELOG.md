CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本アーキテクチャと主要コンポーネントを実装（初期リリース）。
  - execution: ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の実行系コンポーネントを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite DB (デフォルト: data/paper_trading.db) に記録する。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを組み込み（utils.process_priority.set_process_priority）。
  - monitoring: SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）を追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
    - 監視処理は本番用 sqlite_path を常に使用する設計（KABUSYS_ENV に依存しない）。
  - config: Settings クラスによる環境変数 / .env 読み込み・検証を実装。
    - .env 自動ロードをプロジェクトルート（.git または pyproject.toml）から行い、読み込み順序は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 必須キー取得用の _require() を実装し、未設定時は ValueError を送出。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）を実装。
    - データベースや監視設定等のデフォルトパス/閾値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）を提供。
  - tools: paper_verification_report スクリプトを追加。
    - Paper Trading の検証レポートを生成（期間指定 --from / --to、--db オプションで DB 指定可）。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を集計し、PASS/FAIL 判定（しきい値はソース内定義）。
  - portfolio: ポートフォリオ構築用の純粋関数群を追加（DB 非依存）。
    - 候補選定 (select_candidates)、等配分/スコア配分 (calc_equal_weights / calc_score_weights)。
    - セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
    - 株数決定・リスク制限・単元丸め (calc_position_sizes)（risk_based / equal / score の配分方式、aggregate cap のスケーリング、lot size 考慮）。
  - research: ファクター計算・特徴量探索モジュールを追加（DuckDB を利用）。
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials から各種ファクターを計算。
    - calc_forward_returns, calc_ic, factor_summary, rank：将来リターン計算、IC（Spearman ρ）計算、統計サマリー等を実装。外部ライブラリに依存しない実装。
    - DuckDB 接続を受け取り SQL と純 Python で安全に計算する設計。
  - ai: ニュース NLP スコアリングモジュール (ai.news_nlp) を追加。
    - raw_news を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとに -1.0〜1.0 のスコアを算出して ai_scores に書き込む。
    - バッチ処理（最大 20 銘柄／回）、トークン肥大対策（記事数・文字数制限）、429/5xx/ネットワークエラーに対する指数バックオフでのリトライを実装。
    - 出力バリデーション、スコアの ±1.0 クリップ、部分成功時のテーブル更新戦略（対象コードのみ置換）などフェイルセーフ設計。
    - OPENAI_API_KEY（引数または環境変数）必須。未設定時は ValueError を送出。
  - utils: プロセス優先度・CPU affinity 設定ユーティリティを追加（psutil 利用）。
    - set_process_priority(level: "high"|"normal"|"low")：Windows / POSIX の差分を吸収して実行。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count: Optional[int])：最初の N コアに固定。エラー時は警告でスキップ。
  - パッケージのメタ情報に __version__="0.1.0" を追加。

Changed
- なし（初期リリースのため既存機能の変更点は無し）。

Fixed
- なし（初期リリース）

Notes / 使用上の重要点
- 監視ランナー（run_monitoring.py）は KABUSYS_ENV に関係なく Settings.sqlite_path（本番 DB）を使用します。paper_trading と分離したい場合は別途 run_execution などの実行方式を利用してください。
- MONITOR_POLL_INTERVAL: 不正値（非整数・0 以下）は無視され、デフォルト 60 秒にフォールバックして警告を出します。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊環境では無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して外部から設定を提供してください。
- paper_verification_report はデータ欠損やテーブル非存在時に安全に N/A を扱うよう設計されています（OperationalError を捕捉してフォールバック）。
- ai.news_nlp は OpenAI API を直接呼び出します。API キーの管理と利用上のコスト・レートリミットに注意してください。

ライセンス
- （リポジトリに別途 LICENSE があればその内容に従ってください）