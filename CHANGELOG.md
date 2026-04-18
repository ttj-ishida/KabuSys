# Changelog

すべての非互換性のない変更は遵守された仕様に従って記載します。（Keep a Changelog 準拠）

※ 内容はリポジトリ内のソースコードから推測してまとめた変更履歴です。

## [Unreleased]

### Added
- 環境設定関連
  - .env 自動読み込みの実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数は保護され、.env.local は .env を上書きする仕組みを導入（src/kabusys/config.py）。
  - .env 行パーサーを強化。export 付きの行、クォートされた値、インラインコメント、エスケープシーケンスに対応（src/kabusys/config.py）。
  - 対話式環境設定ウィザードを追加。.env の初期作成・更新を支援する CLI（python -m kabusys.config_setup）（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパースをチェック可能（--strict オプションで警告を失敗扱い可能）（src/kabusys/validate_config.py）。

- 実行/監視ランナー
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 時はペーパートレード用 DB を使用し、Mock ブローカー等を切り替え可能（src/kabusys/run_execution.py）。
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を常に使用（src/kabusys/run_monitoring.py）。
  - 停止フラグ / PID ファイルによるプロセス制御を実装（data/stop_requested.flag, data/execution.pid 等を使用）（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算関数を実装（スコア降順の選択、等金額配分、スコア加重配分、スコア全ゼロ時のフォールバック） （src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。セクター別エクスポージャ計算や未知レジームのフォールバックロジックを含む（src/kabusys/portfolio/risk_adjustment.py）。
  - 株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元丸め（lot_size）、aggregate cap スケーリング、cost_buffer を考慮したスケーリングと小数端数処理を含む（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージの __all__ を整備（src/kabusys/portfolio/__init__.py）。

- ユーティリティ
  - 統一ロギングセットアップを提供（StreamHandler→stdout と TimedRotatingFileHandler による日次ローテーション、ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR を尊重）（src/kabusys/utils/logging_setup.py）。
  - プロセス優先度および CPU affinity のユーティリティを追加。Windows/Linux/macOS の差分吸収、権限不足時のフォールバックや警告出力を実装（src/kabusys/utils/process_priority.py）。

- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を出力（src/kabusys/tools/paper_verification_report.py）。
  - レポートは期間フィルタや DB パス指定 (--from, --to, --db) に対応。

- リサーチ（未完）
  - ファクター計算モジュールの土台を追加。モメンタム / MA / ATR / ボリューム等の計算設計方針と定数を定義（src/kabusys/research/factor_research.py）。（実装は途中）

### Changed
- Logger とプロセス優先度の初期化順序を統一。起動スクリプトは最初に setup_logging を呼び、その直後に set_process_priority を実行するようになっている（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- DB 接続の取り扱いを明確化。Monitoring は常に sqlite_path（本番）を使用、Execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py, src/kabusys/config.py）。

### Fixed
- .env 読み込み時にファイル読み取り失敗した場合の警告出力を改善（警告を発生させつつ起動継続）（src/kabusys/config.py）。
- ロギング設定でログディレクトリ作成に失敗した場合に stdout/stderr に警告を出し、ファイルハンドラをスキップする安全策を追加（src/kabusys/utils/logging_setup.py）。
- プロセス優先度設定でサポート外 OS や権限不足時に適切に警告して処理をスキップするようにした（src/kabusys/utils/process_priority.py）。

---

## [0.1.0] - 2026-04-18

### Added
- 初版リリースとして以下の主要コンポーネントを追加:
  - 設定管理:
    - Settings クラスを持つ環境変数ラッパー。各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, LOG_LEVEL, DB パス等）の取得と基本バリデーションを提供（src/kabusys/config.py）。
  - 起動スクリプト:
    - 実行エンジン起動スクリプト（run_execution.py）。
    - 監視起動スクリプト（run_monitoring.py）。
  - CLI ユーティリティ:
    - 環境設定ウィザード（config_setup.py）。
    - 設定検証ツール（validate_config.py）。
  - ロギング・プロセス管理ユーティリティ:
    - logging_setup.py、process_priority.py を実装。
  - ポートフォリオ構築:
    - portfolio モジュール（候補選定・重み計算・ポジションサイズ算出・リスク調整）を実装。
  - ペーパートレード検証:
    - tools/paper_verification_report.py を実装し、ペーパートレード DB から検証レポートを出力可能に。
  - パッケージメタ:
    - __version__ = "0.1.0" を設定（src/kabusys/__init__.py）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

---

注:
- 上記はソースコードから推測して作成した変更履歴です。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。
- 省略・推測が含まれるため、必要であれば個別ファイルごとの詳細な変更点（関数説明、引数仕様、既知の制限など）を追記できます。