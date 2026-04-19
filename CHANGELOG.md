# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルではリポジトリの現状から推測できる機能追加・仕様・既知の制約をまとめています。

全般的なルール:
- バージョンは `src/kabusys/__init__.py` の __version__ に合わせています。
- 日付は本コードベース取得日（2026-04-19）を使用しています。

## [Unreleased]
（現在のブランチに対する未リリースの小変更・修正があればここに追記してください）

## [0.1.0] - 2026-04-19
初期リリース（推測）。主に自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築、設定管理、および診断ツールを実装。

### Added
- 基本メタ
  - パッケージバージョンを `0.1.0` として設定（src/kabusys/__init__.py）。
  - パッケージトップレベルのエクスポートを定義（data, strategy, execution, monitoring）。

- 起動スクリプト / 実行制御
  - run_monitoring.py: SystemMonitor のポーリングループを起動する CLI スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御にプロジェクト内の `data/stop_requested.flag` を使用。
    - Monitoring は KABUSYS_ENV にかかわらず本番（設定された）sqlite_path を使用する挙動を明示。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine（取引実行エンジン）起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、paper_trading 専用 DB（`data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動/停止のための `data/stop_requested.flag` と PID ファイル (`data/execution.pid`) の利用。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止する制御を実装。

- 設定管理 / ユーティリティ
  - config.py: 環境設定管理クラス `Settings` を提供。
    - `.env` 自動ロード（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - `.env.local` による上書き、OS 環境変数保護、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。
    - 各種設定プロパティを定義（J-Quants, kabu API, LINE, DuckDB/SQLite パス、paper trading 設定、監視しきい値、ログ設定等）。
    - 値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）を実装。
  - config_setup.py: 対話式ウィザードにより `.env` を作成・更新する CLI を追加。
    - 項目一覧と説明・デフォルトを用意し、既存値の読み取り・マスク表示・保存までをサポート。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、`config/*.yaml` の存在／YAML パース検証（PyYAML がインストールされている場合）等を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを提供。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。日数保持は 30 日。
    - 既存ハンドラのクリア、ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを提供。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収し、"high"/"normal"/"low" の指定で優先度を設定。
    - `set_cpu_affinity` により先頭 N コアにピン留め可能。アクセス権限や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を防ぐための候補フィルタ（既存保有をセクター別に時価換算して上限を超えるセクターの新規を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた投下資金乗数を返す（unknown は 1.0 にフォールバックし警告）。
    - 既知の注意点: price が欠損した場合の扱い（今後の改善 TODO）を注記。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を決定（allocation_method: "risk_based","equal","score" をサポート）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap に基づくスケールダウン、cost_buffer を用いた保守的見積り、余り再配分ロジックを実装。
    - TODO: 銘柄別 lot_size を将来的にサポートする旨の注記。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成コマンドを追加（期間指定 --from/--to、DB パス指定 --db）。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定（閾値はソース内に定義）。
    - レポートは SQLite（paper_trading DB）を直接参照。P95 の算出や日付フィルタの実装を含む。

- 研究用モジュール（断片的に実装）
  - research/factor_research.py:
    - DuckDB 接続を受け取り、momentum 等のファクターを計算する設計を導入（関数の骨格と定数を実装）。（ファイル末尾は切れているため一部未完）

### Changed
- （初期リリースのため大きな互換性破壊変更は無し。実装の設計上の決定をドキュメントに反映）
  - Monitoring と Execution の DB の使い分けを明確化:
    - Monitoring は常に設定された sqlite_path（本番監視用 DB）を利用。
    - Execution は `KABUSYS_ENV=paper_trading` の場合に専用の paper_sqlite_path を使用し本番 DB と分離。

### Fixed
- 設定読み込みに関する頑健性向上:
  - .env パーサでクォート付き値のエスケープ処理やインラインコメントの扱い、`export KEY=val` 形式のサポートを追加。これにより .env の多様な記法に耐える。

### Security
- .env の扱いに関する注意:
  - config_setup.py が生成する .env コメントヘッダに「.env は絶対に Git にコミットしないこと」と明示。

### Notes / Known limitations / TODO
- research/factor_research.py はファイル末尾が途切れており、モメンタム計算の完全実装が未完の可能性あり（実装の続きが必要）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる課題あり。将来的に前日終値等でフォールバックする検討を注記。
- position_sizing: 銘柄ごとの単元（lot_size）を銘柄マスタで管理する拡張が TODO。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでは警告してスキップする実装。運用環境での動作確認を推奨。
- validate_config: PyYAML が未インストールの場合は YAML の内容検証をスキップするため、可能なら依存を入れておくことを推奨。

---

この CHANGELOG はソースコードの実装・コメントから推測して作成しています。実際のリリースノートとして正式に使用する場合は、差分コミットメッセージや開発者による確認をもとに調整してください。