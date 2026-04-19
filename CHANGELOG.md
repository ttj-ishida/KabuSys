# Changelog

すべての注目すべき変更をこのファイルに記載します。  
このドキュメントは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 各リリースは日付付きでセクション化
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用

---

## [0.1.0] - 2026-04-19

初回リリース。リポジトリの主要機能と CLI / ユーティリティ群を実装。

### Added
- 基本パッケージ設定
  - パッケージバージョン: `__version__ = "0.1.0"` を設定。
  - パッケージエクスポート: portfolio / execution / monitoring 等の公開 API を定義。

- 環境設定・管理
  - `kabusys.config.Settings`：環境変数から各種設定を取得する集中管理クラスを実装。
    - サポートする環境: `development`, `paper_trading`, `live`
    - データベースパス等の既定値を提供（例: `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`）。
    - `PAPER_FILL_MODE` のバリデーション（`instant|partial|never|reject`）。
    - `KILL_FLAG_CLEAR_ON_START` 等の運用用フラグをサポート。
  - 自動 .env 読み込み機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み。
    - OS 環境変数は上書きされないよう保護。

- 対話式設定ウィザード
  - `kabusys.config_setup`：.env を対話的に生成・更新する CLI を実装。
    - シークレット入力の扱い、選択肢・デフォルト値、保存確認をサポート。
    - `.env` 書き込みテンプレートを定義（Git へコミットしない旨の注意を追記）。

- 設定検証ツール
  - `kabusys.validate_config`：起動前に環境変数・config/*.yaml を検証する CLI を実装。
    - 必須環境変数のチェック（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告。
    - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - `run_monitoring.py`：
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。0以下や不正値はデフォルトへフォールバック。
    - 監視は環境に関わらず本番（`sqlite_path`）を使用して監視テーブルを初期化。
    - 停止フラグファイル（`data/stop_requested.flag`）を検出してループを終了。
    - プロセス優先度を最初に High に設定。
  - `run_execution.py`：
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB と分離）。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ・PID ファイル管理、スレッドでのエンジン実行・監視を実装。
    - RiskConfig による初期リスク制限設定（例: max_position_pct=0.20, max_utilization=0.80, initial_portfolio_value を broker.get_available_cash() で初期化）。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`：
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 設定を提供（psutil ベース）。
    - 権限不足等の例外は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier）。
    - 不明セクターはブロック対象外、未知レジームは 1.0 でフォールバック（警告ログ）。
  - `kabusys.portfolio.position_sizing`：
    - allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元株（lot_size）で丸め、aggregate cap（available_cash）超過時のスケーリングと残余配分ロジックを実装。
    - cost_buffer を考慮した保守的なコスト推定をサポート。
    - TODO: 将来的に銘柄別 lot_size をサポートする旨の注記。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`：DuckDB 経由で価格テーブル / 財務データを参照し、Momentum/Value/Volatility/Liquidity 系ファクターを計算する設計を追加（calc_momentum 等の実装を含む）。（注: ファイル末尾が未完の可能性あり。詳細は実装箇所参照）

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ等を集計して検証レポートを生成する CLI を実装。
    - 閾値（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）と DB パス（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 計算実装と NULL/データ不足ハンドリングを実装。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

## 既知の注意点 / TODO（コードコメントより推測）
- position_sizing: 銘柄別の単元株（lot_size）を将来的にサポートする予定（TODOコメント）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小見積もられる可能性あり。前日終値等のフォールバック価格を使う改善が検討されている。
- factor_research.py: ファイル末尾に未完成の記述（calc_momentum の続きが欠落）と思われる箇所があるため、実装完了が必要。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（テスト環境などで意図しない挙動になる可能性）。
- ログディレクトリ作成に失敗した際はファイルロギングが無効になり、標準出力のみで継続する挙動に注意。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告でスキップされる。

---

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴に基づくものではないため、実装詳細や日付は推定値を含みます。