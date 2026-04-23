# Changelog

すべての変更は Keep a Changelog の形式に従います。  
バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に基づきます。

なお、本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴と完全に一致しない場合があります。

## [Unreleased]

### Added
- 監視用ポーリングプロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。
  - 停止フラグ（data/stop_requested.flag）を検知して安全にループ終了。
  - 起動時にプロセス優先度を "high" に設定。
  - Monitoring 用 DB 初期化を行い、SQLite と DuckDB の接続を確立。
  - 例外発生時はログ出力して次のポーリングを継続。

- 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
  - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用の SQLite を使用（data/paper_trading.db をデフォルト）。
  - BrokerClientFactory により環境に応じたブローカークライアントを生成（Paper 時は Mock を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 起動・実行中に停止フラグ（data/stop_requested.flag）を監視して安全に停止。
  - PID ファイルの取り扱い（実行エンジン用 pid path）をサポート。

- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env 自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env と .env.local の優先順位、既存 OS 環境変数の保護機能を実装。
  - 各種設定プロパティ（J-Quants, kabu API, DB パス, Paper 設定、監視閾値、環境種別など）を提供。
  - PAPER_FILL_MODE のバリデーション（"instant","partial","never","reject"）。
  - KABUSYS_ENV の有効値検査（development/paper_trading/live）。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検査を実行。
  - PyYAML がない場合は YAML 検査をスキップして警告を出す。
  - `--strict` オプションで警告も失敗扱いにできる。

- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - 対話式に .env を作成・更新するウィザード。
  - シークレット値のマスク表示や選択肢／デフォルトの提示に対応。
  - 生成される .env のテンプレートと保存ロジックを提供。

- ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続。
  - ログレベル・ログディレクトリの解決順を明示。

- プロセス優先度／CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX を吸収してプロセス優先度を設定（"high","normal","low"）。
  - CPU affinity を最初の N コアに固定する関数を提供。
  - psutil API の権限エラーを安全にハンドリングして警告ログを出す。

- Portfolio 構築関連の純粋関数群を追加（src/kabusys/portfolio/*）。
  - 銘柄選定（select_candidates）、重み計算（calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
  - 株数決定ロジック（calc_position_sizes）：risk_based / equal / score の allocation_method をサポート、単元株（lot_size）丸め、cost_buffer を用いた保守的コスト見積り、aggregate scale-down ロジックを実装。
  - 各モジュールは DB 非依存の純粋関数で構成。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - system_status / trade_logs / risk_logs を参照して稼働率、成功率、送信率、レイテンシ（平均/最大/P95）を算出。
  - 合格基準（稼働率・成功率等）の閾値を定義し PASS/FAIL 判定を出力。
  - 日付フィルタ（--from, --to）と DB パス指定（--db / 環境変数）に対応。

- research/factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
  - StrategyModel に基づくモメンタム等のファクター計算を意図した設計と定数定義を追加。
  - DuckDB 接続を受け取り prices_daily / raw_financials を利用してファクターを計算する設計（関数 calc_momentum 等を実装開始、ファイル末尾は一部未完のまま）。

### Changed
- パッケージの初期バージョンを 0.1.0 として定義（src/kabusys/__init__.py）。

### Fixed
- MONITOR_POLL_INTERVAL が不正（非整数・0 以下）の場合にデフォルトにフォールバックするバリデーションを run_monitoring に実装。
- SQLite / DuckDB 接続を開いた後、finally ブロックで確実にクローズするように run_monitoring/run_execution で明示的に close。

### Documentation / UX
- config_setup の生成 .env ヘッダに注意書き（.env を Git にコミットしないこと）を追加。
- validate_config は出力で INFO / WARNING / ERROR を分けて表示し、最後に OK/FAIL を返す UX を実装。

## [0.1.0] - 2026-04-23

初回公開リリース。上記 "Added" 項目を含む主要機能を提供。

- 監視・実行の起動スクリプト（run_monitoring, run_execution）
- 設定管理（.env 自動ロード、Settings クラス）
- 設定ウィザード（config_setup）、設定検証ツール（validate_config）
- ロギング / プロセス優先度ユーティリティ
- ポートフォリオ構築（選定、重み付け、位置量計算、リスク調整）
- Paper Trading 検証レポートツール
- 一部のリサーチ（factor_research）の骨組み

---

注記（既知の TODO / 制限点、ソース内コメントを基に推測）
- factor_research.calc_momentum 等の実装が途中で切れている（ファイル末尾が未完）。実使用前に関数実装とテストが必要。
- position_sizing の price フォールバック（価格欠損時の扱い）は TODO コメントあり。価格が欠損するとエクスポージャーを過少見積りする可能性があるため、前日終値や取得原価のフォールバックを検討すること。
- 単元株（lot_size）を銘柄別に扱う拡張は未実装。将来的に銘柄マスタによる lot_map の導入を想定。
- ログディレクトリ作成やプロセス優先度設定は環境（権限・OS）に依存するため、失敗時はフォールバックして安全に動作するが、運用時は環境依存の動作確認が推奨される。

もし実際のリリースノート（コミットログやバージョン履歴）が別にある場合は、それを元により正確な CHANGELOG.md を作成できます。必要であればその情報を提示してください。