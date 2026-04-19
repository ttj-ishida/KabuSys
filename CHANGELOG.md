# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション初期リリース。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じてペーパートレード用の Mock ブローカを利用し、ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離する。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を検知して安全に終了する。
- 設定管理:
  - config.py — .env 自動ロード機能（.env, .env.local）を追加。OS 環境変数を保護する仕組み（protected keys）や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。環境設定を表現する Settings クラスを提供（各種パス、閾値、フラグ等のプロパティ）。
  - config_setup.py — 対話式ウィザードで .env を作成/更新する CLI を追加。シークレット項目はマスク表示し、保存前に確認を要求する。
  - validate_config.py — 起動前チェック用 CLI を追加。必須環境変数や設定ファイル（config/*.yaml）の存在・パースを検証。`--strict` オプションで警告を FAIL 扱いにできる。
- ロギング／運用ユーティリティ:
  - utils/logging_setup.py — 統一的なロギング初期化ユーティリティを追加。コンソール出力（stdout）と日次ローテーション（TimedRotatingFileHandler、30 日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py — クロスプラットフォームのプロセス優先度設定（`set_process_priority`）および CPU affinity 設定（`set_cpu_affinity`）を追加。Windows / POSIX の差異を吸収し、権限不足や未対応 OS の場合は警告を出して安全にスキップする。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py — 候補選定（スコアソート）、等分配・スコア加重配分関数を追加。
  - portfolio/risk_adjustment.py — セクター集中上限の適用（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py — 発注株数計算を追加（risk_based / equal / score）。単元株（lot_size）丸め、個別上限・集約キャップ、cost_buffer を考慮したスケーリングロジックを実装。
  - portfolio パッケージのエクスポートを追加（select_candidates 等）。
- モニタリング DB 初期化:
  - monitoring/monitoring_db.init_monitoring_db を使用し、起動時に監視用テーブルが存在することを保証する処理を起動スクリプトで呼び出すようにした（冪等）。
- Execution 関連:
  - ExecutionEngine・OrderManager・OrderRepository・RiskManager・Reconciler の組み立てと起動ロジックを run_execution.py に実装。Engine は別スレッドで実行され、停止フラグで安全停止するよう監視する。
- ツール:
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成スクリプトを追加。DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90% 等）はファイル内の定数で定義。
- リサーチ:
  - research/factor_research.py — ファクター計算モジュール（モメンタム、MA200乖離、ATR、流動性等）を実装開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（モジュールは部分実装）

### Changed
- ログ出力:
  - logging_setup でコンソール出力に stdout を利用（stderr ではなく）。これは Task Scheduler / cron 等で stdout/stderr をまとめてリダイレクトする運用を想定した変更。
- .env 読み込み優先度:
  - OS 環境変数を最優先とし、その後 .env、.env.local を読み込む（.env.local は .env よりも優先して上書き。ただし OS 環境変数は保護される）。
- デフォルトパス/挙動:
  - run_monitoring は KABUSYS_ENV に関係なく本番（設定された sqlite_path）を使用して監視する旨を明示（監視は運用上一貫した監視 DB を参照する設計）。
  - run_execution は KABUSYS_ENV=paper_trading のときに paper_sqlite_path を使用して本番 DB と分離する。

### Fixed
- 環境変数パーサーの堅牢化（config._parse_env_line）:
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い等を改善。無効行は無害にスキップされるようにした。
- MONITOR_POLL_INTERVAL の不正値対策:
  - run_monitoring._get_poll_interval で 0 以下や不正な数値が指定された場合に警告を出してデフォルト（60 秒）にフォールバックするようにした（time.sleep に無効な値を渡さない対策）。
- プロセス優先度設定の安全化:
  - set_process_priority は権限不足や未対応プラットフォームで例外を投げず警告ログを出してスキップするようにした。
- ログディレクトリ作成失敗時の退避:
  - ログディレクトリ作成に失敗してもアプリケーションがクラッシュせず、コンソール出力のみで継続するように改善。

### Security
- config_setup にてシークレット項目（J-Quants トークン、kabu API パスワード等）を入力欄でマスク（表示は ****）して扱うことで、誤ってシークレットをコンソールログに表示するリスクを低減。
- .env 出力ヘッダで「.env は絶対に Git にコミットしないこと」を明記。

### Notes / Implementation details
- デフォルトの DB / ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- ログローテーション設定: 日次、バックアップ 30 日分。
- process_priority は Windows と POSIX（Linux/Mac/FreeBSD）に対応。未対応 OS は警告でスキップ。
- paper_verification_report は CLI オプションで期間指定（--from, --to）と DB パス指定（--db）をサポート。
- Settings クラスは環境変数の妥当性チェック（列挙値チェックや数値変換）を行うため、起動前に validate_config で検証する運用を強く推奨。

---

今後の計画（例）
- research/factor_research の完全実装（Value, Volatility, Liquidity ファクターの集計と正規化）。
- backtest / simulation ツールの追加。
- モニタリング・アラート（LINE 通知）連携の実装強化。