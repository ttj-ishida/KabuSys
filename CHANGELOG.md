# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
（注: 以下は提示されたコードベースの内容から実装・挙動を推測して作成しています。）

## [0.1.0] - 2026-04-17

### Added
- 初期リリース（ライブラリ/アプリケーションの基本コンポーネントを追加）。
- 基本メタ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0 以下はデフォルトにフォールバック。
    - 停止フラグファイル `data/stop_requested.flag` を検知してループを終了。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用。
    - DuckDB 接続を使用。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを使用）。
  - run_execution.py
    - ExecutionEngine（取引エンジン）を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を利用し、Paper Trading 用 DB（`data/paper_trading.db` など）に記録して本番 DB と分離。
    - 停止フラグ `data/stop_requested.flag` と PID 管理 `data/execution.pid` に対応。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.Settings クラスを追加し、環境変数／.env ファイルから設定を読み込む仕組みを実装。
    - 自動 .env ロード（プロジェクトルート検出：.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 多数のプロパティを提供（J-Quants、kabu API、LINE API、DB パス、監視閾値、環境種別等）。
    - 必須環境変数チェック（`_require`）を実装（未設定時は ValueError）。
    - `PAPER_FILL_MODE`（instant|partial|never|reject）等の値検証を実施。
- 監視用 DB 初期化ユーティリティ呼び出し（monitoring_db.init_monitoring_db を run_* スクリプトで利用）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - コマンドライン引数で期間指定（--from, --to）と DB パス指定（--db）に対応。
    - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数など。
    - Pass/Fail 基準値を定義（稼働率 99% 等）。出力は人が読みやすいテキストレポート。
- ポートフォリオ構築（純関数モジュール）
  - portfolio.portfolio_builder
    - select_candidates（スコア順で候補選択）
    - calc_equal_weights（等分配）
    - calc_score_weights（スコア正規化、スコア合計が 0 の場合は等分配にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中上限を適用して候補を除外）
    - calc_regime_multiplier（レジームに応じた投下資金乗数を返す。bull/neutral/bear をサポート）
  - portfolio.position_sizing
    - calc_position_sizes（発注株数計算。allocation_method に risk_based/equal/score をサポート）
    - aggregate cap（合計投下額が利用可能現金を超える場合のスケーリングと lot_size 単位での端数処理）を実装。
- 研究（research）モジュール
  - research.factor_research
    - calc_momentum（1/3/6ヶ月リターン、MA200 乖離）
    - calc_volatility（ATR20、相対ATR、平均売買代金、出来高比）
    - calc_value（PER、ROE を raw_financials と prices_daily から算出）
    - DuckDB を用いた SQL ベースの計算（prices_daily / raw_financials を参照）
  - research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターンを LEAD で取得）
    - calc_ic（スピアマンランク相関（IC）を計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理）
  - research.__init__ で API を公開（zscore_normalize を data.stats から再エクスポート）
- AI ニュース NLP（ニュースのセンチメントスコアリング）
  - ai.news_nlp
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを取得して ai_scores に書き込む設計を追加。
    - バッチ処理、トークン爆発対策（記事数／文字数制限）、エラーハンドリング（429/ネットワーク/5xx のリトライ）など設計方針を備える。
    - OpenAI API キー未設定時は ValueError を発生させるチェックを実装。
    - 出力は JSON の厳密検証、スコアを ±1.0 でクリップする方針。
    - （注: 提示コードは途中で切れているため、一部実装は継続・完成が必要）
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level)（Windows / POSIX を吸収して優先度を設定。権限不足や未対応 OS はワーニングでスキップ）
    - set_cpu_affinity(cpu_count)（指定コア数へピンニング。権限不足はワーニングでスキップ）
    - psutil ベースでの実装

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- OpenAI API キーなど機密情報取り扱いに関する注意をコード中で明示（環境変数経由）。.env の自動ロードはプロジェクトルート検出に依存し、無効化可能。

## 重要な運用／移行メモ（Usage / Migration notes）
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token で必須）
  - KABU_API_PASSWORD（Settings.kabu_api_password で必須）
  - OpenAI を利用する場合は OPENAI_API_KEY が必要（ai.news_nlp.score_news）。
- DB パス（デフォルト）
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - 本番監視 SQLite: data/monitoring.db（SQLITE_PATH）
  - Paper トレード SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- 環境変数の自動ロード
  - プロジェクトルートに .env または .env.local がある場合、自動で読み込まれる（OS 環境変数優先）。
  - 自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Paper Trading の分離
  - run_execution は Paper Trading 時に別 DB を使用し、本番 DB と完全分離する設計。
- 停止制御
  - run_monitoring / run_execution は共にプロジェクト配下の data/stop_requested.flag を監視し、フラグ検知で安全終了する。
- ログレベル・環境種別
  - Settings.env は "development" | "paper_trading" | "live" のいずれかを期待。無効値は ValueError。
  - Settings.log_level も検証あり（DEBUG/INFO/...）。
- その他
  - PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかでないとエラーになる。
  - process priority / cpu affinity の設定は権限不足や未対応 OS では無視され、ワーニングが出力される。

---

備考: 上記 CHANGELOG は提供されたソースコードの構造とドキュメント文字列から推測して作成しています。実際のリリースノートとして使用する場合は、コミット差分・リリース目的に応じて調整してください。