# Changelog

すべての重要な変更をここに記載します。フォーマットは Keep a Changelog に準拠します。  
リリース日はソースコードの状態に基づく推測です。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報を追加
  - kabusys.__version__ を "0.1.0" に設定。

- 実行系起動スクリプト
  - run_execution.py を追加。
    - ExecutionEngine の起動フローを実装（Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ監視など）。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番データと完全分離。
    - BrokerClientFactory 経由で MockBrokerClient を利用可能（KABUSYS_ENV=paper_trading 時の想定）。
    - ExecutionEngine の PID ファイル管理、停止フラグ検出による安全停止処理を実装。

- 監視系起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor の初期化とポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、負値や 0 は無効扱いしてデフォルトにフォールバック）。
    - 監視は実行環境に関わらず本番用 sqlite_path を使用する挙動を明示。
    - プロセス優先度を起動時に "high" に設定。

- 設定管理
  - config.py を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動ロード機能（OS 環境変数を保護して .env/.env.local を順序に応じて読み込む）。
    - .env 行パーサの強化: `export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントルールをサポート。
    - 環境変数未設定時に ValueError を送出する _require()、各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、env 判定、paper_trading 向け設定等）を提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加。
    - paper_trading の SQLite DB から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計して人間向けテキストレポートを出力。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
    - P95 計算や欠損データを考慮した堅牢なクエリ実装。
    - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）と Pass/Fail 判定ロジック。

- ポートフォリオ構築ユーティリティ群（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、同点時 tie-breaker に signal_rank を使用）。
    - 等金額配分(calc_equal_weights) とスコア加重配分(calc_score_weights)。全スコアが 0 の場合は等配分へフォールバック（WARNING ログ）。
  - portfolio/risk_adjustment.py
    - 同一セクター集中制限 apply_sector_cap（売却予定銘柄を除外してエクスポージャー計算、"unknown" セクターは上限不適用）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing の主要ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。

- プロセス制御ユーティリティ
  - utils/process_priority.py を追加。
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）。
    - CPU affinity を指定する set_cpu_affinity 実装。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- リサーチ / ファクター計算
  - research/factor_research.py を追加。
    - DuckDB を使ったモメンタム（1/3/6 ヶ月）、MA200乖離、ATR20、平均売買代金、出来高変化率、PER/ROE 等のファクター計算関数（calc_momentum / calc_volatility / calc_value）。
    - SQL ベースでの効率的実装と欠損値ハンドリング。
  - research/feature_exploration.py を追加。
    - 将来リターン計算（複数ホライズンを一括取得）、Spearman ランク相関による IC 計算(calc_ic)、値のランク変換(rank)、ファクター統計サマリー(factor_summary) を実装。
    - 外部依存を避けた純粋 Python 実装。
  - research/__init__.py で主要 API をエクスポート。

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py を追加。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出、ai_scores テーブルへ書き込み。
    - JST ウィンドウ（前日 15:00 〜 当日 08:30）を UTC に変換して対象記事を選別する calc_news_window 実装。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化防止（記事数/文字長制限）、429/5xx/ネットワーク断に対する指数バックオフ、レスポンスの厳密な JSON バリデーション、スコアを ±1.0 にクリップする安全設計を採用。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。

### Changed
- DB 接続方針の明確化
  - 監視(run_monitoring)は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様とした（監視データは本番ターゲットで管理する意図）。
  - 実行(run_execution)は paper_trading に対して専用 DB を使用し、本番 DB と分離。

- .env 読み込みの既定値/保護ルール
  - OS 環境変数は保護され、.env.local は .env の上書きとして読み込まれる順序を採用。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。

- ロギング・例外ハンドリングの改善
  - run_monitoring と run_execution で起動時にプロセス優先度を設定し、ループ内例外をログに残して次回ポーリングに継続する設計に変更。
  - process_priority の失敗ケースは警告ログで抑制。

### Fixed
- 環境変数/設定バリデーションの整備
  - PAPER_FILL_MODE の値チェックを追加（instant/partial/never/reject のみ有効）。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを追加して誤設定時に早期にエラーを出すようにした。

### Security
- 特記事項なし

### Notes / Known limitations
- ai/news_nlp.py は API 呼び出し・DB 書き込みの堅牢なフローを設計しているが、外部 API（OpenAI）との具体的な運用上のチューニングやレート制御は実運用での調整が必要です。
- position_sizing の lot_size はグローバル固定（デフォルト 100）。将来的に銘柄別単元対応を検討する旨の TODO コメントあり。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊な配置の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や明示的な環境変数設定を推奨。

---

今後のリリースではユニットテスト、ドキュメント（API 仕様・設定例）、および ai/news_nlp の実運用向け強化（リトライポリシーの詳細化、監査ログ等）を追加予定です。