# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠します。
項目は重要なユーザー向けの変更点・新機能・修正をコード内容から推測して記載しています。

## [Unreleased]
### Added
- ドキュメントとユーティリティ
  - プロジェクト全体のバージョンを管理する `__version__ = "0.1.0"` を導入。
- 開発・運用支援ツール
  - 対話式の環境設定ウィザードを追加（`kabusys.config_setup`）。
    - `.env` の新規作成・更新を対話で支援。秘密項目はマスク表示される。
    - 出力ファイルのテンプレートや項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を含む。
  - 設定検証 CLI を追加（`kabusys.validate_config`）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パースチェック（PyYAML がない場合は警告してスキップ）。
    - `--strict` オプションで警告を失敗扱いにできる。
  - Paper Trading 検証レポート生成スクリプトを追加（`kabusys.tools.paper_verification_report`）。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db`）から、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを算出し、PASS/FAIL 判定を出力する。
    - デフォルトの合格基準閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
- 実行系・監視系スクリプト
  - 実行エンジン起動スクリプトを追加（`kabusys.run_execution`）。
    - 起動時にプロセス優先度を High に設定。
    - `KABUSYS_ENV=paper_trading` の場合は Paper 専用 SQLite（`data/paper_trading.db` デフォルト）と MockBroker を使い、本番 DB と分離。
    - BrokerClientFactory を通してブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行管理（別スレッドでエンジンを起動し、停止フラグを監視して停止）。
    - PID ファイル出力、停止フラグ（data/stop_requested.flag）により安全に停止可能。
  - 監視ループ起動スクリプトを追加（`kabusys.run_monitoring`）。
    - 起動時にプロセス優先度を High に設定。
    - 環境にかかわらず監視は本番の `sqlite_path` を使用して監視データを格納。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で設定可能。無効値は警告を出してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了、`KeyboardInterrupt` もハンドリングしてクリーンに終了。
- 設定管理（`kabusys.config`）
  - 自動 .env 読込ロジックを追加（プロジェクトルートは .git または pyproject.toml で検索）。
    - 読込順は OS 環境 > .env.local > .env。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用。
  - .env の1行パーサは以下に対応:
    - `export KEY=val` 形式、シングル/ダブルクォート（バックスラッシュエスケープ対応）、行中コメント（クォートなしのときは '#' の前に空白がある場合にコメント扱い）等。
  - Settings クラスでアプリ設定をプロパティとして提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode` 等）。
    - `paper_fill_mode` の有効値チェック（"instant", "partial", "never", "reject"）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性チェック。
    - Kill Switch 関連設定（`kill_flag_path`, `kill_flag_clear_on_start`）を実装。
- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（`kabusys.utils.logging_setup.setup_logging`）。
    - stdout StreamHandler と日次ローテートファイルハンドラ（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順は: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
  - プロセス優先度 / CPU affinity ユーティリティを追加（`kabusys.utils.process_priority`）。
    - Windows / POSIX の差分を吸収して `set_process_priority("high"|"normal"|"low")` を提供（アクセス権限エラー等は警告でスキップ）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアに固定する機能（実行環境のサポートに依存）。
- ポートフォリオ構築関連（kabusys.portfolio）
  - 候補選定・重み計算（`portfolio_builder`）
    - `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - `calc_equal_weights`（等金額配分）。
    - `calc_score_weights`（スコア正規化、全スコアが 0 の場合は等金額にフォールバック）。
  - セクター上限・レジーム乗数（`risk_adjustment`）
    - `apply_sector_cap`：既存保有のセクター別エクスポージャー計算に基づき、上限超過セクターの新規候補を除外（unknown セクターは無視）。
    - `calc_regime_multiplier`：レジームに応じた投下資金乗数（"bull":1.0、"neutral":0.7、"bear":0.3。未知レジームは 1.0 でフォールバック）。
  - 株数計算（`position_sizing`）
    - `calc_position_sizes`：allocation_method（"risk_based","equal","score"）に対応。単元株（lot_size）で丸め、1銘柄上限・総投下上限・コストバッファを考慮したスケーリングを実装。aggregate cap 超過時はスケールダウン後、残余を fractional remainder に基づき lot 単位で再配分。
- 研究モジュール（`kabusys.research.factor_research`）
  - モメンタム / ボラティリティ等のファクター計算の骨格と定数を実装（MA200、1/3/6 ヶ月リターン、ATR、20 日出来高平均等）。
  - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
  - （注意）`calc_momentum` 実装が途中で切れている箇所があり、未完成部分が存在する（Work in progress）。
  
### Changed
- なし（新規追加主体のリリース想定）

### Fixed
- なし（この差分からは特定のバグ修正は読み取れません）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## [0.1.0] - 2026-04-21
初回公開想定のまとめリリース。上記の機能群（実行/監視スクリプト、設定管理・ウィザード/検証、ロギング・プロセス管理ユーティリティ、ポートフォリオ構築関数群、Paper Trading 検証ツール、研究用ファクターモジュールの骨格）を含む。

備考（運用上の注意）
- 監視ループは監視用の SQLite パス（Settings.sqlite_path）を必ず使用します。実行エンジンは環境により paper_trading 用 DB を分離します。
- Kill Switch / stop flag が存在する場合、起動やループ挙動に影響します（stop flag 検知で安全に停止）。
- .env 自動読み込みはプロジェクトルートの検出に依存します。テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `calc_momentum` 等、研究モジュールの一部は未完成の箇所があるため、使用時は注意してください。

もし詳細なリリース日や既知の問題一覧（Known Issues）などを追加したい場合は、その旨を教えてください。コードの別ファイル（未提示の execution engine / monitoring DB schema / broker 実装等）も提供いただければ、より正確な変更履歴を作成できます。