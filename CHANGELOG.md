# CHANGELOG

すべての重要な変更履歴をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

全般:
- このリポジトリではバージョン番号をパッケージトップの `kabusys.__version__` で管理しています（現行: 0.1.0）。
- 多くの機能が CLI スクリプト／ユーティリティ群として追加され、ローカル実行・検証・ペーパートレード用レポート生成までをカバーしています。

## [0.1.0] - 2026-04-20

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (`data/stop_requested.flag`) により安全に停止可能。PID ファイル (`data/execution.pid`) をサポート。
    - BrokerClientFactory、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てを行う。
    - RiskManager のデフォルト設定例（max_position_pct, max_utilization 等）を組み込み。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境 (`KABUSYS_ENV`) にかかわらず本番用 `sqlite_path` を使用する挙動を採用（監視データは本番 DB に集約）。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグでループ終了。
- 設定管理
  - config.py
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）と .env 読み込み機能を追加（`.env` → `.env.local` の順で適切に適用、OS 環境変数を保護）。
    - Settings クラスを導入し、各種環境変数（J-Quants / kabu API / DB パス / 監視しきい値 / 実行環境等）をプロパティとして提供。環境値の検証（有効値チェック、必須チェック）を実装。
    - Paper Trading 用挙動（PAPER_FILL_MODE の検証、`paper_sqlite_path`）を追加。
    - 自動 .env ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - config_setup.py
    - 対話式ウィザードにより `.env` ファイルの初期作成・更新を支援。
    - シークレット入力マスク、選択肢、デフォルト値、保存確認等のユーザフレンドリーな操作。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本的な存在／整合性検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルや DB パスの検証、YAML のパース検査（PyYAML がある場合）などを実行。
    - `--strict` オプションにより警告を FAIL 扱いにするオプションを追加。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30世代保持）を設定するユーティリティを追加。
    - ログ出力先 (`LOG_DIR`)、ログレベル解決順序（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収するプロセス優先度設定ユーティリティを追加（psutil 依存）。
    - CPU affinity 設定（set_cpu_affinity）をサポート。
- Portfolio 構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重み・スコア加重（calc_equal_weights / calc_score_weights）を実装。スコア全0 の場合は等重みへフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック処理あり。
    - セクター上限判定時に既存保有評価額を計算して候補を除外。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score の各方式）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケールダウンを考慮。コストバッファを反映。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB からシステム稼働率、注文成功率、送信率、レイテンシ（P95 を含む）等の集計を行い、閾値比較による PASS/FAIL レポートを生成。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプションで期間 (`--from`, `--to`) と DB パス (`--db`) を指定可能。
- DuckDB 統合
  - run_* および一部モジュールで DuckDB 接続を利用する設計（`DUCKDB_PATH` デフォルト `data/kabusys.duckdb`）。

### Changed
- デフォルト挙動の明確化
  - 監視（run_monitoring）は環境にかかわらず監視用の sqlite_path（デフォルト: `data/monitoring.db`）を使用するよう文書化（監視データは本番的観点で集約する方針）。
  - 実行（run_execution）は paper_trading 環境では paper 用 DB を使用し、本番 DB とデータを分離する。
- ログ出力
  - ハンドラ重複を避けるため、setup_logging() は既存ハンドラをクリアして再設定するように変更。

### Fixed
- （現段階で明確なバグ修正は無し。新規実装リリース）

### Known issues / Notes / TODO
- research/factor_research.py はファイル先頭に設計と定数があり、モメンタム計算関数のスケルトンが含まれますが、一部実装が未完（ソース末尾が途中で切れている可能性があります）。本格運用前に実装完了が必要です。
- position_sizing.calc_position_sizes:
  - price が 0.0 などで欠損している場合、現状はスキップしてしまいエクスポージャーが過小見積もられる可能性あり。将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO コメントあり。
  - 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map に対応する予定。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターに対してはセクター上限を適用しない（除外しない）設計。セクター未登録銘柄の取り扱いは運用ポリシーに依存。
- process_priority / set_cpu_affinity:
  - psutil の権限や実行環境により設定に失敗する場合は警告を出してスキップする実装。コンテナ環境や制限された環境では効果が得られない可能性あり。

### Migration / Upgrade notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。未設定時は起動前に `.env` を作成してください（`python -m kabusys.config_setup` を推奨）。
  - 本番環境で KABUSYS_ENV を `live` に設定する際は LINE 通知系（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL フラグ設定に注意してください（validate_config.py による検証推奨）。
- 環境変数で制御可能な主な項目:
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START, KABUSYS_ENV 等。
- 自動 .env 読み込みを無効化する場合:
  - 起動環境やテストで自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログ:
  - デフォルトでログは `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合は標準出力のみで継続されます。

---

将来的なリリースでは factor_research の完成、各種単体テストおよび E2E テストの追加、BrokerClient のモック拡張や注文周りの堅牢化（再試行・バックオフ）などを予定しています。問題・要望があれば issue を作成してください。