CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-24

初回リリース。

### Added
- 基本アプリケーションパッケージ kabusys を追加
  - バージョン情報: `__version__ = "0.1.0"`

- 起動スクリプト / サービス
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用して実際の／モックブローカーを切り替え。
    - PID ファイル (data/execution.pid) と停止フラグ (data/stop_requested.flag) を監視し、外部からの停止制御に対応。
    - プロセス優先度を "high" に設定する処理を起動時に実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用。
    - 停止フラグ (data/stop_requested.flag) 検知でループを終了。
    - プロセス優先度を "high" に設定する処理を起動時に実行。

- 設定・起動補助ツール
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出に .git または pyproject.toml を使用）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の読み込み順: OS 環境 > .env.local > .env（.env.local は上書き許可）。
    - .env パーサは export 形式、クォート、有効なインラインコメント処理などに対応。
    - Settings クラスを提供し、アプリケーションで必要な設定値（J-Quants トークン、kabu API パスワード、DB パス、各種しきい値、環境種別など）をプロパティとして安全に取得・バリデート。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの検証ロジックを実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成／更新する CLI を提供。
    - 機密項目は表示をマスクし、確認後に .env を書き込み（ファイルは Git 管理しない旨の注意を含むテンプレートで出力）。
  - validate_config.py
    - .env と config/*.yaml の設定を起動前に検証する CLI。
    - 必須環境変数未設定はエラー、プレースホルダ値・本番環境設定は警告を出す。
    - PyYAML が存在する場合は YAML ファイルのパース検証も実行。`--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用することで crontab 等からの出力リダイレクトに適合。
  - utils/process_priority.py
    - psutil を用いて Windows/Linux/Mac の差分を吸収するプロセス優先度設定ユーティリティを提供。
    - nice 値 / Windows 優先度クラスのラップ、CPU affinity 設定関数も実装。許可不足や未対応 OS では警告を出してスキップする堅牢な実装。

- ポートフォリオ構築関連（純粋関数群：副作用なし、メモリ内計算）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順・タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア比率配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中管理 apply_sector_cap（既存保有時価を計算し、指定上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知値は警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮した安全な丸めロジック。
    - 価格欠損時のスキップやログ出力により堅牢化。

- 解析 / レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - 既定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
    - 日付範囲指定と DB パス指定（コマンドラインオプション）に対応。

- リサーチ（ファクター計算）モジュール（着手）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity 等のファクター計算方針を実装するための基盤を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モジュールは実装途中（ファイル末尾で途中）。

### Changed
- n/a（初回リリースのため変更履歴なし）

### Fixed
- n/a（初回リリースのため修正履歴なし）

### Notes / Implementation details
- 設定読み込みは OS 環境変数を優先し、.env/.env.local を上書きするが OS 環境変数保護のため自動ロード時は既存の OS 環境変数を上書きしない設計。
- ログ出力は既存ハンドラをクリアしてから再設定するため、重複したハンドラが発生しない。
- process_priority・CPU affinity は権限不足や未サポート環境でも安全にフォールバックし、起動を妨げない。
- ExecutionEngine / SystemMonitor 起動時に監視テーブル（init_monitoring_db）を冪等に確保する処理が入るため、DB の初期化漏れによるクラッシュを抑制。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター計算ロジックの完成）
- ExecutionEngine / SystemMonitor の細かなテスト & ドキュメント充実
- 戦略・リスク設定の外部 YAML 連携強化と検証ロジック拡張

以上。