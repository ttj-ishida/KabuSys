# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の書式に準拠しています。

全般方針:
- バージョンはパッケージ内の __version__（現在 0.1.0）に合わせています。
- 日付は本リリース作成日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初回公開リリース。

### 追加 (Added)
- 基本アプリケーション
  - package: KabuSys — 日本株自動売買システムの骨子を実装。
  - バージョン情報を __init__.py にて管理（__version__ = "0.1.0"）。

- 設定管理
  - kabusys.config: 環境変数／.env 自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。
    - OS 環境変数を保護する仕組み（.env の上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
    - 必須環境変数取得ヘルパー（_require）と多数の設定プロパティ（DB パス、API トークン、Paper Trading 設定、閾値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。

- 設定支援ツール
  - kabusys.config_setup: 対話式 .env ウィザードを追加。
    - 初期作成・更新を支援する CLI（キー説明、デフォルト、シークレットマスク、保存機能）。
    - .env の生成時にコミットしない注意文を出力。

- 設定検証ツール
  - kabusys.validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数確認、KABUSYS_ENV の検証、LOG_LEVEL の検証、DB パス（親ディレクトリ）チェック。
    - config/*.yaml の存在確認および PyYAML がある場合はパース検証。
    - KABUSYS_ENV=live に対する追加ガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高く設定するユーティリティ呼び出しを含む。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成（paper/live に応じた実装想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組立て ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルを利用した制御。
    - RiskConfig の初期デフォルトをソース内で設定（max_position_pct 等、initial_portfolio_value は broker.get_available_cash() から初期化）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、不正値は警告してデフォルト使用）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop flag による終了、例外時のログ出力、KeyboardInterrupt 対応。

- 監視・DB 初期化
  - monitoring.monitoring_db: run_* スクリプトから呼ばれる監視 DB 初期化ロジックを追加（冪等にテーブル作成を保証）。

- ロギングとプロセス制御ユーティリティ
  - kabusys.utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定する共通ユーティリティを追加。
    - ログレベルとログディレクトリの解決順を導入（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ動作。
  - kabusys.utils.process_priority:
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分吸収実装（psutil 利用、アクセス拒否等の例外は警告でスキップ）。

- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選出する関数。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装（全スコア 0 の場合は等配分にフォールバックして警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を実装（既存保有のセクター比率が上限を超える場合は新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知のレジームは警告を出して 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: 発注株数算出の主要アルゴリズムを実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: リスクパーセンテージ・stop_loss を元に株数を計算。
      - 等配/スコア配分: weight と price から target_shares を算出。
      - 単元株（lot_size）で丸め、max_position_pct による per-stock cap を適用。
      - aggregate cap（available_cash）を超えるとスケールダウンし、残余を fractional remainder によって lot 単位で再配分する（再現性確保のためソート順を安定化）。
      - cost_buffer による保守的見積りをサポート。
      - TODO コメントに将来の銘柄別 lot_size 拡張案を記載。

- Research / ファクター計算
  - kabusys.research.factor_research: DuckDB 接続を利用したファクター計算モジュールを追加。
    - Momentum / Value / Volatility / Liquidity 等の計算方針を定義。prices_daily/raw_financials テーブル参照で外部 API に依存しない設計。
    - （注）ファイルは設計コメントと関数 skeleton を含む（calc_momentum 等の実装冒頭あり）。

- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading の検証レポート生成ツールを実装。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH でオーバーライド可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算。
    - Pass/Fail 判定基準を実装（稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。

- その他
  - data ディレクトリでの stop_requested.flag / execution.pid / kill.flag 等のファイルベースによる外部制御サポートを導入。

### 変更 (Changed)
（初回リリースのため該当なし）

### 修正 (Fixed)
（初回リリースのため該当なし）

### 注意事項 / 既知の制限 (Notes / Known issues)
- apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過小に見積もられる可能性があり、将来的にフォールバック価格（前日終値等）を導入する予定と注記あり。
- position_sizing:
  - 銘柄ごとの単元（lot_size）の固定は現状グローバル値（例: 100）。将来的な拡張のため TODO コメントあり。
- research.factor_research:
  - ファイルは設計方針と一部実装を含むが、完全な関数群の実装（全指標の計算）や単体テストは今後追加予定。
- run_monitoring / run_execution:
  - 監視 DB 初期化や execution の broker 実装に依存するモック/実装差異があるため、Paper / Live の切替は .env 設定と BrokerClientFactory の実装に依存する。
- PyYAML 未インストール環境では validate_config は YAML の中身チェックをスキップして警告を出す動作となる。

### セキュリティ (Security)
（該当なし）

---

今後の公開予定:
- ユニットテスト、インテグレーションテストの整備。
- factor_research の完全実装とベンチマーク、ポートフォリオ最適化周りの追加検証。
- 銘柄別 lot_size サポート、価格フォールバックロジックの強化。