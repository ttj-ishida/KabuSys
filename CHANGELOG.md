# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
初版リリースはパッケージのコード構成と実装から推測して記載しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: そのリリースで追加・変更・修正された主な事項

---

## [Unreleased]

- なし（現行コードベースでは未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージ名: KabuSys
  - バージョン情報: `__version__ = "0.1.0"`

- 環境/設定管理
  - Settings クラスによる環境変数ラッパー（`kabusys.config.Settings`）。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境判定等）。
    - `KABUSYS_ENV`（development / paper_trading / live）および `LOG_LEVEL` の検証を実装。
  - 自動 .env 読み込み機構
    - プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を読み込む。
    - OS 環境変数を保護する仕組み（`.env.local` は上書き可能だが OS 環境変数は保護）。
    - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env パーサ実装（`_parse_env_line`）
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - 行内コメントの扱い（クォート有無での振る舞い差分）を考慮。

- 起動スクリプト
  - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）
    - process priority を高優先度に設定してから起動。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを作成。
    - ExecutionEngine、OrderManager、RiskManager、Reconciler 等の組み立てとスレッド実行制御を実装。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイルの扱いを実装。
  - 監視ループ起動スクリプト（`src/kabusys/run_monitoring.py`）
    - SystemMonitor を用いたポーリングループを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視は本番 DB の利用を想定）。
    - 停止フラグの検出と例外ハンドリングを実装。

- ログ/プロセスユーティリティ
  - 統一ロギング設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app>.log`、30 日保持）をルートロガーに設定。
    - ログディレクトリの自動作成、失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `INFO`。
  - プロセス優先度 / CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows / POSIX (Linux, macOS, FreeBSD) を吸収して nice / priority を設定。
    - `set_cpu_affinity` によりプロセスを最初の N コアに固定可能（権限不足等はワーニングでスキップ）。
    - psutil を利用。権限不足や未対応 OS でのフォールバック処理あり。

- ポートフォリオ構築ライブラリ（pure functions）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定: `select_candidates`（スコア降順、同点は signal_rank 小さい方を優先）
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコアが全て 0 の場合は等金額にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限: `apply_sector_cap`（既存保有比率が上限を超えるセクターの新規候補を除外）
    - レジームに応じた資金乗数: `calc_regime_multiplier`（bull/neutral/bear をマッピング）
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算: `calc_position_sizes`
      - allocation_method による分岐（risk_based / equal / score）
      - 単元（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積り
      - 残差配分ロジック（fractional remainder に基づき lot_size 単位で追加配分）

- 研究・ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB 接続を受け、prices_daily / raw_financials から Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計（関数化、パラメータ定義）。（実装途中ファイルあり）

- CLI / ツール
  - 設定検証 CLI（`kabusys.validate_config`）
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証、live 環境向けの追加警告を実装。
    - `--strict` オプションで警告も失敗扱い（exit 1）。
  - 環境設定ウィザード（`kabusys.config_setup`）
    - 対話式に .env を生成・更新するウィザード。シークレット項目はマスク表示。保存前に確認を促す。
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）
    - paper_trading 用 SQLite からシステム稼働率、注文成功率 / 送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してレポート出力。
    - 判定基準（デフォルト）: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

### Changed
- 新規初期実装のため該当なし。

### Fixed
- 新規初期実装のため該当なし。

### Security
- 機密情報（トークンやパスワード）は .env およびウィザードでシークレット扱い（表示マスク）。  
  ただし .env を絶対に Git にコミットしない旨のコメントを .env 生成テンプレートに明記。

### Notes / Known limitations / TODO
- `kabusys.research.factor_research` の実装がファイル末尾で途中終了している（未完）。  
  - 実際のファクター計算ロジックや SQL の完成が必要。
- `apply_sector_cap` 内で価格が 0.0 の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり：前日終値や取得原価などのフォールバック価格を検討する必要あり。
- `position_sizing`:
  - 銘柄別の lot_size をサポートする拡張（現状は単一 lot_size）が将来の TODO。
- プロセス優先度 / CPU affinity の設定は権限不足や OS 非対応時にスキップされる実装。運用環境での動作確認を推奨。
- ログファイル出力はログディレクトリ作成に失敗した場合は自動的に無効化され、コンソールのみとなる。ログディレクトリ権限を事前確認すること。

---

参考: 主なデフォルトパス / 環境変数
- DuckDB: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）
- SQLite (監視): `SQLITE_PATH`（デフォルト: data/monitoring.db）
- Paper Trading SQLite: `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）
- ログディレクトリ: 環境変数 `LOG_DIR` または `logs/`
- ポーリング間隔: `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）
- 自動 .env 読み込みを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

（本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリース履歴や変更履歴が別途存在する場合は、それに合わせて修正してください。）