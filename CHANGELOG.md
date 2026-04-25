# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
この CHANGELOG はソースコードから推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初回リリース。主要な機能追加・CLI・ユーティリティ・ポートフォリオ構築ロジックなどを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト / 長期運用用プロセス
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に依らず本番用の sqlite パスを使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）により安全にループを終了。
    - DB 初期化（`init_monitoring_db`）を起動時に実行。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBroker を利用し、専用の paper_trading DB を使用して本番 DB と完全分離。
    - PID ファイル管理と停止フラグ（data/stop_requested.flag）による安全停止対応。
    - スレッド実行で Engine の実行/停止を管理。

- 環境設定 / 検証 CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - J-Quants / kabu API などの必須設定項目を対話で設定可能。
    - .env を上書き保存するユーティリティを提供（生成された .env を Git に入れない旨の注釈あり）。
  - validate_config: .env および config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数未設定チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 利用）など。
    - `--strict` オプションで警告を FAIL 扱いにするモードを提供。

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標をレポートし、閾値に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）や DB パス指定（--db / 環境変数）をサポート。

- 環境設定読み込み / Settings
  - config.Settings クラスを導入し、環境変数をプロパティ経由で取得。
    - 自動的にプロジェクトルート（.git または pyproject.toml を探索）を判定し、`.env` と `.env.local` をロード（OS 環境変数が優先され、.env.local は上書き可能）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可（テスト用途）。
    - 各種設定プロパティ（DB パス、pid/kill flag パス、閾値、env/log_level 判定等）を提供。
    - `PAPER_FILL_MODE` の検証や `KABUSYS_ENV` の許容値チェックを実装。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに stdout StreamHandler と TimedRotatingFileHandler（デイリーローテーション）を統一的に設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils.process_priority:
    - set_process_priority: Windows/Linux(Mac/FreeBSD 含む) を吸収してプロセス優先度（high/normal/low）を設定（psutil 利用）。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティを追加。
    - 権限不足や未対応 OS の場合はワーニングを出して処理をスキップする堅牢設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重基準の重み計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数を返す関数。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング処理、余剰分の公正配分（端数処理）を実装。
      - cost_buffer を考慮して保守的にコスト見積もりを行う。

- リサーチ / ファクター計算（着手）
  - research.factor_research: DuckDB の prices_daily / raw_financials を使ったファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性、Value 指標を想定）。モジュールは設計・一部実装（ファイル末尾は切れているが計算設計あり）。

### Changed
- 環境変数パースの改善
  - config._parse_env_line により `.env` の行をより正確にパース（クォート対応、export KEY=val 形式、行内コメントの扱い）するように改善。
  - .env ロード時に既存 OS 環境変数を保護するため protected set を導入。

- 起動時の優先処理
  - run_monitoring / run_execution が起動直後にプロセス優先度（high）を設定するようになり、実行開始前にリソース優先度の調整を行う。

### Fixed / Robustness
- ポーリング間隔の耐障害性
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合にデフォルト 60 秒へフォールバックし、警告ログを出力するようにした。
- DB / ファイル操作の堅牢化
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に、プログラムがクラッシュせずコンソールログのみで継続するようにフォールバック処理を追加。
  - SQLite / DuckDB 接続は finally ブロックで確実にクローズするようにした。
- ExecutionEngine 起動前チェック
  - 停止フラグが既に立っている場合は起動を中止して安全に終了するガードを追加。

### Security
- .env の扱いに関する注意書きを config_setup の生成ファイルに追加（.env を絶対に Git にコミットしない旨明記）。

### Documentation / Messages
- 各モジュールに docstring を整備。CLI ヘルプやログメッセージを日本語で記載して運用者向けの説明を充実。

---

その他:
- ファイル・モジュール設計は外部 API への直接アクセスを最小化する方向で分離（リサーチ/ポートフォリオ/実行/監視の責務分離）。
- 一部モジュール（research.factor_research 等）は引き続き実装途中の箇所があり、将来的な拡張（ファクターの詳細計算、銘柄別 lot_size 対応、フォールバック価格取得等）が想定されます。

もし CHANGELOG をさらに詳細化（各ファイルごとの変更元差分推定や、既知の TODO／未実装一覧を含める等）したい場合は、どのレベルの詳細が必要か教えてください。