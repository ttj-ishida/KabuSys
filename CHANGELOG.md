# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。

### 追加 (Added)
- 設定管理
  - Settings クラスを導入し、環境変数をプロパティ経由で取得する仕組みを提供。J-Quants / kabuステーション / LINE / DB /監視閾値などの設定をラップ。
  - 自動 .env ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いなど）。

- 環境設定ウィザード
  - `kabusys.config_setup` に対話形式のウィザードを追加。`.env` の初期作成・更新を支援。出力テンプレートは .env に書き込まれ、秘密項目はマスク表示される。
  - デフォルト値や選択肢を持つ設定項目を定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリチェック、config/*.yaml の存在および（PyYAML が利用可能なら）パース検証、本番用の追加ガード等を実行。
  - `--strict` オプションをサポート（警告を失敗扱いにする）。

- 実行スクリプト
  - `run_execution.py` を追加。起動順序としてログ設定・プロセス優先度設定・DB 接続・依存コンポーネント組み立て（BrokerClientFactory / OrderRepository / OrderManager / RiskManager / Reconciler）を行い、ExecutionEngine を別スレッドで実行。停止フラグファイル検出で安全に停止する。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）の場合は Mock ブローカーを使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。

- 監視スクリプト
  - `run_monitoring.py` を追加。SystemMonitor を用いたポーリングループを提供。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番の sqlite_path を利用する設計。
  - 停止フラグファイル（data/stop_requested.flag）検出でループを終了。

- ロギング
  - `kabusys.utils.logging_setup` を追加。全起動スクリプトから共通で使用可能なロギング初期化を提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベルの解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。

- プロセス優先度 / CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX（Linux/Mac）差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定するユーティリティも提供。権限不足等は警告ログでスキップ。

- ポートフォリオ構築関連
  - `kabusys.portfolio` モジュールを追加。
    - portfolio_builder: BUY シグナルから候補選定（スコア降順）と等配分/スコア加重配分の計算（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を提供。未知レジームはフォールバック挙動と警告。
    - position_sizing: 発注株数算出ロジック（risk_based / equal / score）を実装。単元株丸め、1銘柄上限・aggregate cap（利用可能現金超過時スケールダウン）、cost_buffer（手数料/スリッページ見積り）に対応。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite から集計して検証レポートを出力（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）。
  - デフォルト基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- 研究用ファクター計算（部分実装）
  - `kabusys.research.factor_research` を追加（モメンタム等ファクター計算の骨格を実装）。DuckDB を利用して prices_daily / raw_financials を参照する設計。関数群の設計方針と定数が定義済み（モメンタム窓長、ATR、出来高日数等）。（一部実装は継続中）

- パッケージメタ
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

### 改良 / 堅牢化 (Changed / Improved)
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメントの扱いを正しく処理。`export KEY=val` 形式に対応。
- ロギング設定の安全性
  - ログディレクトリ作成に失敗した場合でもコンソールログにフォールバックする実装。既存ハンドラの flush/close と再設定で二重ハンドラを防止。
- DB 初期化の冪等性保証
  - 監視用 DB の初期化関数（init_monitoring_db）を起動時に呼ぶことでテーブル存在を保証（冪等）。

### その他（ドキュメント / 使用上の注意）
- 環境変数に関する注意点
  - `PAPER_FILL_MODE` の有効値は "instant" / "partial" / "never" / "reject"。不正値は ValueError。
  - `KILL_FLAG_CLEAR_ON_START` は本番で `1` にすると危険（自動クリア）。validate_config で警告する。
  - 監視ポーリング間隔は `MONITOR_POLL_INTERVAL` で指定可能（1 秒以上の正の整数、無効値はデフォルト 60 秒にフォールバック）。
- ファイル・パスのデフォルト
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / stop flag: data/execution.pid, data/stop_requested.flag 等
- CLI 例
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### 既知の制約 / TODO
- factor_research の各ファクター計算の実装完了（現在はモメンタム関連の実装途中）。
- position_sizing の lot_size は現状全銘柄共通。将来的には銘柄別単位対応を検討（stocks マスタへの lot_size 拡張）。
- apply_sector_cap の価格欠損時の取り扱いに注意（price の欠損があるとエクスポージャが過少評価される可能性あり）。フォールバック価格の導入を検討。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして公開する際は、コミットログやリリース計画に合わせて調整してください。