# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
このファイルはコードの現状（ソースコードから推測）に基づいて作成した変更履歴です。

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-19

初回リリース（コードベースの初期実装をまとめたもの）。主な追加点・設計上の注意点は以下の通りです。

### Added
- 全体
  - パッケージ初版を追加。パッケージメタ情報は `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。
  - DuckDB/SQLite ベースのローカルデータ保存を前提とした設計。
- 設定管理
  - 環境変数・.env の読み込み・管理機能を追加（`src/kabusys/config.py`）。
    - プロジェクトルートを `.git` または `pyproject.toml` から自動検出して `.env` / `.env.local` を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可）。
    - 複雑な .env パース実装（export プレフィックス、クォート内エスケープ、インラインコメント対応）。
    - 必須環境変数チェックユーティリティ `_require` と Settings クラスによるプロパティベースの設定取得を提供（J-Quants、kabu API、DB パス、監視閾値など）。
    - Paper Trading 用の `PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH` 等の設定をサポート。
- 設定支援 CLI
  - 対話式環境設定ウィザード `config_setup.py` を追加。`.env` の初期作成／更新をサポート。
  - 設定検証 CLI `validate_config.py` を追加。必須環境変数や config/*.yaml の存在・簡易パースチェック（PyYAML がなくても警告発行）を実行可能。`--strict` オプションで警告を失敗扱いにできる。
- 実行スクリプト / 実行環境制御
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は mock ブローカーを使用し、paper trading 用 DB（`data/paper_trading.db` がデフォルト）に完全に分離して記録する。
    - 実行中の PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止などを実装。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番用の `sqlite_path` を使用する（監視 DB を常に同じにする設計）。
    - 停止フラグの検知によるループ終了処理、エラー隔離（check_once 内エラーは例外ログを吐いて次ポーリングへ）を実装。
- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ `utils/logging_setup.py` を追加。
    - stdout へ出力する StreamHandler と、日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
  - プロセス優先度・CPU affinity 設定ユーティリティ `utils/process_priority.py` を追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収して `set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity` によるコア固定機能も提供。権限不足や未対応環境では安全に警告を出してスキップする。
- ポートフォリオ構築モジュール
  - `portfolio` パッケージを追加（純粋関数群、DB 参照なし）。
    - `portfolio_builder.py`: 候補選定・重み計算（等分配・スコア加重。全銘柄スコアが 0 の場合は等分配へフォールバック）。
    - `risk_adjustment.py`: セクター集中制限（セクター不明は制限対象外）とレジーム乗数（bull/neutral/bear のマップ、未知レジームは警告して 1.0 でフォールバック）。
    - `position_sizing.py`: 銘柄別発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと残差配分ロジック、コストバッファ（手数料・スリッページ見積り）考慮。
  - `portfolio/__init__.py` で主要関数を公開。
- 研究 / ファクター計算
  - `research/factor_research.py` の骨組みを追加（DuckDB 接続で prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計）。
- ツール
  - Paper Trading の検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - `--from` / `--to` / `--db` オプションで期間・DB 指定が可能。環境変数 `PAPER_TRADING_SQLITE_PATH` を優先して参照。
    - 関連閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）が組み込み。
- 監視用 DB 初期化ユーティリティ
  - `monitoring/monitoring_db.py`（スクリプトから import され使用）により監視テーブルの初期化を保証（冪等）。run_execution/run_monitoring から起動時に呼び出される。

### Changed
- （初版のため特に変更履歴は無し）

### Fixed
- （初版のため特に修正履歴は無し）

### Notes / Breaking changes / 注意点
- 監視（run_monitoring）は「環境にかかわらず」本番用の `sqlite_path` を使用する設計になっています。監視データを分離したい場合は設定を確認してください。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は mock ブローカーと専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離されます。
- `.env` の自動読み込みはデフォルトで有効。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログディレクトリの作成失敗やプロセス優先度設定の失敗は致命的エラーにならず、警告を出してフォールバックする設計です（権限不足などを考慮）。
- `PAPER_FILL_MODE`、`KILL_FLAG_CLEAR_ON_START` 等の環境変数に不正値が設定されていると例外を投げる／警告する箇所があります。`validate_config.py` を先に実行して設定整合性を確認することを推奨します。
- position sizing のロジックは単元株（lot_size）や price 欠損時の挙動に注意。price が 0/欠落していると銘柄がスキップされます（将来的にフォールバック価格の検討コメントあり）。

### Security
- シークレット値（J-Quants リフレッシュトークン、kabu API パスワードなど）は `.env` に保存し Git にコミットしないよう注意喚起をドキュメント化（`config_setup.py` で .env にコミットしない旨のヘッダを出力）。

---

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース履歴や日付、細かい変更点は実際の VCS の履歴に基づいて調整してください。）