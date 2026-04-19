# Changelog

すべての重要な変更履歴を記録します。本ドキュメントは「Keep a Changelog」仕様に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 既知の問題 (Known issues)

## [Unreleased]
（今後の変更をここに記載してください）

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム KabuSys のコア機能を実装しました。

### Added
- 全体
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたローカル分析・監視データ保存の基盤を実装。
- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（data/paper_trading.db）を使用し MockBrokerClient を利用して本番 DB から完全分離。
    - ExecutionEngine の起動・停止制御は PID ファイルおよび data/stop_requested.flag によるフラグで行う。
    - 実行はデーモンスレッドで行い、停止フラグ検知時に安全に停止する実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず本番用 sqlite_path を使用して記録。
    - 停止は data/stop_requested.flag を検出して実行。
- 設定関連
  - config.py: Settings クラスを実装。環境変数の注入・検証を提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（OS 環境変数は保護）。
    - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID / モニタ閾値 / 環境判定等）。PAPER_FILL_MODE のバリデーションを実装（有効値: instant, partial, never, reject）。
  - config_setup.py: .env 作成・更新の対話式ウィザードを提供。
    - 主要項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を対話で設定して .env を書き出す機能を実装。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML があれば検証）を行う。
    - `--strict` モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築・サイズ計算
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート／上位選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター露出を計算し、上限を超えるセクターの候補を除外）。"unknown" セクターは上限除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは 1.0 でフォールバックし警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。lot_size（単元株）丸め、per-stock 上限、aggregate cap（available_cash）超過時のスケールダウンと残差配分ロジックを実装。手数料・スリッページを想定した cost_buffer を考慮。
- ユーティリティ
  - utils.logging_setup:
    - 統一ログ設定ユーティリティを実装。StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリの自動作成試行と失敗時のフォールバック処理あり。
  - utils.process_priority:
    - set_process_priority(level) により Windows / POSIX の差分を吸収して優先度を設定（best-effort）。AccessDenied 等を安全にハンドリング。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を最初の N コアにピン留め（best-effort）。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間の稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - デフォルトのパスは環境変数 `PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db。
    - 判定閾値（初期値）: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- 研究（リサーチ）
  - research.factor_research:
    - ファクター計算モジュールの骨格（モメンタム等）を追加。DuckDB の prices_daily / raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）や ATR/流動性指標等を算出する設計。関数インターフェースと定数を定義。モジュールは段階的に実装予定（モメンタム計算の下地が含まれる）。

### Changed
- ロギングと起動時挙動
  - 全起動スクリプトおよびユーティリティが共通の setup_logging を使用するように統一し、ログの一貫性を確保。
  - プロセス優先度は起動直後に High に設定する慣例を採用（run_execution / run_monitoring）。
- DB の取り扱い
  - 監視（monitoring）は環境に依らず本番用 sqlite_path を使用する方針を明示。
  - Execution は paper_trading モード時、paper 用 SQLite を使用して本番と分離。

### Fixed
- 環境値の頑健性向上
  - MONITOR_POLL_INTERVAL が不正（文字列、0、負数 など）の場合に警告を出しデフォルトにフォールバックする処理を追加（run_monitoring）。
  - .env パーサーの引用符内エスケープやコメント処理の改善により .env の読み込み精度を向上。
- ログディレクトリ作成失敗時の挙動を改善。ファイルハンドラ作成に失敗してもコンソール出力は継続される（Warn を出力）。

### Known issues / Notes
- research.factor_research は基礎実装が含まれるが、関数の一部（例: calc_momentum の実装詳細）はファイル末尾で途切れており、完全実装は今後の課題。
- position_sizing の価格フォールバック: price_map / open_prices に欠損（0.0）がある場合、現在は単純にスキップする挙動。前日終値や取得原価によるフォールバックを将来的に検討。
- apply_sector_cap: "unknown" セクターは上限チェック対象外（仕様）。必要に応じて取り扱いを変更する検討が必要。
- process_priority / cpu_affinity の設定は OS と権限に依存するため、AccessDenied 等で設定がスキップされる場合がある（ログに警告を出力）。

---

署名:
- 作成日: 2026-04-19
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートは開発・運用担当者が確認の上で確定してください。