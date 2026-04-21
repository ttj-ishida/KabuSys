# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

- リリース日付は ISO 形式 (YYYY-MM-DD) を使用しています。
- このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回リリース — 基本的な自動売買インフラ、設定管理、ポートフォリオ構築、ユーティリティ群を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを公開（__version__ = "0.1.0"）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env 自動読み込み機能を実装（.env、.env.local を OS 環境変数を保護しつつ読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

- 設定 / CLI
  - `kabusys.config.Settings` クラスを実装：環境変数から各種設定を取得するプロパティ群（DB パス、API トークン、環境種別、ログレベル、監視閾値など）。
  - 環境値検証（値の整合性チェック）を行うユーティリティを実装（無効な値は ValueError を送出）。
  - `kabusys.config_setup`：対話式ウィザードで .env を作成／更新する CLI を提供。秘密値はマスク表示、保存時に注意文を出力。
  - `kabusys.validate_config`：.env と config/*.yaml の存在／基本整合性を検証する CLI を提供。--strict オプションで警告も失敗扱いに可能。

- 実行 / 監視
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドとして実行。停止フラグ（data/stop_requested.flag）が存在すると安全停止。
    - PID ファイル書き出しパスをサポート（data/execution.pid を既定値）。
    - RiskManager に初期設定を与えるデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit 等）。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ検知でループを終了。KeyboardInterrupt による終了も適切にハンドリング。

- データベース / 分析
  - DuckDB / SQLite に接続するコードを統合。duckdb_path / sqlite_path の設定プロパティを提供。

- ポートフォリオ構築（pure functions）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選出（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック、警告出力）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づき、新規候補を除外するセクター上限ロジックを実装（unknown セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未定義レジームは警告の上 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score をサポート）。
      - risk_based: 許容リスク（risk_pct）と stop_loss_pct に基づく株数算出。
      - equal/score: ウェイトと max_utilization に基づく割当。
      - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）を適用。
      - aggregate cap: 全銘柄合計コストが available_cash を超える場合はスケーリングしてリマインダ処理で lot_size 単位の追加割当を行う。
      - cost_buffer によりスリッページ／手数料を保守的に見積もる。

- ツール / レポート
  - `kabusys.tools.paper_verification_report`：Paper Trading 検証レポートを生成するスクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - 基準値（稼働率 >= 99% 等）はスクリプト内定義で調整可能。
    - P95 の算出ロジックとデータ不足時の N/A ハンドリングを実装。

- ユーティリティ
  - kabusys.utils.logging_setup
    - 統一的ログ設定ユーティリティを実装（StreamHandler: stdout、TimedRotatingFileHandler: 日次ローテーション、30 日保持）。
    - LOG_DIR 環境変数、引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップして警告（stderr または logger）を出力。
    - 既存ハンドラは再設定前に flush/close して重複設定を防止。
  - kabusys.utils.process_priority
    - cross-platform のプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定を実装。
    - psutil を使い、権限不足や未対応環境では警告を出してスキップする安全設計。

- 研究モジュール（research）
  - kabusys.research.factor_research の基本骨子を実装（モメンタム、MA、ATR、出来高等の計算方針と定数を定義）。DuckDB を用いて prices_daily 等を参照する設計を採用（calc_momentum 等の実装が含まれるが、一部ファイルが未完の可能性あり）。

### 変更 (Changed)
- （初回リリースのため特記事項なし）

### 修正 (Fixed)
- （初回リリースのため特記事項なし）

### 既知の制約・注意点 (Notes / TODOs)
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少推定される懸念あり。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing: 現在は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map に拡張する TODO コメントあり。
- research.factor_research: ファイル末尾が未完の箇所がある（実装途中の可能性）。本リリースでは主要ロジックのスケルトンと定数を提供。
- .env の自動読み込みでは OS の既存環境変数を保護する実装。テスト等で自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- logging_setup: ログディレクトリの作成に失敗した場合はコンソール出力にフォールバックするが、その際に stderr に直接警告を出す実装がある点に注意。
- process_priority / set_cpu_affinity: 権限不足や非対応 OS では警告を出して処理をスキップするため、実行環境によっては期待どおりに優先度や affinity が設定されない場合がある。

### セキュリティ / 運用上の注意
- .env は絶対に Git にコミットしない旨を config_setup の README コメントに明記。
- validate_config の live 環境向けチェックでは、LINE 通知未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性を警告（本番運用での注意喚起）。

---

今後の改善例（非網羅）
- factor_research の完成（ファクター出力を安定化）。
- 銘柄ごとの lot_size 管理、price フォールバックロジックの実装。
- 実運用でのメトリクス監視、アラート送信（LINE 連携）の追加強化。
- ユニットテストの追加と CI 自動化。