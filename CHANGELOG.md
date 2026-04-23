# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベース内のバージョン情報およびコード内容から推測しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回公開リリース。システム全体の起動スクリプト、設定管理、ログ/プロセスユーティリティ、ポートフォリオ構築、実行エンジン周りの骨格、およびペーパートレード検証ツールを含む基盤機能を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトルートの `data/stop_requested.flag` を参照。
    - 監視は環境にかかわらず本番用 SQLite パスを使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを実行し、停止フラグで安全に終了可能。
    - `KABUSYS_ENV=paper_trading` 時は専用の paper trading 用 SQLite（`data/paper_trading.db` 既定）を使用して本番 DB と分離。
    - 実行の PID 管理用ファイルパスと停止フラグ参照を実装。

- 設定管理・検証
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と上書き制御、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化機能。
    - .env 行パーサーが `export` 形式やクォート／エスケープ、コメントを適切に扱う実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、API トークン、PaperTrading モード等含む）。
    - 環境値のバリデーション（`KABUSYS_ENV`, `PAPER_FILL_MODE`, `LOG_LEVEL` 等）。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML が存在する場合）、本番環境向けの追加警告等を実装。
    - `--strict` オプションにより警告を FAIL として扱うモードを提供。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env ファイルの初期作成/更新を支援する CLI を追加。
    - シークレット項目はマスク表示、既存 .env を読み込んで再利用可能、最終的に .env を書き出す機能を提供。

- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを実装。
    - ログレベル・ログディレクトリの解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する機能を実装。
    - CPU affinity（最初の N コアにピン留め）を設定する関数も提供。
    - 権限不足や未対応環境時は警告を出して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（スコア合計が 0 の際は等配分へフォールバック）を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有と候補を照らし合わせてセクター上限を超える候補を除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に基づく乗数を返す。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method に応じて risk_based / equal / score をサポート。
    - 単元株（lot_size）で丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。コストバッファを考慮した計算。
  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージとしてエクスポート。

- 実行・発注周りの骨格（参照のみ、実際の broker 実装は別）
  - run_execution で BrokerClientFactory/ExecutionEngine/OrderManager/Reconciler/RiskManager 等の組み立てと起動フローを実装（詳細は実装モジュール依存）。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_monitoring/run_execution 起動フロー内で呼び、監視テーブルが存在することを保証（冪等）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（既定: data/paper_trading.db）から集計し、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を計算してレポートを標準出力に出力。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）をサポート。

- 研究用ファクター計算基盤
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算方針と計算定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計の骨格を追加。
    - （calc_momentum 等の実装途中あり、各種定数と関数枠組みを配置）

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues / TODO
- research/factor_research.py の calc_momentum 関数がファイル末尾で未完（実装途中の兆候あり）。完全なファクター計算実装は今後の作業。
- apply_sector_cap 内の価格欠損（price == 0.0）の場合にエクスポージャーが過小見積りされ得る旨の TODO コメントあり。将来的に前日終値などのフォールバック価格を導入する予定。
- position_sizing では現時点で単元株（lot_size）が全銘柄共通で固定。将来的に銘柄別 lot_size を受け取る設計拡張を予定（TODO コメントあり）。
- Logging のファイルハンドラ作成やログディレクトリ作成に失敗した場合、処理はコンソール出力にフォールバックするよう設計しているが、運用時にはログディレクトリの権限とディスク空き容量を確認すること。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で実行をスキップする。特に低権限コンテナ環境では効果が限定される可能性あり。

---

その他、実運用時の注意点や拡張（ブローカークライアント実装、ExecutionEngine 内の詳細な注文ロジック、完全なファクター計算）については今後のリリースで順次追加していく予定です。