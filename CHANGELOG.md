CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメント/メタ情報の更新、内部リファクタリング（細かなログ文言/コメント等）。


[0.1.0] - 2026-04-18
-------------------

Added
- 初期公開: KabuSys パッケージ全体を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。主な挙動:
    - プロセス優先度を高 ("high") に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止を監視。
    - 起動時に PID ファイル path を指定して実行（_EXECUTION_PID）。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。主な挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルの初期化を行う（init_monitoring_db）。
    - data/stop_requested.flag を検知してループを終了。
- 設定・環境管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数をラップして取得:
    - 各種必須値 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) の取得、env/log_level の検証、デフォルト値の扱い。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID ファイル / Kill Flag 関連設定等を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - .env 自動読み込み機能を追加:
    - プロジェクトルート (.git または pyproject.toml) を起点に .env/.env.local を読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env.local は .env をオーバーライド（ただし既存の OS 環境変数は保護）。
    - .env のパースで export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
- 設定補助 CLI
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）:
    - .env の作成・更新を支援。秘匿項目はマスク表示。生成テンプレートの出力と保存。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates: score 降順＋signal_rank タイブレークで上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコア 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap: 既存保有を基にセクター上限を判定し、新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数 (bull=1.0, neutral=0.7, bear=0.3)、未知レジームは警告のうえ 1.0 をフォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）:
    - allocation_method により "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、1 銘柄上限（max_position_pct）、投下資金の aggregate cap、cost_buffer（スリッページ/手数料見積り）を考慮したスケーリングロジックを実装。
    - aggregate cap によるスケールダウン時は小数端数処理で再配分ロジックを実装し、lot_size 単位での再配分を行う。
- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）:
    - StreamHandler を stdout に設定（cron 等で stdout/stderr を一本化する運用を想定）。
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/ ディレクトリ、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）:
    - set_process_priority(level: "high"|"normal"|"low") を提供。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して nice / HIGH_PRIORITY_CLASS 等を適用。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能（権限不足・未対応 API は警告でスキップ）。
- 監視 DB 初期化ユーティリティ呼び出し
  - init_monitoring_db を起動時に実行して監視テーブルの存在を保証（run_monitoring / run_execution）。
- DuckDB 統合
  - 各種処理で DuckDB 接続を利用する設計（Settings.duckdb_path、duckdb.connect）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）:
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計・出力。
    - 基準値を定義して PASS/FAIL 判定（稼働率99%、成立率90%、送信率95%、P95<=200ms 等）。
    - --from / --to / --db オプションに対応。デフォルトで環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用。
- 研究用モジュール（ファクター計算）
  - 基本構成を追加（src/kabusys/research/factor_research.py）: モメンタム/Value/Volatility/Liquidity 等の算出方針を実装（DuckDB の prices_daily / raw_financials を前提）。（実装は継続）

Changed
- なし（初回リリースのため）。

Fixed
- なし（初回リリースのため）。

Removed
- なし（初回リリースのため）。

Security
- 環境設定ウィザードおよび .env の取り扱いに関して注意喚起を出力（.env を Git にコミットしない旨の注記を生成）。

Notes / Implementation details
- データ分離:
  - paper_trading モードでは発注関連データを専用 SQLite に記録し、本番監視 DB と分離する設計。
  - 監視コンポーネントは環境にかかわらず本番用 sqlite_path を参照する仕様（run_monitoring）。
- ロック/停止:
  - 外部からの停止指示はプロジェクト直下の data/stop_requested.flag によるポーリング検出で行う。
- ログ運用:
  - コンソールは stdout、ファイルは logs/<app_name>.log に日次ローテーションで保存。ファイル出力に失敗してもプロセスは継続する（Console-only フォールバック）。
- .env パーサは実運用を想定して export プレフィックス、クォーティング、エスケープ、インラインコメント等に対応している。

Acknowledgements
- 本リリースはプロジェクト初期状態の機能群（設定管理、起動スクリプト、ポートフォリオ計算、ユーティリティ、検証/ウィザード/レポートツール、研究モジュール）を包含します。今後、ユニットテスト、ドキュメント拡充、欠損値ハンドリングの改善、戦略実装・バックテスト機能の追加などを予定しています。