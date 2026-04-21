# Changelog

すべての重大な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

最新の変更は常に上に記載します。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-21

初期リリース。以下の主要機能とユーティリティを含みます。

### Added（追加）
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 環境設定・ロード
  - .env 自動読み込み機能を追加（プロジェクトルート検出に .git / pyproject.toml を使用）。OS 環境変数を保護して読み込み順序を制御（`.env` → `.env.local`、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。(src/kabusys/config.py)
  - .env パース機能強化：コメント処理、クォート文字列のエスケープ対応、`export KEY=val` 形式に対応。（src/kabusys/config.py）
  - Settings クラスを追加し、アプリ全体で利用する設定プロパティを提供（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連など）。入力検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）を実装。（src/kabusys/config.py）

- 環境設定ウィザード CLI
  - 対話式に .env を作成・更新する `config_setup` CLI を追加。シークレット項目のマスク、既存 .env 読み込み、保存前確認などを実装。（src/kabusys/config_setup.py）

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の整合性をチェックする `validate_config` CLI を追加。必須環境変数チェック、パス（DB）存在チェック、YAML パース（PyYAML がある場合）等を行い、`--strict` で警告を失敗扱いにできる。（src/kabusys/validate_config.py）

- ログ設定ユーティリティ
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する `setup_logging` を追加。ログディレクトリ作成失敗時のフォールバック動作やログレベル解決順を実装。（src/kabusys/utils/logging_setup.py）

- プロセス優先度ユーティリティ
  - Windows / POSIX を吸収する `set_process_priority` および `set_cpu_affinity` を追加（psutil利用）。アクセス権限不足等のフォールバックを考慮。（src/kabusys/utils/process_priority.py）

- 実行・監視エントリスクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。Paper Trading 環境（KABUSYS_ENV=paper_trading）では専用の SQLite（`data/paper_trading.db`）を使用する挙動を実装。BrokerClientFactory を使った Broker クライアント生成、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て、PID ファイル・停止フラグ対応、スレッドでのエンジン実行管理を実装。（src/kabusys/run_execution.py）
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様、停止フラグによる終了、例外を握り潰さずログ出力してループ継続する仕組みを実装。（src/kabusys/run_monitoring.py）

- Portfolio コンストラクション
  - 候補選定・重み計算モジュールを追加（等金額・スコア加重、候補選択）。スコアが全て 0 の場合のフォールバックを実装。（src/kabusys/portfolio/portfolio_builder.py, src/kabusys/portfolio/__init__.py）
  - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。unknown セクターの扱いやレジーム不明時のフォールバックを記載。（src/kabusys/portfolio/risk_adjustment.py）
  - ポジションサイジング（calc_position_sizes）を追加。allocation_method（"risk_based" / "equal" / "score"）対応、単元（lot_size）での丸め、1銘柄上限・集約上限（aggregate cap）や手数料バッファ（cost_buffer）を考慮したスケーリング・残差処理を実装。（src/kabusys/portfolio/position_sizing.py）

- Paper Trading 検証ツール
  - paper_trading の実行結果を集計してレポート（稼働率、注文成功率、送信率、レイテンシ P95 等）を標準出力に出す `paper_verification_report` を追加。デフォルト DB パスは `data/paper_trading.db`。P95 計算、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。（src/kabusys/tools/paper_verification_report.py）

- Research（雛形）
  - ファクター計算モジュール（calc_momentum 等の雛形）を追加。DuckDB 接続を受け取り prices_daily 等のテーブルを参照してファクターを算出する設計。主要定数や設計方針を文書化。（src/kabusys/research/factor_research.py）

- その他ユーティリティ・DB周り
  - DuckDB/SQLite の接続を各スクリプトから利用する設計（monitoring/実行で利用）。
  - 監視 DB の初期化ユーティリティ呼び出し（init_monitoring_db）を実行開始時に行う（冪等）。（複数スクリプトで利用）

### Changed（変更）
- ログ出力先を stdout に統一（StreamHandler）。cron / スケジューラからの起動で扱いやすいよう stderr ではなく stdout を使用。（src/kabusys/utils/logging_setup.py）
- .env の読み込み順を明確化：OS 環境 > .env.local(上書き) > .env（未指定キーのみ）。既存 OS 環境は保護される。（src/kabusys/config.py）

### Fixed（修正）
- process_priority のプラットフォーム互換性向上と例外ハンドリングを実装（設定失敗時に警告を出して継続）。（src/kabusys/utils/process_priority.py）
- ログディレクトリ作成失敗時の堅牢性強化（ファイル出力の無効化とコンソールへの警告）。（src/kabusys/utils/logging_setup.py）
- position sizing における集約スケーリングでの端数処理（lot_size 単位の残差処理）を実装し、再現性ある配分を行うよう改善。（src/kabusys/portfolio/position_sizing.py）

### Deprecated（非推奨）
- 特になし。

### Security（セキュリティ）
- シークレット値（J-Quants トークン・kabu API パスワード等）は .env に保持し、config_setup ではマスク表示。環境変数未設定時はエラーになるためデフォルトのプレースホルダを利用しないことを推奨。（src/kabusys/config.py, src/kabusys/config_setup.py）

---

注:
- 上記はソースコードの実装内容から推測してまとめた初期リリースの変更履歴です。実際のリリースノート作成時には、差分コミットや実際のリリース日・リリース番号に合わせて調整してください。