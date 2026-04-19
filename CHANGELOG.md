# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased

## [Unreleased]

### 追加
- なし

---

## [0.1.0] - 2026-04-19

初回リリース。本リポジトリに含まれる主要機能と実装の概要を記載します。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite (data/paper_trading.db) を使用して本番 DB と完全に分離。BrokerClientFactory によるブローカークライアント生成をサポート。
    - エンジンはデーモンスレッドで実行され、data/stop_requested.flag により安全に停止可能。実行中の PID を data/execution.pid に出力。
    - risk_manager に対する既定のパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを記録。
    - 起動時にプロセス優先度を "high" に設定。停止は data/stop_requested.flag により実施。

- 設定管理
  - config.py
    - .env ファイルの自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。テスト用に自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーを強化: `export KEY=val` 形式、シングル/ダブルクォート中のバックスラッシュエスケープ、行内コメントの扱いなどに対応。
    - Settings クラスを導入し、J-Quants / kabuステーション / DB パス /監視パラメータ / システム状態（KABUSYS_ENV 等）のプロパティアクセスを提供。値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証など）を実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE をサポート。

  - config_setup.py
    - ユーザ対話式の .env 初期作成・更新ウィザードを追加。既存値の再利用、シークレットマスク表示、保存時のテンプレート出力を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスのディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告等を行う。
    - --strict オプションで警告も FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging を追加。root ロガーに stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。LOG_DIR 環境変数や引数によるログ出力ディレクトリの解決、既存ハンドラのクリーンアップ、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - set_process_priority で Windows / POSIX を吸収した優先度設定を実装。set_cpu_affinity による CPU 固定（最初の N コア）を実装。権限不足等は警告でスキップ。

- ポートフォリオ構築（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（既存保有を考慮して上限を超えるセクターの候補除外）を実装。unknown セクターは上限チェック対象外とする挙動。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - allocation_method に応じた発注株数算出（risk_based / equal / score）を実装。risk_based の場合は risk_pct・stop_loss_pct を用いた株数算出。lot_size（単元株）への丸め、max_position_pct による per-stock 上限、available_cash に対する aggregate cap（スケールダウン）を実装。cost_buffer により手数料/スリッページを保守的に見積もる。残差処理で lot_size 単位の追加配分処理を実装。
    - 取引価格欠損時はスキップし、ログ出力で理由を通知。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して標準出力レポートを生成。閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を行う。日付レンジ指定や DB パス指定をサポート。

- 研究用モジュール（DuckDB ベース）
  - research/factor_research.py（実装開始）
    - Momentum / Value / Volatility / Liquidity 等のファクター算出設計を導入。DuckDB 接続を受け、prices_daily / raw_financials テーブルを使って計算する設計。モメンタム（1M/3M/6M、MA200 乖離）などの実装方針を明記。

### 変更
- 監視 DB 初期化
  - init_monitoring_db が idempotent に呼べるように使用場所を統一（monitoring 用テーブルの存在を保証）。
- 実行エンジンの安全仕様
  - run_execution は起動前に停止フラグをチェックし、既に停止フラグが立っている場合は起動せず終了するように変更（安全措置）。

### 修正
- .env 読み込みの堅牢化
  - 読み込み失敗時に warnings.warn を出力して処理を継続するようにし、ファイル読み込み失敗でクラッシュしないように修正。
- ログ出力
  - logging_setup で既存ハンドラを安全に flush/close してから削除するように修正し、二重ハンドラ登録を防止。

### 注意点 / 既知の問題
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨をコメントで記載。将来的に前日終値や取得原価によるフォールバックを検討中。
- portfolio/position_sizing:
  - 現状 lot_size は全銘柄共通の引数であり、銘柄別単元対応は TODO。
- research/factor_research.py:
  - ファイル末尾が未完（calc_momentum の実装途中）であり、研究用モジュールはまだ完成途上。DuckDB テーブル依存のため、本番で使うにはテーブル整備が必要。
- セキュリティ:
  - .env は決してリポジトリにコミットしないこと（config_setup のヘッダーに注意書きを記載）。

### セキュリティ
- .env にシークレット（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD）を扱うため、config_setup で生成される .env を Git 管理下に置かないように明示。

---

今後の予定（例）
- factor_research の完了とユニットテスト追加
- position_sizing の銘柄別 lot_size 対応
- 監視・実行の統合テストとコンテナ化用設定の整備

--- 

（この CHANGELOG は、提供されたソースコードの内容から推測して作成されています。実際のコミット履歴やリリースノートが存在する場合はそれに従って更新してください。）