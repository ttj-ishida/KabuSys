CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠しています。セマンティックバージョニングを採用しています。

Unreleased
----------

（現在差分なし）

0.1.0 - 2026-04-18
-----------------

Added
- 基本バージョン 0.1.0 を初回リリース。
- 起動スクリプトを追加:
  - run_execution.py — ExecutionEngine の起動スクリプト。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを検知して安全に終了する。
- 設定周り:
  - config.py: 環境変数読み込み・管理クラス Settings を追加。多くのプロパティ（J-Quants トークン、kabu API、DB パス、paper_trading 関連、閾値、PID/kill flag パス、環境判定ヘルパー等）を提供。
  - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。.env と .env.local の読み込み順を実装し、OS 環境変数を保護する仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パースの改善: export 対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメント処理を実装。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などの paper_trading 関連設定を追加・検証。
- 設定支援 CLI:
  - config_setup.py — 対話式ウィザードで .env を初期作成/更新するツールを追加。秘匿項目のマスク表示、既存値の再利用、保存テンプレートの出力をサポート。
  - validate_config.py — .env と config/*.yaml の事前検証ツール。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML がある場合）や本番環境向け警告を実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ（純関数）モジュール:
  - portfolio.portfolio_builder: 銘柄選定 select_candidates、等重み calc_equal_weights、スコア重み calc_score_weights を実装（スコアが全て 0 の場合のフォールバックを含む）。
  - portfolio.position_sizing: position size 計算ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（スケーリング）および残余配分アルゴリズムを実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear 対応）を実装。
- ユーティリティ:
  - utils.logging_setup: ルートロガーに対して stdout ストリームハンドラと日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をセットアップするユーティリティを追加。LOG_DIR 環境変数・引数でログ保存先を制御。既存ハンドラをクリアしての再設定、ファイル作成失敗時のフォールバック動作を実装。
  - utils.process_priority: set_process_priority / set_cpu_affinity を追加。Windows と POSIX 系で差を吸収する実装（nice 値や Windows の優先度クラスのフォールバック使用）。権限不足や未実装 API の場合は警告を出してスキップ。
- 分析ツール:
  - tools.paper_verification_report.py — Paper Trading の検証レポート生成スクリプトを追加。system_status/trade_logs/risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定（閾値はソース内定義: 稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を行う。期間フィルタ（--from/--to）と DB パス指定機能を提供。
- 実行系統の依存注入/組み立て:
  - execution 側で BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの組み立てロジックを追加。ExecutionEngine は PID ファイルと停止フラグに対応し、別スレッドでセッションを実行して監視・停止を可能にする。
- DuckDB/SQLite の共存:
  - run_* と各コンポーネントで DuckDB と SQLite の接続管理を導入（分析用 DuckDB と 監視/発注用 SQLite を併用）。

Changed
- ログ出力:
  - ログのデフォルト出力先を stdout に統一し、ファイル出力は日次ローテーションかつ最大バックアップ 30 日で管理する仕様へ変更。
  - 既存ハンドラがある場合は再設定前に一度フラッシュ・クローズしてから削除するようにして二重設定を防止。
- 環境変数のロード方針:
  - OS 環境変数を優先しつつ .env.local で上書きする挙動を導入（テスト等で既存 OS 環境を保護するための protected set を使用）。
- paper_trading の DB 分離:
  - paper_trading モード時は paper_sqlite_path を使用することで本番用 SQLite から完全に分離するように変更。

Fixed
- .env パーサー:
  - クォート内のバックスラッシュエスケープやインラインコメントの扱いの不備を修正。
  - "export KEY=val" 形式のサポートを追加。
- 設定検証:
  - validate_config が PyYAML 未インストール時にも堅牢に動作するよう、YAML 検証の有無を明示的に扱うように修正。
- run_monitoring のポーリング間隔:
  - MONITOR_POLL_INTERVAL に不正な値（0 以下や整数以外）が設定された場合はデフォルト値にフォールバックし、警告ログを出すように修正（time.sleep に渡す際の ValueError 回避）。
- process_priority の互換性:
  - Windows / POSIX の差異でモジュールロードや定数参照が失敗しないよう getattr フォールバックや例外ハンドリングを強化。

Notes / Behavior
- 設計方針:
  - portfolio・risk などのコア計算は純粋関数として実装され、DB 参照は行わない（メモリ内計算）。テスト容易性と再現性を重視。
  - DuckDB 接続を受けてのデータ処理を行う研究用モジュール（factor_research など）を想定した設計。
- 安全停止:
  - run_execution/run_monitoring ともにプロジェクトの data/stop_requested.flag（あるいは設定されたパス）を監視して安全に停止する仕組みを採用。
- デフォルト値:
  - 多くのパス・閾値・挙動にデフォルト値を与え、最低限の設定でローカル開発が可能なよう配慮。

Deprecated
- なし

Removed
- なし

Security
- なし（ただし .env ファイルは機密情報を含むため Git にコミットしない旨を README/テンプレートに明記）

今後の TODO（コード中の注記より）
- position_sizing の lot_size を銘柄別に対応する（stocks マスタへの lot_size 拡張）。
- price 欠損時のフォールバック価格（前日終値や取得原価）の採用によるエクスポージャー推定改善。
- factor_research 等での DuckDB を用いたファクター計算の完成（factor_research 内の未完了箇所の実装）。
- config/*.yaml の生成スクリプトやサンプルデータ生成ツールの整備。

もしリリースノートやカテゴリの修正・詳細追加希望があれば、どの部分を重点的に書き足すか教えてください。