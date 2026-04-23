# Changelog

すべての注目すべき変更点を記録します。This project adheres to "Keep a Changelog" と SemVer を使います。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ExecutionEngine の起動と停止フラグ管理（data/stop_requested.flag）を実装。`KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB を分離して使用する挙動をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能。監視用 DB（SQLite）と DuckDB を接続して SystemMonitor を定期実行する。

- 設定関連
  - config.py: 環境変数/ .env の自動読み込みと Settings クラスを追加。多くの設定プロパティをラップ（DB パス、ログレベル、環境種別、Paper Trading ルール等）。`.env` 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。
  - config_setup.py: 対話式ウィザードを追加して `.env` の初期作成・更新を支援。必須/任意項目、シークレットマスキング、保存前確認を備える。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数・パス・config/*.yaml の存在（および PyYAML があればパース）や本番用ガードチェックを行い、`--strict` で警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定、ログディレクトリ自動作成とフォールバック動作を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。権限不足時は警告を出してスキップする安全設計。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選定（score 降順）と等分・スコア加重の重み算出を提供。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームやスコア 0 の場合のフォールバック挙動を明記。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジック（risk_based / equal / score）および lot_size に基づく丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
  - portfolio/__init__.py: 上記関数を再エクスポートするパッケージ API を提供。

- 監視・ペーパートレード検証ツール
  - monitoring 初期化フック: `init_monitoring_db` を呼び出して監視用テーブルの存在を保証する（冪等）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。期間フィルタ、DB パスオーバーライドオプションをサポート。

- リサーチ／ファクター計算（基盤）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。計算パラメータ（窓長、スキャン幅等）を定義済み。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の注意
- .env パーサはシングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いに細かく対応しており、既存の OS 環境変数を保護する仕組み（protected set）を持つ。
- Logging のファイル出力はログディレクトリ作成に失敗した場合に自動的にコンソール出力へフォールバックするため、cron 等での起動時に安全。
- process_priority は OS や権限により動作しない場合があるが、安全にスキップして起動を続行する設計。
- ExecutionEngine はペーパートレード時に MockBroker を使用して本番 DB と完全分離する（PAPER_TRADING_SQLITE_PATH を使用）。
- Portfolio/position_sizing の一部は将来的に銘柄別 lot_size のサポートや価格フォールバックの拡張を想定した TODO コメントを含む。
- research/factor_research.py はファクター計算の設計方針と定数を含み、関数実装の続きを行う必要がある箇所がある（今後の実装予定）。

### Security
- 本リリースでは機密情報（API トークン、パスワード等）を .env に保存する設計のため、.env を Git にコミットしないよう強調する注記を config_setup に記載。

（以上）