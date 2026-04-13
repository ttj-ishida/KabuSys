CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

[Unreleased]
------------

- （現時点の変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ用エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境変数読み込み
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を追加。
    - .env/.env.local 読み込みロジック：export 形式・クォート（エスケープ対応）・インラインコメントを考慮した堅牢なパーサを実装。
    - OS 環境変数を保護する protected オプション（.env.local の override に際して OS 環境変数を上書きしない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを提供（テスト用途）。
    - Settings クラスを追加し、J-Quants / kabu / LINE / DB / 監視 / システム設定等のプロパティを提供。各種検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）対応のプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS に対する安全なフォールバック（警告ログ）を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの上限チェック（既存保有比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に対応した株数決定ロジック。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 価格欠損時のスキップやログ出力による堅牢性を確保。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を用いて各種ファクター（1M/3M/6M リターン、MA200 乖離、ATR20、平均売買代金、PER/ROE 等）を計算。
    - データ不足時の None 出力、ウィンドウ指定やスキャン日数のバッファを考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: ランク相関（Spearman）による IC 計算（同順位は平均ランクに処理）。
    - factor_summary: カラム単位の count/mean/std/min/max/median 集計。
    - rank ユーティリティ。
  - research/__init__.py で主要関数をエクスポート。
- AI / ニュースNLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価して ai_scores へ書き込む機能を実装（バッチ処理、最大20銘柄/チャンク）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事集約、1銘柄あたりの文字数・記事数上限を設けトークン肥大を抑制。
    - 429/ネットワーク/5xx 等に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護する書き換え戦略（DELETE→INSERT）を実装。
    - API キー未設定時は明示的エラーを返す。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加（--from / --to / --db オプション）。
    - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を算出し、事前定義された閾値で PASS/FAIL を判定して出力。
    - P95 算出ロジック、SQL の日付フィルタ生成、DB 存在チェック、OperationalError を考慮したフォールバックを含む堅牢な実装。
- DB 関連
  - run_* スクリプトやツールで sqlite3（monitoring / paper_trading）および DuckDB を併用する設計を採用。
  - monitoring_db.init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等処理）。
- ロギング
  - 各モジュールで logging を活用。起動時や重要な分岐点で情報・警告・例外ログを出力。

Known limitations / Notes
- ai/news_nlp.py のスコアリング処理は OpenAI API への依存があるため、API のレート・料金・利用規約に注意が必要。
- position_sizing の単元株（lot_size）は現状全銘柄共通の固定値（デフォルト 100）。将来的な銘柄別単元対応は TODO コメントあり。
- apply_sector_cap は price_map に 0.0 がある場合にエクスポージャーを過小評価する可能性があり、将来的にフォールバック価格の導入を検討。
- .env パーサは多くの一般的ケースをカバーするが、極端に複雑なシェル式の評価には対応しない。

Security
- このリリースでは既知のセキュリティ修正は含まれていません。環境変数や外部 API キーの管理は運用上の注意が必要です。

----- 

注: 上記の変更履歴は、提供されたコードベースの実装内容から推測して作成した要約です。実際のリリースノート作成時には、リポジトリのコミット履歴・CI 結果・設計ドキュメント等も参照して確定してください。