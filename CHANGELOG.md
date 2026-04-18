# Changelog

すべての注記は Keep a Changelog の形式に従います。  
想定される変更点は、提供されたコードベースの実装内容から推測して記載しています。

全般的な注記:
- 環境変数や外部依存（psutil, duckdb, PyYAML 等）に対するフォールバックや例外処理が多数実装されており、開発・本番・検証環境での安全な起動を意図した設計になっています。
- ロギング・プロセス優先度・DB パス・.env の自動読込など運用周りのユーティリティが充実しています。

## [Unreleased]

### Added
- 起動用スクリプト
  - run_execution.py を追加。ExecutionEngine 起動フロー（プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、各種コンポーネント組み立て、スレッド実行 / 停止フラグ対応）を実装。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用の SQLite（data/paper_trading.db を想定）を使用する。
    - 起動時に停止フラグ（data/stop_requested.flag）を検知した場合は起動をスキップする挙動を実装。
  - run_monitoring.py を追加。SystemMonitor のポーリングループを実装。
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用する旨を明示。

- 設定・環境関連
  - config.py を追加。.env 自動ロード機能（.env / .env.local、OS 環境変数の保護）と、Settings クラスによる環境変数の取得・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env 行のパースで export プレフィックスやクォート、エスケープ、インラインコメント（空白前の # をコメント扱い）などを考慮。
  - config_setup.py を追加。対話式ウィザードで .env を作成・更新する CLI を実装（シークレット入力のマスク、デフォルト値、確認プロンプト、ファイル書き出し）。
  - validate_config.py を追加。起動前に必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）などを検証する CLI を実装。--strict オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する。
  - utils/process_priority.py を追加。Windows / POSIX（Linux/Mac等）に跨るプロセス優先度設定（high/normal/low）、および CPU affinity 設定ユーティリティを実装。psutil の例外（権限不足等）を安全にハンドル。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外するロジック。
    - レジームに応じた乗数（calc_regime_multiplier）: bull/neutral/bear に応じた投下資金乗数を実装（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method 別（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - lot_size（単元株）考慮、max_position_pct・max_utilization・cost_buffer（手数料/スリッページ見積）を取り入れた aggregate cap スケーリング、端数配分の再配分ロジックを実装。

- リサーチ / ファクター計算（骨組み）
  - research/factor_research.py を追加（モメンタム等ファクター計算の骨組みと定数を定義）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標（稼働率、注文成功率/送信率、リスク却下、レイテンシ P95 等）を集計して検証レポートを生成。閾値に基づいて PASS/FAIL を判定する。

### Changed
- 起動スクリプト・モジュールのログ挙動を統一するため、各スクリプトは setup_logging(app_name=...) を最初に呼ぶように設計。
- run_execution と run_monitoring は起動直後に set_process_priority("high") を呼んで優先度を上げる運用方針を採用。

### Fixed / Robustness
- .env 読み込み処理で以下に対応
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント判定などを考慮して正確にパース。
  - ファイル読み込み失敗時は警告を出して処理を継続。
- ログディレクトリ作成やファイルハンドラ作成失敗時に備え、コンソール出力のみで継続するフォールバックを実装。
- psutil による優先度 / affinity 設定で権限不足や未実装の機能が発生しても例外を握り潰さず警告ログを出して安全にスキップするようにした。
- validate_config で PyYAML 未導入時は YAML 内容検証をスキップしつつ警告を出すように変更。

---

## [0.1.0] - 2026-04-18

初回公開リリース。上記の機能群を含む最初の安定版リリースと想定。

### Added
- 基本的なアーキテクチャと CLI
  - Execution エンジン起動スクリプト（run_execution.py）
  - Monitoring ポーリング起動スクリプト（run_monitoring.py）
  - 設定ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
- 設定管理
  - Settings クラスによる環境変数取得・バリデーション（config.py）
  - .env 自動読み込み（.env / .env.local、OS 環境変数保護）
- ロギング & プロセス管理
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）
- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算（portfolio/portfolio_builder.py）
  - セクター制限・レジーム乗数（portfolio/risk_adjustment.py）
  - ポジションサイズ計算（portfolio/position_sizing.py）
- リサーチ / ツール
  - ファクター計算の骨組み（research/factor_research.py）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）
- パッケージ化
  - パッケージの __version__ を 0.1.0 に設定（src/kabusys/__init__.py）

### Notes / Known limitations
- research/factor_research.py は関数実装（calc_momentum 等）の一部が継続実装中（骨組みあり）。DuckDB を用いた実データ計算を前提としているため、テーブルが揃っていない環境ではエラーやデータ不足が発生する可能性あり。
- position_sizing の価格フォールバック（price 欠損時の補完）について TODO コメントあり。価格欠損時は現状スキップとなるため保守的な挙動。
- モニタリング・エンジンは停止フラグ（data/stop_requested.flag）ファイルを用いるシンプルな停止制御を採用。外部シグナルやプロセスマネージャ連携は個別運用で対応が必要。

---

過去のリリースや追加の変更要求があれば、実装箇所（ファイル名/関数名）を指定していただければ、より詳細な差分推定や今後の変更履歴案を作成します。