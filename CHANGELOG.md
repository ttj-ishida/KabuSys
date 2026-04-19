# Changelog

すべての重要な変更点はこのファイルにまとめます。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージを追加（version 0.1.0）。
  - src/kabusys/__init__.py にバージョン情報を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag ファイル検知で行う。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する挙動を明記。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）の検知でエンジン停止。実行中は execution.pid（data/execution.pid）を使用。
    - デフォルトでプロセス優先度を "high" に設定。

- 設定管理 / ユーティリティ
  - config.py
    - .env 自動読み込み機能を導入（プロジェクトルート自動検出）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
    - .env/.env.local の読み込み順序と OS 環境変数の保護ロジックを実装。
    - 複数の設定プロパティ（DB パス、LINE、kabu、J-Quants、監視しきい値等）を提供。
    - `PAPER_FILL_MODE` の検証、`KABUSYS_ENV` / `LOG_LEVEL` の検証を実装。
  - config_setup.py
    - 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 秘匿項目のマスク表示、選択肢やデフォルト値の提示、保存確認を実装。
  - validate_config.py
    - CLI による設定検証ツールを追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック）。
    - `--strict` オプションで警告を失敗（exit 1）として扱う。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するヘルパーを追加。
    - 既存ハンドラの一掃、LOG_DIR 環境変数対応、ログディレクトリ作成失敗時のフォールバックなどを実装。
    - stdout を利用することで cron 等でのリダイレクトを想定。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティを追加（psutil を使用）。
    - `set_process_priority(level)` により "high"/"normal"/"low" を指定可能。
    - `set_cpu_affinity(cpu_count)` によりプロセスを最初の N コアにピン留めする機能を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築 / リスク調整 / ポジションサイズ決定
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、同点は signal_rank でタイブレーク）関数 `select_candidates` を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を実装。全スコアが 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を実装（既存保有のセクター時価を計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear を標準対応、未知レジームは 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - 単元・リスク基準・各種上限を考慮した株数決定 `calc_position_sizes` を実装。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - lot_size（単元）適用、各銘柄上限（max_position_pct）、総投下キャッシュ上限（available_cash）に基づくスケールダウン（remainder を考慮した再配分）を実装。
    - cost_buffer による保守的コスト見積り対応。
    - 価格欠損時のスキップ、デバッグログを出力。

- モニタリング・検証ツール
  - monitoring/（監視 DB 初期化などは各スクリプトから呼び出し）
    - monitoring の DB 初期化ユーティリティが利用される構成に統一。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し、閾値に基づく PASS/FAIL 判定を出力。
    - CLI オプション `--from`/`--to`/`--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パス指定可。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を採用。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py
    - DuckDB 接続を受け取り、モメンタム・ボラティリティ等のファクター計算を行うモジュールを追加。設計方針、利用するテーブル（prices_daily / raw_financials）と計算対象を明記。
    - モメンタム計算（calc_momentum）の実装を開始（ファイル末尾で未完の部分が存在）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details & safe defaults
- .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行うため、CWD 非依存で動作。
- .env のパースは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの扱いなどに対応し、現実的な .env ファイル形式に耐性を持たせている。
- ログ出力はコンソール（stdout）とファイルの両方を標準で行い、ログディレクトリ作成に失敗した場合はファイル出力を自動的に無効化して続行する（デフォルトの堅牢性を重視）。
- run_execution は paper_trading と本番 DB を明確に分離。paper_trading 用 DB は環境変数で上書き可能。
- プロセス優先度・CPU アフィニティ設定は権限不足や未対応プラットフォームでも例外を暴露せず警告でフォールバックする。

### Known Limitations / TODO
- research/factor_research.py の一部（calc_momentum の続き等）が未完。今後、全ファクター（Value, Volatility, Liquidity）の実装と Z スコア正規化連携を予定。
- position_sizing の価格欠損時の扱いについて注記（現在は 0.0 を使用すると見積りが過少になる可能性あり）。将来的に前日終値等のフォールバックを追加予定。
- 一部の外部モジュール（psutil, duckdb, PyYAML 等）に依存。環境により警告や機能制限が発生するため、導入手順の README に依存関係を追記すると良い。

---

今後のリリースでは、ファクター計算の完成、戦略実行部分（ExecutionEngine / Broker 接続周り）の追加・安定化、テストカバレッジの拡充、ドキュメント（運用手順・デプロイ手順）の整備を予定しています。