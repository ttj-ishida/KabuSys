# Changelog

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本文は与えられたコードベースの内容から推測して作成しています（ファイル内コメントや実装から機能・挙動を抽出）。

## [Unreleased]

- 小さな改善・リファクタやドキュメント整備を予定。

---

## [0.1.0] - 2026-04-17

初回リリース（推定）。主要な機能群と実装上の振る舞いを含みます。

### Added
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動するランチャーを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）および MockBrokerClient を利用して本番 DB と完全に分離。  
    - スレッドでエンジンを実行し、data/stop_requested.flag による外部停止をサポート。プロセス PID ファイル(data/execution.pid) に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番の sqlite_path を使用（設計上の意図）。停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - config.py: 環境変数/.env 管理モジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づき .env/.env.local の自動ロードを実装（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
    - 値検証機能（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の妥当性チェック）と各種パス/properties を提供。  
    - PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID/kill flag 関連設定などをサポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア重み計算（calc_equal_weights / calc_score_weights）。
  - portfolio.position_sizing: 発注株数・投下資金制約・単元株丸め・aggregate cap に基づくスケーリング（calc_position_sizes）。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。

- リサーチ / ファクター算出
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を利用、prices_daily / raw_financials を参照）。  
    - mom_1m/3m/6m、MA200 乖離、ATR20、平均売買代金などを算出。
  - research.feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic）・ランク関数、ファクター統計サマリ（factor_summary）。

- ニュース NLP（AI スコアリング）
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄別スコアを ai_scores テーブルへ書き込むためのモジュールを追加。  
    - タイムウィンドウの計算、記事集約（1 銘柄あたり最大記事数／文字数でトリム）、バッチ送信（最大 20 銘柄）、429/5xx/ネットワークエラー等に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時でも既存スコア保護のためコード絞り込みでの置換ロジック等を設計。

- ユーティリティ
  - utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX 対応）、CPU affinity の設定ユーティリティを追加。起動時に優先度を "high" に設定する呼び出しが run_* スクリプトで行われる。
  - monitoring.monitoring_db（参照のみ）を初期化する init_monitoring_db の利用により監視テーブルを整備。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI ツールを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定（デフォルト閾値あり）。  
    - --from/--to/--db オプションをサポート。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- DB 周りの振る舞い
  - 監視系（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計（環境分離の方針は実行系と異なる点に注意）。  
  - run_execution は paper_trading 環境時に専用 DB を使用して本番と分離（安全設計）。

- 堅牢性・ロバストネス
  - 各種クエリや集計処理でデータ不足時に None を返す・例外を捕捉してフォールバックする実装になっている（tools.paper_verification_report 等）。  
  - run_monitoring のループ内部で monitor.check_once() の例外を捕捉し、次回ポーリングまで継続するフェイルセーフ設計。

- 環境ファイルパーサ
  - config._parse_env_line にてクォート付き値やエスケープ、インラインコメント処理に対応。export KEY=val 形式もサポート。

### Fixed
- 環境値の妥当性チェックを追加（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証）し、不正な値での起動を早期に検知可能にした。
- position_sizing での rounding / lot_size 単位処理や aggregate cap スケーリングでの端数分配アルゴリズムを実装（再現性確保のため安定ソート）。

### Documentation / Comments
- 各モジュールに設計方針・参照ドキュメント・注意点（例: レジーム時の振る舞いや将来拡張 TODO）をコメントとして明記。これにより将来の拡張や保守が容易に。

### Known issues / Notes
- ai.news_nlp モジュールは設計が詳細に書かれているものの、与えられたスナップショットでは一部実装（記事取得関数や後続処理）が切れている可能性がある（スナップショット末尾で途切れた箇所あり）。実運用前に _fetch_articles 等の実装と統合テストが必要。  
- portfolio.risk_adjustment.apply_sector_cap に注記あり: price が欠損（0.0）の場合に exposure が過少見積りされ得る旨の TODO コメントあり。将来的に価格フォールバックの実装を推奨。
- DuckDB executemany に関する注意（空 params を渡さない等）がコメントとして残っているため、DB バルク書き込み時は注意が必要。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得する仕様。未設定時は ValueError を送出して明示的に失敗するため、キー漏洩に注意して環境管理を行うこと。

---

以前のバージョンが存在する場合は対応して差分を記載してください。必要であれば、各ファイルごとの変更点（行単位）やリリース手順、移行ガイドの作成も支援します。