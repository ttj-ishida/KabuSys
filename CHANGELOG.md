# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
フォーマット: 変更分類 (Added / Changed / Fixed / Deprecated / Removed / Security)

## [0.1.0] - 2026-04-21

### Added
- 全体
  - 初期リリース。KabuSys の主要機能（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、検証ツール等）を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用。
    - 停止はプロジェクト内 `data/stop_requested.flag` の存在で検知。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、paper_trading 用 DB (`data/paper_trading.db` デフォルト) と分離して動作。
    - 実行中の PID 管理用ファイル (`data/execution.pid`) と停止フラグによる安全停止に対応。
    - 実行はデーモンスレッドで行い、停止フラグで Engine.stop() を呼び出して終了。

- 設定管理・検証
  - config.py:
    - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - `.env` / `.env.local` の読み込み順序と上書き保護（OS 環境変数の保護）に対応。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env 行パーサは `export KEY=...`、クォート、エスケープ、行内コメント等に対応。
    - 設定アクセス用 `Settings` クラスを提供（各種環境変数の取得ラッパー、妥当性チェック付き）。
    - `paper_fill_mode` の妥当値検証、`env` / `log_level` の検証、各種パスや監視閾値をプロパティで提供。
  - config_setup.py:
    - 対話式 .env 作成・更新ウィザードを追加。既存値の再利用、シークレットのマスク、選択肢サポートなど。
    - `.env` の書き出しテンプレートを提供（書き込み時に注意コメントを挿入）。
  - validate_config.py:
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML がない場合は警告）等を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - シグナル選定（score 降順、同点時は signal_rank によるタイブレーク）を実装。
    - 等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap を実装（既存保有比率が閾値を超えるセクターの新規候補を除外）。"unknown" セクターは制限対象外として扱う。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップ、未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method に応じた株数決定ロジックを実装（"risk_based", "equal", "score" をサポート）。
    - risk_based: 許容リスク率・ストップロス率に基づく株数算出。
    - 等配/スコア配: 各銘柄の重み・max_utilization・max_position_pct を考慮した算出。
    - 単元株（lot_size）丸め、price がない銘柄のスキップ、aggregate cap（available_cash） によるスケールダウン、cost_buffer（手数料/スリッページ見積）を考慮した調整、残差処理によるロット単位の追加配分を実装。
  - portfolio パッケージ `__all__` エクスポートを整備。

- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーを統一的に設定するユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、環境変数 LOG_DIR で変更可）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 引数 / 環境変数によるログレベル解決ロジックを実装。
  - utils/process_priority.py:
    - プロセス優先度設定（set_process_priority）を実装。Windows / POSIX の差分を吸収して "high"/"normal"/"low" をサポートし、権限不足などは警告でスキップ。
    - CPU affinity 設定（set_cpu_affinity）も提供し、コア数制約や権限エラーをハンドリング。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を抽出し、Pass/Fail 判定を実行。
    - CLI 引数 `--from` / `--to` / `--db` と環境変数 `PAPER_TRADING_SQLITE_PATH` をサポート。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）をデフォルトとして設定。

- リサーチ
  - research/factor_research.py:
    - ファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（モジュール化されたファクター計算の骨格）。

### Changed
- ログ出力
  - logging_setup のデフォルトで stdout を使用するように明示。これにより cron/Task Scheduler 等で stdout/stderr のリダイレクト運用を容易化。
- DB 接続の扱い
  - run_monitoring は環境にかかわらず監視用に設定された sqlite_path（本番想定）を使用する仕様を明記（意図的な設計）。
  - run_execution は `paper_trading` 環境時に専用の paper_sqlite_path を使用して本番 DB と分離するよう動作。

### Fixed
- 設定パーサの堅牢化
  - .env のパースロジックでクォート内のバックスラッシュエスケープや、行内コメントの扱い、`export ` プレフィックスの取り扱いなどに対応し、より実用的な .env 解析を実現。
- ポートフォリオ計算の安定化
  - calc_score_weights において全スコアが 0 の場合にゼロ除算/不正な重みを避けるため等金額配分へフォールバックする挙動を実装。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注記:
- 一部モジュール（例: research/factor_research.py）はファクター計算ロジックの主要構造を実装していますが、実運用にあたってはテストデータやマスターデータ（銘柄の lot_size 等）との結合確認、境界ケースの追加テストを推奨します。
- 実行スクリプトは停止フラグ / PID ファイル / kill フラグなどに依存するため、デプロイ時に `data/` ディレクトリのパーミッション・存在を確認してください。