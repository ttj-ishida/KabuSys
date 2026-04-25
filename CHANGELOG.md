# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現行バージョン: 0.1.0

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点と設計上の注意点は以下の通りです。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト配下の `data/stop_requested.flag` を監視。
    - Monitoring は環境に関係なく本番用の SQLite (`Settings.sqlite_path`) を使用する旨を明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。`KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）で本番 DB と分離。
    - スレッドでエンジンを実行し、停止フラグによる安全停止処理を実装。
    - PID ファイル管理用の `data/execution.pid` パスを使用。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。`.env` / `.env.local` の読み込み順を実装し、OS 環境変数の上書きを保護。
    - 環境変数パース機能を強化（`export KEY=val`、クォート文字列、インラインコメント処理など対応）。
    - Settings クラスを提供し、各種設定（DB パス、PID ファイル、しきい値、paper_trading 関連設定等）をプロパティ経由で取得可能。
    - `PAPER_FILL_MODE` の検証（有効値: instant/partial/never/reject）や `PAPER_TRADING_SQLITE_PATH` などペーパートレード向け設定をサポート。

- 設定支援・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する機能を追加。必須項目と任意項目を区別し、シークレット値はマスク表示。
  - validate_config.py
    - 起動前の設定検証ツール (.env と config/*.yaml のチェック)。`--strict` を指定すると警告も失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出力。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/ 日次ローテーション）を設定する共通ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収して現在プロセスの優先度（high/normal/low）を設定する機能を追加。CPU アフィニティ固定機能も提供（最初の N コアにピン留め）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、タイブレークは signal_rank）と、等金額配分・スコア加重配分を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別エクスポージャー計算・除外処理）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing の実装（allocation_method: risk_based/equal/score をサポート）。
    - 単元株（lot_size）丸め、個別上限（max_position_pct）、投下上限（max_utilization）、コストバッファ考慮によるスケールダウンと残差処理ロジックを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL を判定。
    - データ欠如やテーブル未作成時に安全に動作するよう例外をハンドリング。
    - 閾値（稼働率 99% 等）を定義しているため、検証基準のドキュメント化に活用可能。

- リサーチ（部分実装）
  - research/factor_research.py
    - DuckDB を用いたファクター計算（Momentum, Value, Volatility, Liquidity）の設計を追加。モメンタム計算関数の骨子（パラメータ定義など）を含む（実装途中）。

- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 に設定。

### Changed
- なし（初回リリースのため新規実装が中心）

### Fixed
- 設定読み込み・ロバストネス向上
  - .env のパース処理でクォートやエスケープ、コメントの扱いを細かく扱うようにし、意図しない文字列切り取りや誤読を低減。
  - validate_config: PyYAML 未導入時の挙動を安全にし、該当チェックをスキップして警告を出す。
  - logging_setup: ログディレクトリ作成失敗時にアプリ全体がクラッシュしないようフォールバック（ファイルハンドラ無効化）を追加。
  - process_priority / set_cpu_affinity: 未対応 OS やアクセス権限不足のケースで例外を捕捉して警告を出し、処理をスキップするように改善。

### Security
- .env ファイルを生成する際に注意書きを追加（.env を絶対に Git にコミットしないよう明記）。
- config_setup のシークレット項目は表示時にマスクしますが、保存される .env はユーザー側で厳重に管理する必要があります（ドキュメントにも注意喚起あり）。

### Notes / Known limitations
- research/factor_research.py はモジュールの一部実装に留まっており、完全なファクター計算の実装は今後の作業予定です。
- portfolio の position sizing は現状すべての銘柄で共通の lot_size を想定（将来的に銘柄別 lot_size 対応を検討）。
- run_monitoring は「監視 DB に本番 sqlite_path を常に使う」設計になっているため、開発環境で別の DB に切り替えたい場合はコードや設定の見直しが必要です（設計上の明示的な決定）。
- 一部の機能は外部ライブラリ（psutil、duckdb、PyYAML 等）に依存します。動作環境に応じて依存関係の導入が必要です。

---

注: この CHANGELOG はリポジトリ内のソースコードから挙動・設計意図を推測して作成しています。実際のリリースノート作成時には、変更差分・コミット履歴・リリース担当者の確認を反映してください。