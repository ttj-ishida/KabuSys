CHANGELOG
=========

すべての非破壊的な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
比較: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-16
--------------------

Added
- パッケージ初回リリース相当の機能群を追加。
- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と完全分離する仕組みを導入。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせてエンジンを構築し、スレッドで実行。
    - 停止制御用フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
    - 起動直後にプロセス優先度を "high" に設定する処理を組み込み（psutil を利用）。
- 監視関連スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - check_once() の例外はログ出力して継続するフェイルセーフを実装。
- 設定管理
  - config.py
    - Settings クラスを導入して環境変数を集中管理。
    - .env / .env.local の自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。既存 OS 環境変数は保護される（.env.local は override）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサーは export プレフィックス、クォート、インラインコメントに対応。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / PID パス / 監視閾値 等）と検証ロジックを提供。
    - PAPER_FILL_MODE の有効値チェック（instant|partial|never|reject）を実装。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS を想定）。
    - CPU affinity 設定関数を提供（指定されたコア数に固定）。
    - 権限不足や非対応環境では警告ログを出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークロジックを実装。
    - calc_equal_weights / calc_score_weights: スコア合計が 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限による候補除外ロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score に対応した株数算出ロジック。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケーリング時に残差処理で lot_size 単位の再配分を行い再現性を確保。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials を用いた SQL ベースの計算。
    - 各種ウィンドウ長や欠損値ハンドリング、200 日移動平均のカウント制御等を考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）計算（ペア数不足時は None）。
    - factor_summary / rank: ファクター統計要約とランク関数を提供（同順位は平均ランク）。
  - research/__init__.py に主要関数をエクスポート。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、結果を ai_scores テーブルへ格納する処理を設計。
    - バッチ処理（1 リクエストで最大 20 銘柄）、トークン肥大化対策（記事数/文字数制限）、429/ネットワーク/5xx に対する指数バックオフ再試行、結果バリデーション、スコア ±1.0 クリッピング等の堅牢化を実装。
    - ニュース時間ウィンドウ計算（JST ベース）とシステムプロンプト定義を含む。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン引数 --from/--to/--db に対応し、稼働率・注文成功率・送信率・P95 レイテンシなどを算出して PASS/FAIL 判定を出力する。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定める。
    - P95 算出、欠損時の表示（N/A）や SQL エラーに対するフォールバック処理を実装。

Changed
- パッケージの初期構造を整備し、public API を __all__ で明示（kabusys.__init__, portfolio.__init__, research.__init__）。

Fixed
- （初期リリース）データ欠損や OS 非対応時のフェイルセーフとログ出力を随所に追加（psutil 例外、SQLite/DuckDB の OperationalError 等）。

Known issues / Notes
- ai/news_nlp.py のスクリプトは大枠の実装が含まれていますが、提供ソースの一部が途中で切れているため（スナップショット内で処理途中の行が存在）、実行前に _fetch_articles 等の内部関数の完全実装および統合テストが必要です。
- position_sizing の price が 0.0 （欠損）時にエクスポージャーが過少見積もられる旨の TODO コメントあり。将来的に価格フォールバック（前日終値等）を導入する余地あり。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール環境ではルートが見つからないケースに注意（その場合は自動読み込みをスキップ）。

Authors
- 初回リリース: コードベースから推測して記載

References
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/