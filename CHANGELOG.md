# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ 下記は渡されたコードベースから推測して作成したリリースノートです。ファイル・挙動の記述はソースの内容に基づき要点を抽出しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。本リリースでは日本株自動売買システム「KabuSys」の基本的な実行基盤、設定管理、監視、ポートフォリオ構築、ポジションサイジング、ユーティリティ群、およびいくつかのコマンドラインツールを導入しています。

### Added
- 基本バージョン情報を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 設定管理
  - .env ファイルと環境変数から設定を自動読み込みする `kabusys.config.Settings` を追加。デフォルト値や型変換（float, Path）を含むプロパティを提供（src/kabusys/config.py）。
  - .env 自動読み込みの探索はプロジェクトルート（.git または pyproject.toml）基準で行うため、CWD に依存しない動作を実現。
  - 自動読み込みの保護機構（OS 環境変数を上書きしない保護リスト）を実装。
  - 環境変数の必須チェックを行う `_require()` を提供。
- 設定関連 CLI
  - 対話式 .env 作成/更新ウィザード `kabusys.config_setup` を追加。シークレット項目のマスク表示、既存値の取り込み、保存テンプレートをサポート（src/kabusys/config_setup.py）。
  - 起動前検証ツール `kabusys.validate_config` を追加。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向け追加ガードを実装（src/kabusys/validate_config.py）。
- 実行/監視ランナー
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動を行う。スレッド実行と stop フラグ検出による安全停止をサポート（src/kabusys/run_execution.py）。
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告表示。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様（明示的に本番 DB を参照する設計）。
    - 停止フラグファイル検出によるループ終了、例外発生時のログ出力とリトライ継続を実装（src/kabusys/run_monitoring.py）。
- 監視 DB 初期化
  - monitoring 用 DB の初期化を保証する `init_monitoring_db` 呼び出しを Execution/Monitoring 起動時に行う（冪等性を意識）。
- ロギング
  - 統一的なログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリの作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
- プロセス優先度 / CPU アフィニティ制御
  - クロスプラットフォームな `kabusys.utils.process_priority.set_process_priority` を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応する nice/priority の設定を行い、アクセス権限エラー等は警告ログに落とす。
  - `set_cpu_affinity` を追加し、指定コア数へ固定する機能を提供（psutil ベース）。
- ポートフォリオ構築
  - 候補選定・重み計算モジュール（純関数群）を追加:
    - select_candidates（スコア降順・タイブレークの挙動規定）
    - calc_equal_weights（等重み）
    - calc_score_weights（スコア重み、全スコアが 0 の場合は等重みへフォールバックして警告）  
    （src/kabusys/portfolio/portfolio_builder.py, src/kabusys/portfolio/__init__.py）
- リスク調整
  - apply_sector_cap（セクター集中制限の適用、未知セクターは除外しない挙動）
  - calc_regime_multiplier（市場レジームに応じた資金乗数。'bull'/'neutral'/'bear' をサポートし、未知レジームは 1.0 でフォールバック）  
    （src/kabusys/portfolio/risk_adjustment.py）
- ポジションサイズ計算
  - calc_position_sizes を実装。下記をサポート:
    - allocation_method: "risk_based" / "equal" / "score"
    - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、aggregate cap によるスケールダウン
    - cost_buffer を使った保守的コスト見積り、残差分の lot 単位での追加配分アルゴリズム
    - 価格欠損時のスキップとデバッグログ出力  
    （src/kabusys/portfolio/position_sizing.py）
- 研究（リサーチ）
  - ファクター計算モジュール骨格 `kabusys.research.factor_research` を追加（モメンタム、MA200、ATR、出来高系などを想定）。DuckDB 接続を受け SQL/Python 混在で計算する設計（src/kabusys/research/factor_research.py）。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から期間指定で各種指標（稼働率、注文成功率、送信率、レイテンシ平均/最大/P95、リスク却下数）を集計し、PASS/FAIL 判定を出力する。P95 算出、閾値定義、欠測時の N/A ハンドリングを実装（src/kabusys/tools/paper_verification_report.py）。

### Changed
- .env 読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込み。`.env.local` は OS 環境変数を上書き可能（ただし保護されるキーは除く）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途想定）。
- ログ出力のデフォルトを stdout に統一
  - StreamHandler を stdout にして、cron 等で stdout/stderr を一本化した運用を想定（file handler は任意）。
- run_monitoring のデフォルトポーリング間隔の検証強化
  - `MONITOR_POLL_INTERVAL` の不正値（非数や 0 以下）は警告してデフォルトにフォールバックするように変更。
- run_execution の DB 選択ロジック
  - Paper Trading 実行時は paper_sqlite_path を優先して接続し、本番 DB と明確に分離するロジックを導入。
- サードパーティ依存関係の扱い
  - config 検証時に PyYAML がない場合は YAML 検証をスキップして警告を出すようにして、PyYAML 非インストール環境でも軽量に動作できるように調整。

### Fixed
- .env パーサの堅牢化
  - `export KEY=val` 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時のコメント判定（'#' の直前がスペース/タブのときのみコメント扱い）などを実装し、さまざまな .env 記法に対応（src/kabusys/config.py）。
- calc_score_weights のゼロスコア処理
  - 全銘柄スコア合計が 0 の場合は等金額配分にフォールバックし、警告ログを出すように修正（src/kabusys/portfolio/portfolio_builder.py）。
- ログハンドラの二重登録防止
  - setup_logging にて既存ハンドラを明示的に flush/close/削除してからハンドラを再設定することで、複数回呼び出した際の二重出力を防止（src/kabusys/utils/logging_setup.py）。
- プロセス優先度設定の互換性改善
  - Windows 固有の priority 定数が存在しない場合のフォールバックや、POSIX 系での nice 値適用、例外（AccessDenied 等）を捕捉して安全にスキップする挙動を導入（src/kabusys/utils/process_priority.py）。
- run_execution / run_monitoring の安全停止
  - プロジェクト直下の data/stop_requested.flag を監視して停止する仕組みを導入。Execution はスレッドに対する join/stop の制御を行う（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。
- DuckDB / SQLite 接続のクローズ保証
  - 起動スクリプト内で finally ブロックなどにより接続クローズを確実に行う処理を追加。

### Internal / Documentation
- config_setup が出力する .env テンプレートに注意書き（.env を絶対に Git にコミットしないこと）を追加。
- validate_config の出力メッセージや exit code の挙動（--strict による警告の FAIL 扱い）を整備。
- tools と portfolio モジュールに docstring を整備し、設計意図や参照ドキュメント（PortfolioConstruction.md 等）を明記。

### Security
- .env ファイルの取り扱いに関する注意（config_setup のヘッダ）を追加し、秘密情報の画面表示はマスクするなど配慮。

---

注意:
- 上記はソースコードから推測した変更点・機能です。実際のコミット履歴や関連ドキュメント（CHANGELOG の元データ）があれば合わせて反映してください。