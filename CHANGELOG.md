# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25
初回リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- 実行エントリ / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視用 DB は環境に関わらず本番の sqlite_path を使用。
    - monitor.check_once() 実行時の例外を捕捉してログ出力し、次ポーリングへ継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離。
    - 停止フラグと PID ファイル（data/execution.pid）による制御を実装。起動時に停止フラグが立っていれば起動を中止。
    - スレッドでエンジンを起動し、停止フラグ検出時に engine.stop() で安全に停止するループ。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env 自動ロード機能を実装（無効化環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意）。
    - .env ファイルの堅牢なパーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理）。
    - Settings クラスを導入し、各種設定項目をプロパティで提供（必須トークンの取得・検証、デフォルト値、値チェック）。
    - paper_trading 用の設定（PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH など）。
    - システム監視閾値（CPU/MEM/DISK）や PID / kill flag 周りの設定を明示化。
    - settings シングルトンをエクスポート。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話形式で入力・保存可能。
    - 既存 .env の読み込みと既存値の再利用、シークレット値のマスク表示、保存前の確認を実装。

  - validate_config.py
    - 起動前チェック CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML があればパース検証）等を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定確認や KILL_FLAG_CLEAR_ON_START の警告）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一されたロギング初期化ユーティリティを追加。
    - stdout への StreamHandler（標準出力）、および日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 重複ハンドラ防止のため既存ハンドラをクリアして再設定。
    - LOG_LEVEL / LOG_DIR の解決順とファイル出力失敗時のフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS 対応を考慮）。
    - `set_process_priority(level)`：high / normal / low をサポート。権限不足等の失敗は警告でスキップ。
    - `set_cpu_affinity(cpu_count)`：最初の N コアにピン留めする機能（権限不足時は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点時に signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を考慮して特定セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を追加。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、1 銘柄上限・aggregate 上限の適用、cost_buffer を含めた保守的コスト見積り、合計額が available_cash を超える場合のスケーリングと残差処理（lot 単位で再配分順序を安定化）を実装。

- 解析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを集計。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - DB ファイルパスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトの順で解決。

- リサーチ（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計、DuckDB 接続受入れ、出力仕様など）。
    - calc_momentum の開始実装（定数・仕様定義を含む）。（実装は継続中／部分的）

- パッケージメタ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。
  - パッケージの __all__ に主要サブパッケージを追加。

### Changed
- （初回リリースのため過去からの変更はなし）

### Fixed
- （初回リリースのため過去からのバグ修正はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- run_execution / run_monitoring の動作は外部コンポーネント（BrokerClient, ExecutionEngine, SystemMonitor 等）に依存します。これらの実体実装は別モジュールにあり、本リリースでは起動フローや周辺ユーティリティの整備を中心に行いました。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後やテスト環境での安全性を確保）。
- ファイルやディレクトリの作成に失敗した場合、ロギングはコンソール出力にフォールバックするよう設計しています。