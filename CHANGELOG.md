# Changelog

すべての重要な変更点をこのファイルに記載します。フォーマットは「Keep a Changelog」準拠です。  
バージョン番号はパッケージの __version__ と一致します。

全般ルール:
- 重要な新機能、変更、バグ修正、既知の制約・注意点を明記しています。
- 日付はリリース日を示します。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-12
初回公開リリース。以下の主要機能・実装を含みます。

### Added
- 基本アプリケーション構造
  - パッケージ初期化とバージョン情報 (kabusys.__version__ = "0.1.0") を追加。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite(DB) を使用する（data/paper_trading.db をデフォルト）。  
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、EngineConfig/ExecutionEngine の起動を実装。  
    - RiskManager のデフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値は broker.get_available_cash() を参照。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。プロセス優先度を起動時に設定。
- 設定管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート判定に .git または pyproject.toml を使用）。  
    - 読み込み優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。  
    - .env の行パーサを実装（export 形式、引用符付き値・バックスラッシュエスケープ、インラインコメント処理などに対応）。  
    - Settings クラスを導入し、各種環境変数（API トークン、DB パス、PID/KILL ファイルパス、閾値、env/log レベル、paper trading 設定など）を型付きプロパティとして提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行う。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を run モジュールで呼び出し、監視テーブルが存在することを保証（冪等）。
- ポートフォリオ構築機能（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で並べ上位 N を選定。タイブレークは signal_rank で解決。  
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全てが 0 の場合は等金額にフォールバック、警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を考慮して新規候補から除外するロジックを実装（unknown セクターは除外対象外）。sell_codes を当日売却予定として除外可能。  
    - calc_regime_multiplier: market レジームに基づく乗数 (bull/neutral/bear) を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した発注株数決定ロジックを実装。  
      - lot_size（単元）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料・スリッページ見積）考慮、残差処理による lot 単位での切り上げ配分を実装。
- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200 乖離を DuckDB SQL で計算。データ不足時は None を返す設計。
    - calc_volatility: ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新財務データの取得に ROW_NUMBER を利用）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて取得（LEAD を利用）。horizons の妥当性チェックを実装。  
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足・定数分散の場合には None を返す。  
    - factor_summary / rank: 基本統計量・ランク付けユーティリティを実装（外部ライブラリに依存しない実装）。
  - research.__init__ で zscore_normalize をエクスポート。
- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp:
    - raw_news → 銘柄ごとに記事集約、OpenAI（gpt-4o-mini）へバッチ送信、JSON 形式でセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ反映する処理を実装。  
    - バッチサイズ制御、トークン肥大対策（記事数・文字数上限）、429/5xx/ネットワーク断に対する指数バックオフリトライ、レスポンス検証とスコアクリップを実装。  
    - calc_news_window: ニュース収集ウィンドウ（JST 基準を UTC に変換）ユーティリティを提供。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、PASS/FAIL 判定（閾値付き）を標準出力へ出力。  
    - --from/--to/--db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数対応。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を実装し、Windows と POSIX 系（Linux/Mac/FreeBSD）での差分を吸収。アクセス権限不足時は警告でスキップするフェイルセーフを備える。

### Changed
- 設計上の注意点や挙動の明示
  - run_monitoring は monitoring 用に常に本番 sqlite_path を使用する（環境に依存しない監視データ収集）。  
  - run_execution は paper_trading 環境時に DB を分離し、実運用とテストを明確に区別。
  - config の .env パーサは慎重な引用符/エスケープ処理とコメント処理を行い、OS 環境変数の保護をサポート。
  - research と portfolio の関数群は純粋関数（DB 参照なし／メモリ計算）という設計方針を注記（副作用なし）。

### Fixed
- 不正な MONITOR_POLL_INTERVAL に対する耐性を実装（0 以下や非数値を指定した場合にデフォルトにフォールバックしログ出力）。
- .env ファイル読み込みでファイルアクセスエラーが発生した場合、警告を出して継続するように修正（例外伝播を防止）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY か関数引数で供給する仕様。キー未設定時は明示的にエラーを返す（誤ったキーの自動取得を防止）。

### Notes / Known limitations
- run_monitoring と run_execution は起動時に set_process_priority("high") を呼ぶため、権限によっては設定に失敗して警告となる（psutil.AccessDenied をハンドリング）。  
- apply_sector_cap は price が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的に価格フォールバック（前日終値など）を導入する予定（TODO コメントあり）。  
- calc_position_sizes の設計は現時点で lot_size を全銘柄共通としている。将来的には銘柄別単元情報を受け取る拡張を想定（TODO）。  
- DuckDB に対する executemany の制約や空パラメータ処理に注意（ai.news_nlp のコメントに言及）。  
- research モジュールは prices_daily / raw_financials のデータ品質に依存する。データ不足時は None を返す設計。
- ai/news_nlp 実装はファイル末尾で処理が途中で切れている可能性があるため、実装の完全性確認を推奨（本 CHANGELOG はコードベースの現状から推測して記載）。

---

今後のリリースでは以下を想定しています:
- エラーハンドリング強化・監視メトリクスの拡張
- portfolio の単元株・手数料モデルの高度化
- ai.news_nlp の安定化（部分失敗時のトランザクション制御やテストの追加）
- CI/テストケース追加とドキュメント強化

（以上）