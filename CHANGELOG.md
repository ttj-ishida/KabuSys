# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
初版リリースの内容をコードベースから推測して記載しています。

全般的な注意
- 本プロジェクトのバージョンは src/kabusys/__init__.py にて `0.1.0` として定義されています。
- 日付は本解析時点（2026-04-21）をリリース日として記載しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-21

### Added
- 基本フレームワーク・ユーティリティ
  - 環境設定 / 読み込み機能を提供する `kabusys.config` を追加
    - .env 自動読み込み（プロジェクトルートを `.git` または `pyproject.toml` で検出）
    - .env の構文解析で `export KEY=val`、シングル/ダブルクォート、エスケープ、行内コメント処理をサポート
    - 必須環境変数取得ヘルパー `_require` と各種設定プロパティ（DB パス、API トークン、運用環境フラグ等）
    - `PAPER_FILL_MODE` のバリデーション（有効値: "instant","partial","never","reject"）
  - 環境設定ウィザード CLI `kabusys.config_setup`
    - 対話式に .env を作成/更新するウィザードを実装
    - 秘匿項目はマスク表示、.env 書き込みテンプレートを提供
  - 起動前設定検証 CLI `kabusys.validate_config`
    - 必須環境変数、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース（PyYAML 未導入時はスキップ）等を検証
    - `--strict` オプションで警告も失敗扱いにできる
  - ログ設定ユーティリティ `kabusys.utils.logging_setup`
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一的なログ設定を提供
    - ログレベル・ログディレクトリは引数 / 環境変数で制御可能、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority`
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定
    - CPU affinity を先頭 N コアへ固定するヘルパーを提供
    - 権限不足や未対応 OS に対する安全なフォールバックと警告を実装

- 実行/監視用エントリスクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、ブローカークライアント生成、ExecutionEngine のスレッド実行／停止監視）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離
    - 起動時に停止フラグ（data/stop_requested.flag）があれば起動を行わない
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告後デフォルトにフォールバック）
    - 監視は環境にかかわらず本番の sqlite_path を使用（監視データは本番監視 DB へ格納）
    - 停止フラグの検知でループを終了

- ポートフォリオ構築関連の純粋関数群（DB非依存）
  - `kabusys.portfolio.portfolio_builder`
    - BUY シグナル選定 (`select_candidates`) と重み計算 (`calc_equal_weights`, `calc_score_weights`)
    - スコア全ゼロ時に等金額配分へフォールバックして警告を出す
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限適用 (`apply_sector_cap`)
      - 当日売却予定銘柄をエクスポージャー計算から除外
      - "unknown" セクターはセクター上限制限を適用しない
    - 市場レジームに基づく投下資金乗数 (`calc_regime_multiplier`)
      - "bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバック（警告ログ）
  - `kabusys.portfolio.position_sizing`
    - 各種配分方式（risk_based / equal / score）に基づく株数算出ロジック
    - 単元株（lot_size）丸め、1銘柄上限、総投下資金（available_cash）に対する aggregate cap スケールダウンと残差処理を実装
    - 手数料・スリッページの見積り係数（cost_buffer）を考慮した保守的見積り

- 研究・解析基盤
  - `kabusys.research.factor_research`（ファクター計算の基盤を追加）
    - モメンタム、移動平均、ATR、出来高等の計算方針を定義（DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計）
    - （注意）ソースは途中まで実装されている（ファイル末尾で途中切れが見られるため、今後継続実装予定）

- ツールスクリプト
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用検証レポート生成スクリプト
    - SQLite（デフォルト `data/paper_trading.db` or 環境変数 PAPER_TRADING_SQLITE_PATH / --db）から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を評価
    - 判定閾値（例: 稼働率 >= 99.0%、注文成功率 >= 90%、P95 <= 200 ms）を定義し PASS/FAIL を出力

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- `.env` の取り扱いに関する注意喚起を config_setup のヘッダに明記（.env を絶対にバージョン管理にコミットしないこと）

開発上のメモ（コードからの推測）
- Execution / Monitoring は stop flag ファイル（data/stop_requested.flag）や pid ファイルを介して外部からの停止制御を受け付ける設計になっている。
- paper_trading モードでは発注処理を完全に本番 DB から分離する設計（MockBrokerClient と専用 SQLite）を採用している。
- ロギングは stdout を主要出力とし、ログファイルは存在すれば日次ローテーションで保存する設計。ログディレクトリ作成失敗時も起動続行されるため自動化ジョブ環境での堅牢性を考慮している。
- process_priority / cpu_affinity は権限や OS に依存する操作であるため失敗時も例外を投げずに警告で済ませるフォールバックを用意している。

もし特定のファイルや機能ごとにさらに詳細な変更履歴（例: 関数単位の変更点や TODO / 未実装箇所）を希望される場合は、その対象を教えてください。コードを参照して追記します。