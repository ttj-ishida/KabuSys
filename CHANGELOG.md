# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-19

初回リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール群、監視・検証ツールを提供します。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 `sqlite_path` を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 専用 DB に記録（本番 DB と分離）。
    - 停止フラグ / PID ファイルの処理を実装。
    - スレッドでエンジンを起動し、停止フラグで安全に停止。

- 設定管理
  - 環境設定読み込み・検証モジュール `config.py` を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - `.env` / `.env.local` の自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` のパースロジック（export プレフィックス、クォート文字列、インラインコメントルール等）を実装。
    - `Settings` クラスで設定値をラップし、必須変数は未設定時に例外を投げる。Paper Trading 用のパスや fill_mode のバリデーションなどを含む。
  - 設定ウィザード CLI `config_setup.py` を追加。
    - 対話式で `.env` を作成・更新。デフォルト値、選択肢、シークレット入力対応。
  - 設定検証 CLI `validate_config.py` を追加。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML が存在する場合）を検証。
    - `--strict` オプションで警告を FAIL 扱い（exit code 1）にできる。

- ロギング / プロセスユーティリティ
  - 統一ロギングセットアップ `utils/logging_setup.py` を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティ `utils/process_priority.py` を追加。
    - Windows / POSIX を吸収して `set_process_priority("high"|"normal"|"low")` を提供。
    - `set_cpu_affinity(cpu_count)` によるコア固定機能を提供。
    - 権限不足や未サポート環境では安全にフォールバックして警告を出力。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - `portfolio/portfolio_builder.py`
    - シグナルの候補選定（スコア降順、タイブレーク） select_candidates
    - 等金額配分 calc_equal_weights
    - スコア正規化配分 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）
  - `portfolio/risk_adjustment.py`
    - セクター集中制限 apply_sector_cap（既存保有を考慮して候補を除外）
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）
  - `portfolio/position_sizing.py`
    - 各種配分方式（risk_based / equal / score）に基づく発注株数計算 calc_position_sizes
    - 単元株丸め、per-position および aggregate のキャップ、コストバッファ考慮、スケーリングロジックを実装

- 監視・検証ツール
  - Monitoring DB 初期化ユーティリティを各起動スクリプトから使用（init_monitoring_db）。
  - Paper Trading 検証レポート生成ツール `tools/paper_verification_report.py` を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を解析し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - CLI 引数 `--from`, `--to`, `--db` に対応。
    - Pass/Fail 判定基準（稼働率 99% など）を定義して判定を行う。

- 研究用モジュール（ドラフト）
  - `research/factor_research.py` を追加。
    - モメンタム、バリュー、ボラティリティ、流動性等のファクター計算の設計と基盤を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
    - モメンタム計算のための定数と calc_momentum の骨組みを導入（将来的な拡張を想定）。

### Changed
- なし（初回リリースのため既存の変更点はなし）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 実行環境分離
  - 監視（monitoring）は常に本番用の `SQLITE_PATH` を使用する設計。これにより監視データは環境に依存せず一貫して収集される。
  - 発注エンジン（execution）は `KABUSYS_ENV=paper_trading` の場合 `PAPER_TRADING_SQLITE_PATH` を使用して本番データと完全分離される。
- 環境変数の自動読み込み
  - プロジェクトルートが検出できない場合（配布パッケージ等）は自動ロードをスキップ。
  - OS 環境変数を保護するため、.env の上書きロジックは適切に扱われる（`.env.local` は上書き可能だが OS 環境は保護）。
- ログ出力
  - StreamHandler は stdout を使用（cron 等で stdout/stderr をまとめて扱う運用を想定）。
  - ファイルハンドラ作成に失敗してもコンソールログは維持される。
- エラーハンドリング
  - 起動ループ内での予期しない例外はログ出力して次のポーリングへ継続（監視ループ）。
  - プロセス優先度や CPU affinity は権限やプラットフォームにより失敗する可能性があるが、安全に警告してスキップする設計。
- Paper Trading 検証レポート
  - レイテンシの P95 はメモリ上で計算（小規模 DB を想定）。大規模データでは計算方法の見直しが必要になる可能性がある。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

今後の予定（短期ロードマップの一例）
- research モジュールの完全実装（ファクター正規化、Z スコア、パイプライン化）
- ExecutionEngine / Broker クライアントの詳細実装および MockBroker の充実
- 単体テスト・統合テストの追加（特に position_sizing のキャップ・スケーリングロジック）
- 運用用ドキュメント（デプロイ手順・監視設定・アラート設定）の整備

もし特定のファイルや変更点について詳細なリリースノート（例: 重要な内部アルゴリズムの説明や設計上の注意点）を追加したい場合は、対象を指定してくださると追記します。