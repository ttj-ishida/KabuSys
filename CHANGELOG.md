# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新の変更履歴は以下のバージョンに記載されています。

未リリースの変更については Unreleased セクションを利用してください。

## [Unreleased]
- なし（現在のコードベースは最初の公開バージョン相当の実装を含みます）
- 注意: research/factor_research.py 内の calc_momentum の実装が途中で途切れている箇所があり、ファクター計算モジュールの追加実装・テストが必要です。

## [0.1.0] - 2026-04-18
初回リリース相当の実装。システムの起動スクリプト、設定管理、監視・実行コンポーネントの基盤、ポートフォリオ構築ロジック、ユーティリティ群、及び運用支援ツールを追加。

### Added
- 基本バージョン
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する設計に対応。
    - 起動時にプロセス優先度を High に設定するフローを組み込み（set_process_priority を呼び出し）。
    - エンジンは別スレッドで run_session を実行し、 data/stop_requested.flag による停止シグナル監視を行う。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視は環境に依存しない設計）。
    - 起動時にプロセス優先度を High に設定。

- 設定管理
  - 環境変数/ .env 自動読み込みと Settings ラッパーを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード（環境変数による無効化オプション `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意）。
    - .env の読み込みは OS 環境変数（既存のキー）を保護する仕組みを導入（.env.local は override により上書き可能）。
    - 多数の設定プロパティを提供（J-Quants, kabu API, LINE, DB パス、監視閾値、実行環境判定等）。
    - `PAPER_FILL_MODE` のバリデーション、`KABUSYS_ENV` および `LOG_LEVEL` の検証ロジックを実装。

- 設定支援ツール
  - インタラクティブな .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で主要な環境変数を入力でき、.env を生成・更新するユーティリティ。
    - シークレット項目のマスク表示、選択肢チェック、既存 .env の読み込み・再利用に対応。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース等を検証。
    - `--strict` オプションで警告を失敗扱いにできる。live 環境時のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコアが全て 0 の場合は等配分へフォールバック。
  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮しセクター集中を抑制（"unknown" セクターは制限対象外として扱う）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは 1.0 でフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、端数分配ロジックを実装。

- 運用ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log、30 日保持）を統一的に設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/macOS/FreeBSD）を吸収して優先度を設定、psutil 使用。失敗時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアに固定可能（権限不足時は警告）。

- 監視・モニタリング
  - 監視 DB 初期化呼び出しを run_monitoring / run_execution で行う（monitoring_db.init_monitoring_db を呼出し、監視テーブル存在を保証）。
  - 監視ループは停止フラグ（data/stop_requested.flag）を監視して安全に終了。

- ペーパートレード検証ツール
  - Paper Trading 向け検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL 判定（閾値はソース内で定義）。
    - CLI オプション --from / --to / --db に対応。デフォルト DB は環境変数または data/paper_trading.db。

- 研究用モジュール（骨格）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum, Value, Volatility, Liquidity 等の計算方針と定数を定義。
    - DuckDB 接続経由で prices_daily / raw_financials を参照して計算する設計。
    - calc_momentum の実装を開始（途中でコードが途切れているため追加実装が必要）。

### Changed
- なし（初回リリース向け実装のため「追加」が中心）

### Fixed
- なし（初期実装。既知の動作は logger.warning や例外で安全にフォールバックする実装が含まれる）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（ただしシークレット扱いの環境変数は config_setup でマスク表示し、.env の Git へのコミット禁止をコメントで明記）

---

注記:
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして利用する場合は、リリース時の差分・マージ履歴・テスト結果等を反映して適宜更新してください。
- research/factor_research.py の未完箇所や将来的に必要な機能（ロギングの詳細設定、より厳密な価格フォールバック、銘柄別 lot_size 対応など）は今後の改善候補です。