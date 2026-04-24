# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、コードベースの内容から推測して作成したリリースノートです。

全般的な注記
- 本リポジトリは日本株自動売買システム「KabuSys」の一部モジュールを含みます。
- 環境変数ベースの設定、起動用スクリプト、モニタリング、Execution エンジンの起動補助、ポートフォリオ構築関数群、ユーティリティ（ロギング・プロセス優先度設定）や分析ツール等が含まれます。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-24
最初の公開リリース。本リリースではシステム起動/運用に必要な基本機能群、設定管理、監視・実行用スクリプト、ポートフォリオ構築ロジック、ユーティリティ、および分析用ツールを提供します。

### 追加 (Added)
- 起動/実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
    - Monitoring は環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する仕様を採用。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、Paper Trading 用の専用 SQLite データベース（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する。
    - 停止フラグ、PID ファイル管理、スレッドでの ExecutionEngine 実行と安全な停止処理を実装。

- 設定管理 / ウィザード / 検証
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み機能を実装。
    - .env のパースは export プレフィックス、引用符付き値、インラインコメント等の一般的書式をサポート。
    - OS 環境変数を保護する仕組み（読み込み時の保護キー）を導入。
    - Settings クラスで各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境判定 等）。
    - Paper Trading 設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを実装。各設定項目の説明表示、既存値の再利用、シークレットマスク表示等をサポート。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば）検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - コンソール（stdout）用 StreamHandler と 日次ローテーションする TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定する共通ユーティリティを追加。
    - 環境変数 / 引数に応じたログレベル・ログディレクトリ解決、既存ハンドラのクリア、ログディレクトリ作成失敗時にファイル出力をスキップするフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合に安全にフォールバックする実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順, 同点は signal_rank でタイブレーク）、等配分・スコア加重配分の計算関数を追加。
    - スコア合計が 0 の場合は等配分にフォールバックする挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用して候補をフィルタする apply_sector_cap を追加。sell_codes（当日売却予定）を除外する機能あり。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を追加。
    - risk_based / equal / score の割当方式をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
    - スケーリング時の再配分ロジック（端数を残差順に lot 単位で配分）を実装。

- 分析 / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、レイテンシ（avg, max, P95）等を集計し、PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200ms）を定義。
    - --from/--to/--db オプションをサポート。

- パッケージ初期化
  - __init__.py にバージョン情報 (__version__ = "0.1.0") を追加。

### 変更 (Changed)
- デフォルトの DB/ログ配置や環境変数の優先順位（OS > .env.local > .env）を明示的に実装。
- Logging: コンソールは stdout を使用するように変更（cron/Task Scheduler で stdout/stderr を一本化する運用を想定）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどの対応を追加し、一般的な .env フォーマットに対する互換性を向上。
- 実行ループの安全な終了
  - run_monitoring/run_execution で停止フラグ検知や KeyboardInterrupt を正しくハンドリングして DB 接続やスレッドをクリーンに閉じるように修正。

### その他 / 内部 (Internal)
- DuckDB と SQLite の両方を利用する設計
  - DuckDB を分析用（prices_daily 等の大規模読み取り）に、SQLite を監視・トランザクション小規模データ（monitoring / trade_logs）に使用する方針を反映。
- モジュール分割
  - 機能を pure function（portfolio）とオペレーション（execution/monitoring）に分離し、ユニットテストや再利用をしやすく設計。
- 設定検証が PyYAML の有無に依存する（インストールされていない場合は YAML 検証をスキップして警告のみ出す）。

### 既知の制約 / 注意点
- run_monitoring は Monitoring データベース接続に常に production 用の sqlite_path を使用する（KABUSYS_ENV に依存しない）。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかで、無効な値は ValueError を発生させます。
- プロセス優先度 / CPU affinity の設定は OS と実行権限に依存し、権限不足や未対応環境では警告を出してスキップします。
- config/*.yaml の自動生成はスクリプト（scripts/generate_config.py）を想定しているが、このスクリプトは本リリースに含まれていない可能性があります。
- research/factor_research.py はモジュールとして存在するが一部（冒頭で途切れた実装）が未完の可能性あり。

### セキュリティ (Security)
- 機密情報（API トークン等）は .env 内で管理する想定。`.env` を Git にコミットしないことを README 等で明記することを推奨。

---

今後の改善案（参考）
- research モジュールの完全実装とテスト追加。
- 自動化された CI による設定検証（validate_config の導入を CI に組み込む）。
- 各 CLI のユニットテスト・統合テストの整備。
- ログの構造化（JSON）や外部監視（Prometheus / Grafana 連携）対応検討。