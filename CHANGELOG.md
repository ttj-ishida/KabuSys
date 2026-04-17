# Changelog

すべての注記は Keep a Changelog 準拠の形式で記載しています。  
このファイルは、コードベース（src/ 以下）から推測できる機能追加・仕様・互換性注意点をまとめたものです。

フォーマット:
- Added: 新規機能・主要コンポーネントの追加
- Changed: 既存仕様の重要な変更・挙動の明示
- Fixed: バグ修正や堅牢化
- Security / Deprecated / Removed: 必要に応じて記載

## [Unreleased]

（将来の変更をここに記載）

---

## [0.1.0] - 2026-04-17

初回リリース（コードベースの現状から推測してまとめたリリースノート）。

### Added
- 全体
  - KabuSys 初期実装を追加。パッケージバージョンは `__version__ = "0.1.0"` に設定。
  - DuckDB および SQLite を併用するデータレイヤ設計を採用（prices / raw_financials 等は DuckDB、監視・発注ログ等は SQLite 想定）。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動・監視する制御を実装。
    - 停止用フラグファイル（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を導入。

  - run_monitoring: SystemMonitor のポーリング起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - Monitoring は KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用する（設計上の意図を明示）。
    - 停止フラグファイル（data/stop_requested.flag）検出でループ終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。

- 設定管理
  - config.Settings: 環境変数・.env ファイルの読み込み・バリデーションを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。CWD に依存しない実装。
    - .env のパースは以下に対応:
      - コメント行・空行無視、`export KEY=val` 形式、シングル・ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理。
    - 自動ロード順: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（上書きされない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / env 判定 等）を提供。
    - PAPER_FILL_MODE の値検証（有効値: "instant", "partial", "never", "reject"）。不正値は ValueError。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順、同点時は signal_rank のタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。スコア全体が 0 の場合は等分配にフォールバックし警告。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを実装。既存保有のセクター比率が max_sector_pct を超える場合に当該セクターの新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に基づく投下資金乗数を提供。未知レジームは警告のうえ 1.0 にフォールバック。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based","equal","score") に対応した株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的見積り、余剰資金による残差分配ロジックを実装。

- 研究・リサーチ
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value を追加。DuckDB 上の prices_daily / raw_financials に対する SQL ベースのファクター計算を実装（MA200, ATR20, turnover 等）。
    - スキャン範囲バッファや欠損行の扱い（ウィンドウ内行数不足で None を返す）を考慮。

  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算を実装。horizons に対する入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算を実装（有効レコード < 3 の場合 None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）・基本統計の計算を提供。
    - pandas 等外部ライブラリに依存せず標準ライブラリのみで実装。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算・判定（既定閾値あり）。
    - DB が存在しない場合のメッセージ、SQLite の OperationalError を考慮したフェイルセーフ処理を実装。
    - P95 の計算ロジック・日付フィルタを提供。コマンドライン引数で期間指定可能。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI API（既定: gpt-4o-mini）でスコアリングし、ai_scores に結果を書き込む設計を追加。
    - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を正確に計算する util calc_news_window。
    - バッチ（最大 20 銘柄）送信、JSON Mode 出力厳格検証、429/5xx/ネットワーク系のリトライ（指数バックオフ）、スコアの ±1.0 クリップ等を想定した堅牢化設計。
    - API キーが未設定の場合は ValueError を投げる旨を明示。

- ユーティリティ
  - utils.process_priority:
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を実装。
    - set_cpu_affinity による CPU 固定機能を実装（引数検証・権限失敗時は警告してスキップ）。
    - 権限不足や未サポート環境への耐性処理を含む。

### Changed
- 環境変数ロードの挙動を明確化
  - 自動ロード順序を OS 環境変数 > .env.local > .env とし、OS 環境変数は上書きされない（protected）。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD を追加して自動ロードを抑止可能。
- run_monitoring の挙動
  - Monitoring は KABUSYS_ENV によらず settings.sqlite_path（本番想定）を使用する仕様を明示。運用時に本番 DB を参照する点に注意。

### Fixed / Hardened
- .env パーサ
  - クォート内のバックスラッシュエスケープ処理、export 接頭辞対応、インラインコメントの取り扱いなどを改善し、.env の実運用での堅牢性を向上。
- 各種 SQL クエリ呼び出しでの例外（sqlite3.OperationalError）をハンドリングすることでツール類（paper_verification_report 等）の堅牢性を向上。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし warning を出すようにしてゼロ除算や不正重みを防止。

### Notes / Breaking changes / 注意点
- Monitoring の DB 選択
  - run_monitoring は KABUSYS_ENV にかかわらず `sqlite_path` を使用します。paper_trading 環境であっても監視 DB は本番と同一になるため、テスト用に監視を分離したい場合は設定やスクリプトの修正が必要です。
- Paper Trading 完全分離
  - Execution 起動時は settings.is_paper によって paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用する設計のため、本番 DB への誤送信リスクは低減されています。Paper 環境と本番で DB を分けて運用することを推奨します。
- OpenAI API
  - ai.news_nlp は OpenAI API キー必須・外部 API に依存するモジュールです。API 呼び出しでの課金・レート制限に注意してください。また出力は厳密な JSON を要求します。
- 権限関連
  - process priority / cpu affinity の設定は権限不足で失敗する可能性があります。失敗時はログで警告が出て処理は継続します。

---

今後の改善候補（コード内 TODO からの抜粋）
- position_sizing: 銘柄別 lot_size（単元）対応や前日終値等の価格フォールバック導入。
- ai.news_nlp: 大量ニュース時のトークン最適化、部分失敗時のより精細なロールバック戦略。
- Monitoring/SystemMonitor 側の詳細な記録・アラート出力の強化。

（以上）