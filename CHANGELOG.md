# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
重大な互換性のある変更は "Changed"、新機能は "Added"、不具合修正は "Fixed" に分類しています。

## [Unreleased]

### Added
- 一連の起動スクリプトを追加 / 整備
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視 DB に接続。
    - 停止用フラグファイル（data/stop_requested.flag）を検知してループを停止。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を使って環境に応じたブローカクライアントを生成。
    - エンジンは別スレッドで実行し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
- 設定管理・自動読み込み
  - config.py
    - .env / 環境変数から設定を読み込む Settings クラスを提供。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env/.env.local を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env のパース時にシングル/ダブルクォート、バックスラッシュエスケープ、`export KEY=...` 形式、コメント扱いのルールをサポート。
    - 各種設定プロパティ（DBパス、ログレベル、Paper Trading の挙動など）を定義。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が利用可能な場合）、本番環境向けの追加ガード等を実装。
    - `--strict` で警告を FAIL 扱いにできる。
- 設定ウィザード
  - config_setup.py
    - .env の対話式作成／更新ウィザードを提供（対話プロンプト、シークレットマスク、デフォルト値・選択肢サポート）。
    - 保存時に .env のテンプレートを出力（Git にコミットしない旨の注意を明記）。
- ロギングユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで統一して使えるログ設定関数 setup_logging を提供。
    - stdout 出力（StreamHandler）と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数や引数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- プロセス優先度・CPU 固定ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX の差を吸収して優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン固定可能（未対応プラットフォームや権限不足の場合は警告を出してスキップ）。
- Portfolio 構築機能
  - portfolio/portfolio_builder.py
    - シグナル選定関数 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア全て0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別露出上限に基づいて新規候補をフィルタリング（"unknown" セクターは上限の対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を提供（未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した発注株数計算を実装。
    - lot_size 単位で丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケールダウン、端数配分ロジックを備える。cost_buffer により保守的なコスト見積りが可能。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から各種指標を集計してコンソール出力する検証レポートを実装（フィルタ: 日付範囲、DB パス）。
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, リスク却下数, レイテンシ（avg/max/P95）など。
    - デフォルト閾値（例: 稼働率 99%、P95 レイテンシ 200ms 等）に基づく PASS/FAIL 判定を出力。
    - DB が存在しない、またはテーブルがない場合は Graceful に N/A 表示。
- research/factor_research.py
  - ファクター計算モジュールの骨格を実装（モメンタム、MA200、ATR、流動性等）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（関数群は純粋関数で副作用なし）。

### Changed
- ログ出力の既存ハンドラ処理を改善
  - setup_logging は既存ハンドラを flush/close の上で削除し、二重ハンドラ設定を防止。
- run_monitoring / run_execution の起動時にプロセス優先度を "high" に設定するよう明示的に追加。
- ExecutionEngine 起動時の DB 接続先を環境（paper_trading）に応じて切り替えるように実装（Paper 用 DB と本番 DB を分離）。
- .env 自動読み込みの挙動
  - プロジェクトルートが特定できない場合は自動読み込みをスキップするように改善。
  - `.env.local` を `.env` の後に上書き読み込みするロジックを明確化（OS 環境変数は保護）。

### Fixed
- .env パーサの堅牢化
  - クォート文字列内のバックスラッシュエスケープ処理、`export KEY=...` 形式、インラインコメント扱いを適切に処理するよう改善。
- process_priority の例外処理強化
  - 権限不足や未実装プラットフォームでの例外をキャッチして警告を出力し、起動を継続するようにした。
- run_monitoring のポーリング間隔読み取りで不正値（0 や負数、数値でない文字列）を検出したときにデフォルトにフォールバックし警告するように修正。
- Paper 検証レポートの P95 計算と空データハンドリングを強化（空リスト時は N/A を返す）。

### Security
- .env の書き出しテンプレートに「.env を絶対に Git にコミットしないこと」を明記して、秘密情報の流出リスク軽減を促進。

---

## [0.1.0] - 2026-04-21

初回リリース。上記の主要機能群を含む初期実装を公開。

- 起動スクリプト: run_monitoring, run_execution
- 設定管理: config.py（自動 .env 読み込み、Settings クラス）
- 設定ユーティリティ: config_setup（.env ウィザード）、validate_config（設定検証 CLI）
- ロギング・プロセス管理: utils/logging_setup, utils/process_priority
- Portfolio 構築: portfolio_builder, risk_adjustment, position_sizing（選定・重み付け・サイズ計算）
- Paper Trading 検証: tools/paper_verification_report
- 研究用: research/factor_research（ファクター計算の下地）
- パッケージメタ: __version__ = "0.1.0"

---

注: 上記は提供されたソースコードから推測して作成した変更履歴です。実際のコミット履歴や差分と完全に一致しない場合があります。必要であれば、各ファイルの実際の変更点（追加/更新された関数や行番号など）に基づいてより詳細なログを生成します。