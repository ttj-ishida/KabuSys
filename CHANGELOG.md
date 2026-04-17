# Changelog

全ての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニング (MAJOR.MINOR.PATCH) に従います。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム KabuSys のコア機能群と運用用 CLI / ユーティリティを追加しました。

### Added
- パッケージ基盤
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 環境設定・検証
  - .env 自動読み込み機能を追加（OS 環境変数優先、.env.local → .env を読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（src/kabusys/config.py）。
  - .env パーサー実装：export 構文、シングル/ダブルクォート、エスケープ、行末コメント等に対応（src/kabusys/config.py）。
  - Settings クラスを追加して環境変数を型変換/検証付きで提供（DB パス、KABUSYS_ENV、PAPER_FILL_MODE など多数の設定プロパティ）（src/kabusys/config.py）。
  - 対話式環境設定ウィザードを追加（python -m kabusys.config_setup）。.env の生成・更新を支援し、シークレットのマスク表示やデフォルトの扱いを実装（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML 有無を考慮）、および本番用ガードチェック（LINE 通知設定や Kill Switch の設定）を実施。--strict オプションで警告を失敗扱いに可能（src/kabusys/validate_config.py）。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を高く設定（src/kabusys/utils/process_priority.py を利用）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - エンジンはデーモンスレッドで実行し、 data/stop_requested.flag による停止検出で安全終了。execution.pid を扱う仕組みを導入。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop_requested.flag による終了検出、例外はログに出してループ継続する安全性設計。
- データベース / 分析
  - duckdb 接続を用いる設計を採用（duckdb_path 設定）。両 CLI で duckdb 接続の生成とクローズを行う。
- ポートフォリオ構築（純粋関数）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークロジックを実装。
    - calc_equal_weights / calc_score_weights: スコア合計が 0 の場合は等金額配分にフォールバック（警告出力）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率に基づき新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear とマップ、未知レジームは警告のうえ 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）をサポート。risk_based の基本ロジック、max_position_pct、max_utilization、lot_size（単元株丸め）、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap のスケールダウンと端数処理（lot 単位で残余キャッシュを再配分）。
  - ポートフォリオ API のエクスポートを提供（src/kabusys/portfolio/__init__.py）。
- 監視・運用ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収。psutil を用いて優先度（high/normal/low）と set_cpu_affinity を扱う。権限不足や未実装 API の場合は警告を出してスキップ。
- Paper Trading 検証ツール
  - paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均、最大、P95）を集計。
    - P95 計算、日時フィルタ（ISO8601 UTC 文字列で範囲指定）、しきい値による PASS/FAIL 判定を実装。
    - DB やテーブル欠如時の安全なフォールバック（OperationalError への耐性）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーでの細かい耐久性向上
  - クォート内のバックスラッシュエスケープ処理やインラインコメントの無視、export 付き行のサポートなどにより一般的な .env 形式に堅牢に対応（src/kabusys/config.py）。
- CLI/ランナーのリソースクリーンアップ強化
  - run_monitoring / run_execution で finally ブロックを使って sqlite / duckdb 接続を確実にクローズするようにした。

### Security
- .env ファイルに関する注意書きを config_setup の出力に追加（.env を Git にコミットしないことを明示）。

### Documentation / UX
- config_setup の対話ウィザードでシークレットをマスク表示、デフォルト提示、入力キャンセルのハンドリングを追加（src/kabusys/config_setup.py）。
- validate_config の出力で INFO / WARNING / ERROR を整備し、--strict による CI での厳格チェックを想定。
- run_execution と run_monitoring の起動ログに起動環境（KABUSYS_ENV）とポーリング間隔等を出力。

---

注:
- 初回リリースのため破壊的変更や廃止項目はありません。
- 今後のリリースでは各コンポーネント（ExecutionEngine、BrokerClient、Reconciler、監視 DB スキーマなど）の詳細なバグ修正・最適化を追記していきます。