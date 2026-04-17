# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日の日付はコードベースのスナップショット作成日 (2026-04-17) を使用しています。

## [Unreleased]

### Added
- なし（次回リリースへ向けた作業中）

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-17

初回リリース。コードベースから推測できる主要な機能・設計・修正点をまとめます。

### Added
- コア構成
  - パッケージ識別子とバージョンを追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数駆動の設定管理を実装。
    - 自動 .env/.env.local 読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 必須変数チェック (`_require`) と値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - データベースパスや各種フラグのパス定義（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
- 実行系（Execution）
  - run_execution スクリプトを追加。
    - プロセス開始時にプロセス優先度を設定（高優先度に設定）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成（Paper 環境では Mock を利用）。
    - ExecutionEngine の組み立てと起動（EngineConfig, Reconciler, RiskManager, OrderManager, OrderRepository の組合せ）。
    - エンジンを別スレッドで稼働し、 stop フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行用 PID ファイル管理（data/execution.pid）。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- 監視系（Monitoring）
  - run_monitoring スクリプトを追加。
    - SystemMonitor の初期化、SQLite/DuckDB 接続、監視ポーリングループの実装。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグでループ終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（明確な分離仕様）。
- ポートフォリオ構築（Portfolio）
  - portfolio モジュールを追加。
    - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全0時は等配分へフォールバック。
    - risk_adjustment: セクター上限適用（apply_sector_cap：既存保有を考慮し、unknown セクターは制限対象外）、市場レジーム乗数（calc_regime_multiplier：bull/neutral/bearマッピング、未知レジームは警告して1.0フォールバック）。
    - position_sizing: 発注株数計算（calc_position_sizes）。
      - allocation_method（risk_based / equal / score）をサポート。
      - 単元株（lot_size）、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリング。
      - スケーリング時の残差配分アルゴリズム（fractional remainder に基づく lot 単位での追加配分）を実装。
      - 価格欠損時のスキップや上限 (_max_per_stock) を考慮。
- リサーチ（Research）
  - research モジュールを追加（duckdb を利用）。
    - factor_research:
      - モメンタム（calc_momentum）：1/3/6 か月リターン、200日移動平均乖離率を計算。
      - ボラティリティ（calc_volatility）：ATR20、相対ATR、20日平均売買代金、出来高比率を計算。
      - バリュー（calc_value）：raw_financials から EPS/ROE を参照して PER/ROE を計算。
      - DuckDB 上でのウィンドウ関数を活用した実装。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）: LEAD を用いて任意ホライズンの将来リターンを算出。horizons のバリデーションあり。
      - IC（calc_ic）: スピアマン（ランク）ベースの Information Coefficient を計算。records の結合・フィルタリング・ties の扱いを実装。
      - ランク付けユーティリティ（rank）とファクター統計サマリ（factor_summary）を提供。
    - research.__init__ で zscore_normalize（kabusys.data.stats）を再エクスポート。
- AI / ニュース NLP（ai.news_nlp）
  - ニュース記事を OpenAI API（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込むための骨格を実装。
    - ニュースウィンドウ計算（JST ベース → UTC へ変換）。
    - 記事集約、銘柄ごとの最大記事数/文字数トリム、バッチ送信（最大 20 銘柄/コール）、429/5xx/タイムアウトに対する指数バックオフリトライ、レスポンスバリデーション、スコア ±1.0 クリップ、部分置換での DB 更新方針等を設計。
    - 実装の一部（関数内部）が未終了／途中で切れている箇所が存在（追加実装が必要）。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成コマンドラインツールを実装。
    - 指標：稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）などを算出し、PASS/FAIL 判定を行う基準値を設定（稼働率 >= 99%、fill >= 90% 等）。
    - P95 計算、日付フィルタ、DB ファイル存在チェック、テーブルが存在しない場合のフォールバックを備える。
- DB 関連
  - DuckDB と SQLite を併用する設計を明確化。
    - DuckDB は時系列価格やファクタ計算向けの大規模データ処理用に接続。
    - SQLite は監視・実行ログ等の軽量ストレージ（paper_trading 用に分離可能）。
  - monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority（Windows / POSIX 対応, psutil ベース）を追加。権限不足等の例外は警告してスキップ。
    - set_cpu_affinity（最初の N コアに固定）を追加。バリデーションと例外ハンドリングを含む。
  - .env パーサー（config._parse_env_line）:
    - export KEY=val 形式、シングル/ダブルクォート・バックスラッシュエスケープ、インラインコメントの取り扱い、未設定行やコメント行の無視等をサポート。
    - _load_env_file による override/protected ロジックで OS 環境変数の上書きを制御。
- ロギング・堅牢化
  - 多くの場所で logging を用いた情報・デバッグ・警告・例外ログ出力を追加。
  - run_monitoring / run_execution で停止フラグ検出や KeyboardInterrupt に対するクリーンアップ処理を実装。
  - 無効な環境値やパラメータに対して明確な例外（ValueError）や警告で対処。

### Changed
- 初版のため、変更履歴はなし（以降のバージョンで差分を記録）。

### Fixed
- 初版のため、修正履歴はなし。

### Notes / Known issues
- ai/news_nlp モジュールの score_news 関数が途中で切れている（コード断片が末尾で途切れている）。実運用前に残りのロジック（記事フェッチ・API 呼び出し・DB 書込等）の完成が必要。
- portfolio.position_sizing の注記:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積になる可能性がある旨の TODO コメントあり。将来的なフォールバック価格ロジックを検討中。
- 一部の TODO や拡張メモがソース内に残されている（銘柄別 lot_size 管理など）。
- 外部依存:
  - psutil、duckdb、openai ライブラリが必要。CI/デプロイ環境で明示的に依存関係を用意すること。

---

作成方針・補足:
- 本 CHANGELOG はコードの実装内容から推測して作成しています。実際のコミット履歴や issue トラッキングがあれば、より正確なリリースノートに反映できます。必要であれば、コミットログベースの詳細な CHANGELOG 作成を支援します。