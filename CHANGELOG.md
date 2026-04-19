# CHANGELOG

すべての重要な変更を追跡します。フォーマットは「Keep a Changelog」に準拠しています。  
セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーションパッケージを初期リリース。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動 / 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定して実行。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止制御: `data/stop_requested.flag` を検知して安全に停止する仕組みを実装。PID ファイル出力（`data/execution.pid`）に対応。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関係なく本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイルでループ終了を行う実装。

- 設定管理 / 初期化ツール
  - config.py
    - 環境変数 / .env 読み込みロジックを実装。プロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込み（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` の行パーサが quotes、エスケープ、`export KEY=...` 形式、インラインコメントなどに対応。
    - Settings クラスを実装し、各種設定値（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定 等）をプロパティで提供。入力値の検証（有効な env 値、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。
  - config_setup.py
    - 対話式ウィザードで `.env` を作成・更新する CLI を追加。デフォルト値、シークレット入力、保存の確認、.env のテンプレート書き込みを提供。
    - .env を誤って Git にコミットしないよう注意書き付きで出力。

  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と PyYAML を用いたパース検証（PyYAML 未インストール時は警告）などをチェック。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、タイブレークは signal_rank）と重み計算（等額配分 / スコア加重）を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクターごとの集中上限適用（既存保有を考慮して新規候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0、ログ警告を出力。
  - portfolio/position_sizing.py
    - 発注株数算出ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を用いた保守的なコスト見積り、残余配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止、ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - utils/process_priority.py
    - プロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 設定ユーティリティを追加。アクセス拒否等の例外を安全にハンドリングして警告を出力。

- 監視・検証ツール
  - monitoring モジュール用の DB 初期化フック（init_monitoring_db を複数箇所から呼び出して冪等性を担保）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し、閾値（稼働率 99%、成立率 90% など）に基づいて PASS/FAIL を判定。
    - P95 計算、SQL 日付フィルタの組み立て、DB 存在チェックとエラーハンドリングを実装。

- リサーチ（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受け、prices_daily / raw_financials を参照して計算する設計。モメンタム計算（calc_momentum）の実装が開始されている（未完の状態の可能性あり）。

### 変更 (Changed)
- ログ出力の仕様を統一
  - StreamHandler を stdout に設定（stderr ではなく stdout を使うことで cron 等のリダイレクトを想定）。
  - ログレベル解決順やログディレクトリの決定ロジックを明確化。

- 環境変数ロードの優先度
  - OS 環境変数 > .env.local > .env の順で読み込む。既存 OS 環境変数は保護される。

### 修正 (Fixed)
- .env パーサの頑健性向上
  - クォート内のバックスラッシュエスケープに対応、export 構文の許容、インラインコメント処理の改善等を実施し、より多様な .env 記述に対応。

- DB 初期化の冪等性
  - init_monitoring_db() を Execution と Monitoring の両方で呼び出し、監視テーブルが確実に存在するように保証（複数回呼んでも安全）。

### 注意点 / 既知の制約 (Known issues / Notes)
- research/factor_research.py の calc_momentum 実装が途中で終わっている（ソースの途中で切れている）。本番運用前に完了・テストが必要。
- position_sizing のコメントで指摘されているように、価格欠損（price=0.0）の取り扱いに改善余地あり（現状はスキップしているため保守的すぎる可能性）。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計のため、テスト時は sqlite_path を適切に差し替えること。
- process_priority / set_cpu_affinity は権限や OS 実装に依存するため、設定に失敗した場合は警告を出して安全にスキップする。

### セキュリティ (Security)
- .env は生成時に Git にコミットしないよう注意書きを追加（config_setup のテンプレートに明記）。

---

今後の予定（例）
- factor_research の完実装（全ファクター計算の完成と DuckDB クエリ最適化）
- strategy / execution の単体テスト整備、paper_trading 用のより詳細なシミュレーションと検証スイート
- price フォールバックロジックや銘柄毎の lot_size をサポートする拡張設計

もし CHANGELOG に特に強調したい変更点や補足したい箇所があれば教えてください。