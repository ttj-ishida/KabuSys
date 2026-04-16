# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」に準拠した形式で記載しています。

フォーマット: セマンティックバージョニングに準拠しています。  

---

## [Unreleased]

- ドキュメント化や内部リファクタリング向けの注記を集約中。

---

## [0.1.0] - 2026-04-16

初回公開リリース。以下の主要機能・改善を含みます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングしてシステム状態を継続監視するループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグで制御。
    - 監視処理は実行環境にかかわらず本番用 sqlite_path を使用する仕様を明示。
  - run_execution.py
    - ExecutionEngine を起動するランナーを実装。
    - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - 実行中は別スレッドでエンジンを実行し、停止フラグで安全に停止させるループ構成。

- 設定管理
  - config.Settings クラスを実装。環境変数経由で各種設定（DB パス、API トークン、監視閾値、ログレベル等）を取得。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込みを実装（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 環境値のバリデーション:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL の検証。
    - PAPER_FILL_MODE の許容値検証（instant/partial/never/reject）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコアに基づく選定と重み計算を提供。
  - portfolio.position_sizing
    - calc_position_sizes を実装。risk_based / equal / score の配分方式に対応し、単元株（lot_size）で丸め、aggregate cap（利用可能現金）に基づくスケーリングを実装。
    - cost_buffer を考慮した保守的見積りを実装。
  - portfolio.risk_adjustment
    - apply_sector_cap によるセクター集中制限（既存ポジションを考慮）を実装。
    - calc_regime_multiplier による市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を利用して各種ファクターを算出。
  - research.feature_exploration
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary、rank を実装。
    - pandas 等の外部依存を用いず標準ライブラリと DuckDB で完結する設計。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存する処理骨格を実装。
    - バッチサイズ、トークン肥大対策（記事数/文字数上限）、JSON Mode での入出力、429/ネットワーク/5xx に対する指数バックオフリトライ、スコアの ±1.0 クリップを実装。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - API キー未設定時に明示的にエラーを返す。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し PASS/FAIL 判定を行う。しきい値はソース内で定義（稼働率 99% 等）。
    - --from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB を参照。

- ユーティリティ
  - utils.process_priority
    - psutil を用いて Windows / POSIX（Linux/Mac/FreeBSD）でプロセス優先度と CPU affinity を設定するユーティリティを実装。
    - アクセス権限や未対応 OS の場合は警告を出してスキップする堅牢な実装。

- パッケージメタ
  - __version__ を "0.1.0" に設定。

### Changed
- .env ローダーを堅牢化
  - export KEY=val 形式、クォートされた値、インラインコメントの扱い、既存 OS 環境変数の保護（protected）を考慮するよう改善。
  - .env.local を .env の上書き用にサポート（ただし OS 環境変数は保護）。

- DB 周りの扱いを明確化
  - 監視用途（run_monitoring）は常に本番 sqlite_path を使用する仕様を明示。
  - 実行エンジン側は paper_trading 環境時のみ paper_sqlite_path を切り替え、本番 DB と完全分離するように実装。

### Fixed
- 各種入力値のバリデーションを追加・強化（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。
- ポジションサイズ計算に関する丸め・スケーリングロジックで、lot_size 単位での端数処理と残余配分の安定化を実装。

### Notes / Known limitations
- apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、現在はその銘柄を無視して計算するためエクスポージャーが過少見積りされ得る。将来的に前日終値や取得原価でのフォールバックを検討（ソース内 TODO に記載）。
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map の導入を検討（ソース内 TODO）。
- ai.news_nlp:
  - 高可用性のため部分失敗時に既存スコアを保護する設計（コード絞り込みでの DELETE→INSERT）を取るが、完全なトランザクション保証は環境依存。API 利用回数やコストに注意。
- DuckDB に対する executemany の挙動に対する注意点がソース内に記載（params が空でないことを確認）。

### Security
- OpenAI API キーや各種外部トークンは環境変数経由で取得し、未設定時は明示的に ValueError を発生させることで安全性を確保。

---

（補足）
- 本 CHANGELOG はコードからの推測に基づき記載しています。実際のリリース履歴や日付はプロジェクトの公式履歴に合わせて適宜修正してください。