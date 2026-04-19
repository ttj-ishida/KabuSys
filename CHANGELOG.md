# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
重大な互換性のある変更はセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ群、起動スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツールなどを追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止はプロジェクト直下の data/stop_requested.flag によって検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を使用する想定）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ検知による安全なシャットダウン処理（PID ファイル管理、スレッド監視）。

- 設定関連
  - config.py
    - .env ファイル自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env と .env.local の読み込み順序、既存 OS 環境変数を保護する挙動をサポート。
    - Settings クラスを導入し、環境変数のラッパー（各種必須／オプション設定、バリデーション、パス解決など）を提供。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / 各種閾値（CPU/MEM/DISK）などのプロパティを実装。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値チェックを実装。

  - config_setup.py
    - .env の初期作成・更新を支援する対話式ウィザードを追加。
    - 入力のヒント表示、シークレットマスク、既存 .env の読み込み／再利用、保存確認機能を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 存在時）などを実行。
    - --strict オプションで警告をエラー扱いにできる機能を追加。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を追加。
    - stdout への StreamHandler（標準出力）および日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、デフォルト 30 日保存）を設定。
    - LOG_DIR / LOG_LEVEL の環境変数を尊重。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。

  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定関数 set_process_priority を追加（Windows の priority class / POSIX の nice を設定）。
    - CPU affinity を設定する set_cpu_affinity 関数も追加（利用可能コア数の範囲チェック、権限不足時に警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点のタイブレークロジック）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックと警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中制限ロジック。既存保有と当日売却予定を考慮して新規候補を除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告のうえ 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes：発注株数決定ロジックを実装（allocation_method に応じた risk_based / equal / score、単元株での丸め、1 銘柄上限・集計上限、cost_buffer による保守的見積り、available_cash に基づくスケールダウンと残差配分）。
    - lot_size（単元）と cost_buffer を考慮した安全な丸め・スケーリング実装。

- リサーチ / ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム等のファクター計算のためのスケルトン実装を追加（定数・設計方針・calc_momentum の開始部分を含む）。DuckDB を受け取り prices_daily / raw_financials を参照して計算する設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。期間フィルタ --from / --to をサポート。
    - しきい値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）を定義し判定に使用。

- パッケージ初期化
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 環境変数の自動ロードはプロジェクトルートを .git または pyproject.toml で検出するため、パッケージ展開後の CWD に依存しない設計。ただしルートが見つからない場合は自動ロードをスキップ。
- .env の読み込み順と上書きルール:
  - OS 環境変数が最優先。次に .env（既存値を上書きしない）、最後に .env.local（上書き許可）という挙動。
  - テストなどで自動ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- run_monitoring は Monitoring 用 DB を環境に依らず本番 sqlite_path を使うという設計意図が明示されている（監視が必ず本番状態を監視する想定）。
- run_execution はペーパートレード時に DB を完全に分離（data/paper_trading.db）することで本番データへの影響を排除。
- ロギングは stdout を主要なストリームとして使用（cron / Task Scheduler からの実行を考慮）、ファイル出力は日次ローテートで 30 日分保存。
- process_priority 関連は権限不足や未サポート OS に対しては警告を出して処理をスキップする安全設計。

---

今後の予定（提案）
- research/factor_research.py の各ファクター計算（Value, Volatility, Liquidity）の完成とユニットテスト追加。
- ExecutionEngine / BrokerClient の実装とペーパートレードの動作確認、さらに risk_manager 等の統合テスト。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）の実装補完。
- 単体テストおよび CI による自動検証の追加。