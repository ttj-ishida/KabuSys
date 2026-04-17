# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能とユーティリティを実装しています。

### Added

- 実行スクリプト / ランタイム
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する仕様（監視データは本番 DB に保存）。
    - stop フラグファイル（data/stop_requested.flag）検知で安全終了。
    - check_once() 実行時の例外をログ出力してループ継続する耐障害性を実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中は PID ファイルを書き、data/stop_requested.flag によりセッション停止を可能にする。
    - スレッドで engine.run_session を実行し、stop フラグで安全に engine.stop() を呼ぶ制御を実装。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から型付きの設定を取得する API を提供。
    - .env 自動読み込み機能を実装（OS 環境変数の優先、.env.local が .env を上書き）。
    - POJO ライクなプロパティ: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk thresholds, env/log_level 判定など。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値、選択肢、シークレット入力、既存 .env の読み込み／再利用をサポート。
    - 書き出しテンプレート（コメント付き）を生成。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の設定整合性を事前検証する CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML の有無に応じた YAML 検証のスキップ／実行。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター集中をチェックし、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数 (bull/neutral/bear) を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）で丸め、max_position_pct・max_utilization による制限、cost_buffer を用いた保守的なコスト見積・スケーリングを実装。
    - aggregate cap 超過時にスケールダウンし、残余資金を用いた再配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いて Momentum / Volatility 等のファクターを計算する関数を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR / 平均売買代金 / 出来高比率等を計算（部分窓対応、データ不足時は None を返す）。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）を追加。psutil を利用し、権限不足等は警告でスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定するユーティリティを追加（未対応プラットフォームや権限不足は警告でスキップ）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite からリポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、日付フィルタ、閾値判定（デフォルト: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を実装。

### Changed

- ログ・挙動
  - run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを追加）。
  - Settings による設定取得は厳格なバリデーションを行い、不正な環境変数は ValueError を発生させる（起動前に validate_config によるチェック推奨）。
  - .env 自動読み込みの優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

- データベース接続
  - 監視 (run_monitoring) は常に sqlite_path（本番監視 DB）を使用する仕様に明確化。
  - run_execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離する仕様を明示。

### Fixed / Improved

- .env パーサ
  - _parse_env_line: export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等を正しく処理するように改善。
  - _load_env_file: ファイル読み込み失敗時は警告を出して処理を継続する（堅牢化）。

- フォールバック / 安全弁
  - calc_score_weights: 全銘柄のスコアが 0 の場合は等金額配分にフォールバックして警告を出す。
  - calc_regime_multiplier: 未知のレジーム文字列が来た場合は 1.0 にフォールバックして警告を出す。
  - process_priority / cpu_affinity 設定は権限不足や未実装の API を検出した場合に警告でスキップするようにして、起動失敗しないように改善。

- CLI の堅牢性
  - validate_config: PyYAML が未インストールの場合は YAML 内容検証をスキップし、警告を出す。
  - paper_verification_report: 対象 DB が存在しない場合にわかりやすいエラーメッセージを出力して終了する。

### Documentation / Meta

- パッケージバージョンを __version__ = "0.1.0" として設定。
- package __all__ を設定して主要サブパッケージをエクスポート。

### Security

- 環境変数取り扱いに関して、.env ファイル生成時に強く注意を促すヘッダを付与（.env を絶対に Git にコミットしない旨を明記）。

## 未記載の注意点（実装上の挙動）

- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下や非数を与えた場合、警告を出してデフォルト 60 秒を使用します。
- position_sizing の価格欠損時の扱いについて TODO コメントが残っており、将来的なフォールバック（前日終値等）の導入を想定しています。
- 一部モジュールは外部パッケージ（psutil, duckdb, PyYAML）を使用しており、実行環境にインストールされていることを前提とします。

---

（注）上記は提供されたコードベースの内容から推測してまとめた変更履歴です。実際のコミット履歴や changelog エントリが存在する場合はそれに基づいて更新してください。