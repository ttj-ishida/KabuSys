CHANGELOG
=========

すべての注目すべき変更履歴をこのファイルで管理します。
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし（現時点のリリースは v0.1.0）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ初期実装: kabusys v0.1.0 をリリース。
  - パッケージメタ情報に __version__ = "0.1.0" を追加（src/kabusys/__init__.py）。
- 実行用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 専用 DB（data/paper_trading.db）を使用し、MockBrokerClient で完全分離された動作が可能。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込む。
    - export KEY=val, クォート文字列、インラインコメント、エスケープ処理などに対応した堅牢な .env パーサを実装。
    - OS 環境変数を保護する protected 機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 各種設定プロパティを提供（J-Quants / Kabu API / LINE / DB パス / 監視しきい値 / PID ファイル等）。
    - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。
- ポートフォリオ構築
  - portfolio_builder: 銘柄選定と重み付け関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加。
    - apply_sector_cap は既存保有をセクター別に評価して新規候補を除外。
    - calc_regime_multiplier は market regime に応じた投下資金乗数を返す（bull/neutral/bear）。
  - position_sizing: 発注株数計算（calc_position_sizes）を追加。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積りを実装。
- リサーチ（ファクター計算・特徴量探索）
  - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials テーブルを想定した SQL ベースの実装。
    - MA200 や ATR 等のウィンドウ計算、データ不足時の None ハンドリングを実装。
  - research.feature_exploration: 将来リターン計算・IC（スピアマン）・統計サマリー・ランク関数を実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 外部依存を使わず標準ライブラリのみで実装。
  - research.__init__ で主要ユーティリティをエクスポート。
- ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py を追加。
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄単位のセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）、記事・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフリトライを実装（最大 _MAX_RETRIES）。
    - レスポンスの厳密なバリデーションとスコアクリップ（±1.0）、部分成功時に既存スコアを保護する DB 操作（該当コードの削除→挿入）を実装。
    - API キー未設定時は ValueError を送出する明示的なチェックを実装。
- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading DB（デフォルト data/paper_trading.db）から検証指標（稼働率 / 注文成功率 / 送信率 / レイテンシ P95 等）を集計してレポートを標準出力に出力する CLI ツール。
    - P95 算出、各クエリの日付フィルタ、閾値による PASS/FAIL 判定を実装。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を実装（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足や未対応 API の場合は警告を出して安全にスキップ。

Changed
- なし（初回リリース）

Fixed
- .env パーサ: export 形式のサポート、クォート文字列中のエスケープ処理、インラインコメント処理などを追加し堅牢性を向上（src/kabusys/config.py）。
- MONITOR_POLL_INTERVAL の取り扱い: 0 以下や不正値は警告出力のうえデフォルトにフォールバックして time.sleep の ValueError を防止（src/kabusys/run_monitoring.py）。
- calc_score_weights: 全スコア合計が 0 の場合に等金額配分へフォールバックし、明示的な WARNING を出す実装（src/kabusys/portfolio/portfolio_builder.py）。
- position_sizing の aggregate cap: 投資合計が available_cash を超えた場合のスケーリングと lot_size 単位での再配分ロジックを追加して端数処理を安定化（src/kabusys/portfolio/position_sizing.py）。
- research / feature_exploration: calc_forward_returns で horizons のバリデーション（1〜252 範囲）を追加し、SQL スキャン範囲のバッファを設定してパフォーマンスと堅牢性を改善。

Security
- ai/news_nlp.py: OpenAI API キーの未設定時に早期に例外を投げることで、意図しないネットワーク呼び出しを防止。

Notes / Known issues
- run_monitoring は監視用 DB として常に sqlite_path（本番想定）を使うため、開発環境で運用する際は sqlite_path の設定に注意してください。
- position_sizing は現状で全銘柄共通の lot_size を仮定しています。将来的な拡張点として銘柄別 lot_map の導入を想定しています（TODO コメントあり）。
- ai/news_nlp の実行は OpenAI API の利用料金・レート制限に依存します。大量実行時は API 制限に注意してください。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やインストール環境でルートが特定できない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を設定してください。

Acknowledgements
- 初期設計では DuckDB を分析用ローカル SQL エンジンとして利用し、SQLite を軽量な状態記録／トレードログ用に併用するアーキテクチャを採用しています。