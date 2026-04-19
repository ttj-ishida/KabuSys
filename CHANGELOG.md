CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。
日付はリポジトリ内のコードから推測しました。

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコア機能群を追加。
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient（Paper Trading）を使用し、data/paper_trading.db を利用して本番 DB と完全に分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御を実装。
    - Engine を別スレッドで動作させ、停止フラグ検知時に安全に停止するロジックを追加。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様を明記。
    - 停止フラグ検知時にループを終了し、リソースをクローズする処理を実装。
- 設定・環境変数管理
  - Settings クラス（src/kabusys/config.py）を追加。各種環境変数の取得・検証を提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env/.env.local を読み込む（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証、PAPER_TRADING_SQLITE_PATH（Paper 用 DB パス）、DUCKDB_PATH / SQLITE_PATH 等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック、is_live/is_paper/is_dev のユーティリティを実装。
- 設定補助 CLI
  - config_setup: 対話式ウィザードで .env を作成 / 更新する CLI を追加（src/kabusys/config_setup.py）。
    - シークレット項目は入力時・確認時にマスク表示。ファイルに注釈付きで書き出す。
  - validate_config: .env と config/*.yaml の検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ存在確認、YAML パースチェック（PyYAML がない場合は警告）を実装。
    - --strict オプションにより警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定と CPU affinity 設定を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）対応の優先度設定。権限不足など失敗時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアにピン留め可能（未指定は変更なし）。
- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio_builder: 候補選定・等配分・スコア加重配分を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順・タイブレークで signal_rank を使用して上位 N を選択。
    - calc_equal_weights / calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
  - risk_adjustment: セクター集中制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存ポジションを基にセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた乗数（bull/neutral/bear）を返す。未知レジームは 1.0 にフォールバックして警告。
    - 注意点: price 欠損時の挙動に関する TODO コメントあり（フォールバック価格の導入を検討）。
  - position_sizing: 発注株数決定ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - リスクベースの計算（risk_pct, stop_loss_pct）と 1 銘柄上限（max_position_pct）を実装。
    - lot_size（単元）で丸め、aggregate cap（available_cash）を超える場合はスケールダウンして残差を lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer による手数料・スリッページの保守的見積りを考慮。
    - TODO: 将来的な銘柄毎 lot_size 対応の注記あり。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）を算出して判定。
    - P95 計算、日付範囲フィルタ、閾値（稼働率 99%、填率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - CLI 引数: --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可。
- Research
  - research.factor_research（ファクター計算モジュール）を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 系の計算方針を実装方針として定義。
    - DuckDB を用いて prices_daily / raw_financials に依存する設計。calc_momentum の実装開始（ファイル末尾で途中） — WIP。

Changed
- ログ出力の標準化: すべての起動スクリプトは utils.setup_logging を最初に呼び出す設計になっているため、ログ振る舞いが一貫化。
- プロセス起動時の優先度強化: 起動直後に set_process_priority("high") を呼び出すようにして、実行中の安定性を向上。

Fixed
- validate_config: PyYAML 未インストール環境でもスクリプトが実行できるように、YAML 未インストール時はパースチェックをスキップして警告を出す挙動に修正。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の管理でシークレット項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE チャネルトークン等）は対話ウィザードでマスクして表示。環境変数は .env に平文で保存されるため、.env を Git にコミットしない旨を .env ヘッダに明記。

Known issues / Notes
- research.factor_research.calc_momentum の実装が途中（ファイル末尾で途切れ）であり、WIP 状態です。
- apply_sector_cap は price_map に欠損（0.0）がある場合に過少評価される可能性があり、将来的にフォールバック価格を導入することを検討中。
- position_sizing の将来拡張として銘柄別 lot_size をサポートする予定あり（現状は全銘柄共通の lot_size を想定）。
- 一部の機能（プロセス優先度設定、CPU affinity）は OS 権限やプラットフォーム依存で動作しない場合があり、その場合は警告を出してスキップするよう安全策を入れている。

参考: 主要な環境変数・デフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 60（run_monitoring のデフォルトポーリング秒数）
- KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）

以上。