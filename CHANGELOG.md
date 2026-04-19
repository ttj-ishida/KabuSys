CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠しています。  
初期リリース (v0.1.0) の変更点をコードベースから推測して日本語でまとめています。

[v0.1.0] - 2026-04-19
--------------------

Added
- 全体
  - プロジェクト初期バージョンを追加。パッケージ名: kabusys、バージョン: 0.1.0。
  - package エントリポイント・モジュール構成を整備（monitoring / execution / portfolio / utils / tools / research 等を含む）。

- 設定管理
  - Settings クラスを実装し、環境変数から各種設定値を提供（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH 等）。
  - .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を OS 環境変数を保護しつつ読み込み）。
  - 高度な .env パーサーを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。

- 設定ツール / 検証ツール
  - 対話式環境設定ウィザード (kabusys.config_setup) を提供。.env の初期作成・更新を支援。
  - validate_config CLI を提供。必須環境変数・KABUSYS_ENV の値・ログレベル・DB パス・config/*.yaml の存在および YAML パース検証（PyYAML がある場合）・本番環境向けガードをチェック可能。--strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視用 DB は環境にかかわらず production sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) による安全な終了処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（data/paper_trading.db）に完全分離して記録。
    - 起動時に停止フラグが立っている場合は起動を中止する安全ガード。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検出時に engine.stop() でシャットダウンするループ制御。

- データベース / 永続化
  - DuckDB / SQLite 接続を利用する設計を採用（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
  - 監視用テーブル作成を保証するための init_monitoring_db 呼び出しを統合（冪等）。

- ロギング・プロセス管理
  - 共通ロギング初期化ユーティリティ (kabusys.utils.logging_setup) を追加。
    - stdout 出力の StreamHandler と 日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。
    - ログディレクトリ自動作成・作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - process_priority ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX を吸収した優先度設定（high/normal/low）と CPU affinity 設定機能を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフあり。
  - 起動スクリプトは最初にプロセス優先度を "high" に設定するようになっている。

- ポートフォリオ構築（純関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順・タイブレークは signal_rank でソートして上位を返す。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア比率の重み計算。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存保有や売却予定銘柄を考慮してセクター別エクスポージャーを算出し、上限を超えるセクターの候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックして警告。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応した株数決定ロジック（単元株丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer による保守的見積り、残余配分ロジック等を実装）。
    - 単元処理や price 欠損に対するログ出力や TODO コメントで将来拡張ポイントを明記。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシなどを算出して判定（PASS/FAIL）。
    - CLI オプションで期間指定 (--from / --to) と DB パス指定 (--db) をサポート。
    - 既定の閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）および判定ロジックを実装。

- リサーチ
  - research.factor_research の骨格を追加。DuckDB を使ったファクター計算（Momentum、Value、Volatility、Liquidity 等）の設計方針と定数を定義。関数の実装は継続中（calc_momentum 等の実装開始）。

Security / Ops
- .env ファイルは Git にコミットしないことを README / コメントにて明示。
- 環境変数のプレースホルダ検出（例: VALUE_here）が validate_config で警告される。

Known issues / Notes
- research.calc_momentum の実装がファイル終端で未完（途中で切れている）。ファクター計算モジュールはまだ完成していない部分がある。
- position_sizing と risk_adjustment にいくつかの TODO コメントあり（例: price 欠損時のフォールバック、lot_size の将来拡張など）。
- process_priority / set_cpu_affinity は権限や OS に依存するため、AccessDenied や未実装例外時は警告を出してスキップする実装。正しく動作させるには適切な権限が必要。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続する。大量ログや長期保管が必要な運用では LOG_DIR 設定やファイルシステム権限を確認すること。
- validate_config は PyYAML がない場合 YAML 内容検証をスキップする。厳密な検証には PyYAML のインストールを推奨。
- run_execution/run_monitoring はファイルによる停止フラグ (data/stop_requested.flag や data/execution.pid) に依存する。オペレーション手順に従ったフラグ管理が必要。

Migration / Upgrade notes
- 初回導入時は config_setup で .env を作成し、validate_config で検証してください。
- 本番運用 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します（自動クリアは危険）。
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定すると paper_trading.db に完全分離して記録されます。

その他
- 以後のリリースでは research モジュールの完成、追加の監視アラート（LINE 通知等）、および細かいバグ修正やパラメータ調整が予定されます。

参照
- 本 CHANGELOG はソースコードの記述・コメントから推測して作成されています。実際のコミットログではありません。