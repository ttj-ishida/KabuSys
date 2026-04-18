# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

--------------------------------------------------------------------------------

## [0.1.0] - 2026-04-18

初回リリース。

### Added
- 基本アプリケーションパッケージを追加（kabusys, バージョン 0.1.0）。
  - src/kabusys/__init__.py: パッケージのメタ情報（__version__ 等）。

- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して、本番 DB と完全分離して動作。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動・停止制御を実装。
    - 停止フラグファイル (data/stop_requested.flag) による外部停止制御と PID ファイル出力をサポート。

  - src/kabusys/run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（monitoring 用テーブルの初期化を実行）。
    - 停止フラグ検知でループ終了。KeyboardInterrupt による終了処理も整備。

- 設定管理
  - src/kabusys/config.py
    - 環境変数/.env の読み込みロジックを実装。
      - プロジェクトルート検出（.git または pyproject.toml を探索）により .env 自動ロード（無効化用: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
      - .env/.env.local の順でロードし、.env.local は上書き（ただし既存 OS 環境変数は保護）。
      - export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントなどを考慮した堅牢なパーサを実装。
    - Settings クラスでアプリ設定をプロパティ経由で取得可能に。
      - データベースパス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH)
      - ペーパートレードの fill モード（PAPER_FILL_MODE、valid: instant|partial|never|reject）
      - PID / kill flag 関連パス、閾値設定（CPU / memory / disk）
      - KABUSYS_ENV の検証（development/paper_trading/live）や LOG_LEVEL の検証など。

- 設定ユーティリティ
  - src/kabusys/config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter による再利用、最終的にファイルへ書き込み。
    - デフォルト値・選択肢・説明を提示してユーザビリティを向上。

  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パース検査（PyYAML が無ければ警告でスキップ）、本番環境用の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）などを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラの重複を避けるため一度クリアする。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作するフォールバックを実装。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な解決。

  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定（high/normal/low）を行うユーティリティを追加。psutil を利用。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等配分にフォールバックし警告を出す。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存保有と価格マップを基にセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対応。未知レジームはログ警告の上 1.0 でフォールバック。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - risk_based: リスク許容率(risk_pct), 損切り率(stop_loss_pct) に基づく株数算出。
    - equal/score: weight に基づく配分、単元株（lot_size）で丸め。
    - aggregate cap（available_cash）超過時のスケーリング処理、残余キャッシュを用いた端数配分ロジック、cost_buffer による保守的コスト見積りをサポート。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージエクスポート。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。P95 計算、日付フィルタ (--from/--to)、DB パス指定 (--db) をサポート。
    - デフォルト閾値: 稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200 ms。判定を PASS/FAIL で表示。

- リサーチ: ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールのスケルトンを追加。Momemtum/Value/Volatility/Liquidity の設計方針と定数を定義（DuckDB を使用、prices_daily/raw_financials の利用を想定）。
    - calc_momentum の関数ヘッダと定数定義（実装途中でコードが続く設計になっていることを意図）。

### Changed
- なし（初回リリースのため「追加」が中心）。

### Fixed
- なし（初回リリース）。

### Notes / Usage highlights
- 環境変数読み込み:
  - 自動ロードはプロジェクトルートが判定できる場合にのみ行われ、OS 環境変数は .env による上書きから保護されます。
  - 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ペーパートレード分離:
  - KABUSYS_ENV=paper_trading の場合、ペーパートレードは paper_trading.db（デフォルト）を使用し本番データと完全に分離されます。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動を制御できます（instant/partial/never/reject）。

- 監視プロセス:
  - run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を設定可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックしログに警告出力します。
  - 両スクリプトとも起動直後にプロセス優先度を "high" に設定する呼び出しを行います（set_process_priority）。権限が足りない場合は警告を出してスキップします。

- ログ:
  - ログは標準出力へ出力されるほか、logs/<app_name>.log に日次ローテーションで保存されます（ディレクトリ作成やファイル出力に失敗した場合はコンソールのみで動作）。

--------------------------------------------------------------------------------

今後の予定（例）
- factor_research の完全実装（calc_momentum 等の内部ロジック）。
- ExecutionEngine / SystemMonitor の詳細処理やテストの追加。
- 単体テスト、CI ワークフロー、ドキュメントの拡充。

もしこの CHANGELOG に追記・修正したい点があれば指示してください。