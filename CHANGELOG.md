# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

全体のバージョン: 0.1.0 - 2026-04-19

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本ライブラリの初期実装を追加しました（KabuSys v0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の Paper DB を使用し、本番 DB と分離して動作します。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱います。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用します。
- 設定・初期化・検証
  - config.py: 環境変数読み込みと Settings クラスを実装。.env の自動読み込み（.env → .env.local の優先度）、export 形式やクォートを考慮したパーサを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup.py: 対話式ウィザードで .env の初期生成／更新を行う CLI を追加。主要項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、各種パス等）を対話で設定可能。
  - validate_config.py: 起動前に環境変数・config/*.yaml・パス等の整合性をチェックする CLI を追加。--strict オプションで警告もエラー扱いにできます。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバック動作を定義（ファイル出力をスキップ）。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。set_process_priority, set_cpu_affinity を提供し、権限不足時は警告を出してスキップします。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等額配分およびスコア重み配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限に基づき候補除外を行う。unknown セクターは除外対象外。sell_codes を考慮して当日売却予定をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元（lot_size）丸め、銘柄上限・集約上限（available_cash）によるスケーリング、cost_buffer による保守的見積り、0/欠損価格のハンドリング等を実装。
  - portfolio/__init__.py: 上記 API をパッケージエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。以下の指標を集計・表示:
    - システム稼働率（system_status）
    - 注文成功率 / 送信率（trade_logs）
    - リスク却下数（risk_logs）
    - API レイテンシ（平均 / 最大 / P95）
    - PASS/FAIL 判定（デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）
  - CLI オプションで期間指定（--from, --to）および DB パス指定（--db）に対応。P95 計算や欠損データ時のフォールバックを取り扱います。
- research/factor_research.py: DuckDB を用いたファクター計算の基盤を追加（モメンタム等の仕様・定数を定義、関数の実装を開始）。prices_daily / raw_financials テーブルを前提に設計。

### 変更 (Changed)
- ロギング動作の標準化:
  - stdout を StreamHandler に使用することで、cron やシェルから stdout/stderr のリダイレクトを容易にしています。
  - ログファイルはデフォルトで logs/<app_name>.log に日次ローテーション（30 日分保持）。
- .env 読み込み挙動:
  - OS 環境変数を保護するため .env 読み込み時に既存値を上書きしない（.env.local は上書き可能）。自動読み込みはプロジェクトルートが特定できない場合はスキップ。

### 修正 (Fixed)
- run_execution / run_monitoring の終了シグナル処理を確実に行うため、停止フラグファイルの存在チェックと例外ハンドリングを追加しました（例: monitor.check_once() の例外はロギングしてポーリングを継続）。

### 注意事項 (Notes)
- Settings.env は KABUSYS_ENV を小文字正規化して検証します。無効な値は ValueError を送出します。
- Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を利用します。Execution は paper_trading 環境で settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離しています。
- .env の自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority の設定は OS と権限に依存します。権限不足や未対応 OS の場合は警告を出して処理をスキップします。
- research/factor_research.py はファクター計算の設計を含みますが、外部依存（テーブル構造や追加ユーティリティ）との連携が必要です。

### 既知の制限 / TODO
- portfolio.position_sizing.calc_position_sizes:
  - lot_size は現状グローバル共通（デフォルト 100）。将来的に銘柄毎の単元対応を検討中（stocks マスタに lot_size を持たせる）。
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる問題があり、前日終値や取得原価を用いるフォールバックを検討中。
- research/factor_research モジュールは未完（関数の続きや詳細なテストが必要）。
- config/*.yaml の自動検証は PyYAML が存在する場合にのみ実行されます。PyYAML 未インストール時は YAML 検証をスキップします。

### セキュリティ (Security)
- なし

---

今後のリリースでは、ユニットテストの追加、research モジュールの完成、銘柄別 lot_size 対応、より詳細なエラーハンドリングやモニタリング指標の拡張を予定しています。