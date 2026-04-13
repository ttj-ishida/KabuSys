Keep a Changelog
=================

すべての変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: KabuSys のコア機能群を追加。
- 実行/監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成（MockBrokerClient を含む）。
    - ExecutionEngine の起動に必要な依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定管理
  - config.py: 環境変数と .env ファイルを読み込む Settings クラスを追加。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の読み取りで export, クォート, インラインコメント等に対応するパーサを実装。
    - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - 各種デフォルトパス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等) を定義。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates, calc_equal_weights, calc_score_weights を追加。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中制限）を追加。既存保有のセクターエクスポージャーを計算し上限超過セクターの新規候補を除外。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。'bull'/'neutral'/'bear' をサポートし、未知値は警告のうえ 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes を追加。allocation_method('risk_based' / 'equal' / 'score') に対応し、単元株丸め、per-stock 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を考慮した保守的見積りを実装。スケールダウン後の端数は lot 単位で再配分するロジックを内蔵。
- リサーチ（DuckDB ベース）
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を追加。prices_daily / raw_financials テーブルを用いて各種ファクターを計算。
  - research.feature_exploration:
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関 ICD の計算）、factor_summary、rank を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ内で zscore_normalize（kabusys.data.stats から）を再エクスポート。
- AI ニュース NLP
  - ai.news_nlp:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を追加。
    - 1チャンク最大 20 銘柄、記事・文字数の上限 (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK)、JSON Mode 出力のバリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ（上限あり）。
    - ニュース集計ウィンドウの算出ユーティリティ calc_news_window を提供（JST の前日 15:00 〜 当日 08:30）。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority（Windows / POSIX を吸収）と set_cpu_affinity を追加。権限不足や未対応 OS の場合は警告を出して処理をスキップするフェイルセーフ実装。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し CLI 出力。--from/--to/--db オプションをサポート。
    - 報告用の判定閾値 (稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms) を定義。
- データベース連携
  - sqlite3 / duckdb を用途に応じて併用する設計を採用（monitoring 用 SQLite、分析用 DuckDB 等）。

Changed
- 初期化順序の注意点: run_execution/run_monitoring 起動時にプロセス優先度を最初に "high" に設定する処理を追加（set_process_priority を呼び出す）。
- run_execution: paper_trading 環境時に paper 用 DB を使用するよう明確化（settings.is_paper）。
- init_monitoring_db 呼び出しを run_execution/run_monitoring の両方に入れて監視テーブル存在を保証（冪等に実行）。
- config.py の .env ロード優先度: OS 環境 > .env.local > .env（既存 OS 環境は保護され上書きされない）。
- .env パーサを強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
- モニタリングのポーリング間隔取得で不正値（0 以下や非整数）を検出した際はデフォルトにフォールバックし警告を出すように改善。

Fixed
- プロセス優先度設定で権限不足・未対応環境だった場合に例外で落ちないよう try/except を追加し警告でスキップするように修正。
- position_sizing のスケールダウンロジックで lot 単位処理と残余配分を明確化し、端数処理の再現性を確保（安定ソートで determinism を維持）。
- research.feature_exploration.calc_forward_returns の horizons バリデーションを追加（正の整数かつ <=252）。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を必要とし、未設定時は明確な ValueError を発生させるようにして誤った運用を防止。

Notes
- デフォルト設定:
  - MONITOR_POLL_INTERVAL: 60 秒
  - PAPER_FILL_MODE: "instant"（有効値: "instant" | "partial" | "never" | "reject"）
  - デフォルト DB パス: data/monitoring.db（SQLite）, data/kabusys.duckdb（DuckDB）, data/paper_trading.db（paper trading）
- Breaking changes: なし（初回リリースのため互換性の概念は該当せず）。

Acknowledgements
- このリリースは、監視・実行・ポートフォリオ構築・リサーチ・AI スコアリング・運用ユーティリティを含む初期実装をまとめたものです。今後のリリースでは単体テストやパフォーマンス改善、エラー監視の強化を予定しています。