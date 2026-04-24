# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

注意: 以下は提示されたコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys 自動売買システムのコア機能を追加。
  - パッケージメタデータ: src/kabusys/__init__.py にバージョン `0.1.0` を追加。

- 実行スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出による安全な停止処理、例外発生時のログ捕捉。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBroker を利用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）/PID ファイル（data/execution.pid）を用いた制御。
    - スレッドでエンジンを実行し、停止フラグで安全に停止。

- 設定管理・ウィザード・検証
  - config.py: Settings クラスを導入。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パースでクォート、エスケープ、`export KEY=val` 形式、インラインコメント等に対応。
    - 必須環境変数取得ヘルパや env 値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用のパス分離（paper_sqlite_path）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 推奨デフォルト設定、シークレット入力のマスク、保存前の確認など。
    - .env 書き込みテンプレートを提供（.env を誤ってコミットしない旨の警告を含む）。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在・パース検証。
    - PyYAML 未インストール時のスキップや、本番環境時の追加警告（LINE 設定、KILL_FLAG_CLEAR_ON_START）等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログディレクトリ自動作成、作成失敗時はファイルハンドラを無効化してコンソールのみ継続。
    - ログレベル/ログディレクトリ解決ロジック（引数・環境変数・デフォルト）。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度設定（Windows の priority class / POSIX nice）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告を出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルに基づく候補選定 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合の候補除外。unknown セクターは除外対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method に基づく発注株数計算 calc_position_sizes（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ (cost_buffer) を考慮したスケーリングロジック、残差を用いた追加配分の実装。
    - 価格データ欠損時のスキップやログ出力。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - DuckDB 接続を受けてモメンタム等のファクターを計算するモジュール骨格を追加。
    - モメンタム指標（mom_1m/mom_3m/mom_6m、MA200乖離）等の計算方針を実装（ファイルは途中まで含まれる）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite からシステム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 閾値に基づく PASS/FAIL 判定（稼働率 >= 99% など）。
    - コマンドラインで日付範囲指定 (--from / --to) と DB 指定 (--db) に対応。

- 監視用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が呼ばれて、監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため対象なし）

### Fixed
- （初回リリースのため対象なし）

### Security
- （初回リリースのため特記事項なし）

---

注意事項・設計上のポイント（コードからの注記）
- .env 自動ロードは OS 環境変数を破壊しないよう保護（protected set）しており、テスト時に無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- run_monitoring は環境に依存せず本番用監視 DB を参照する設計（意図的な分離）。
- run_execution は paper_trading 時に本番 DB と完全分離された paper DB を使用するため、ペーパートレードの検証が容易。
- ロギングは stdout を使う設計（cron/Task Scheduler から起動したときにリダイレクトしやすい）。
- process_priority・CPU affinity は権限不足や未対応 OS でも安全にフォールバックする実装。
- 一部モジュール（研究系の factor_research.py 等）は実装途中の箇所が見受けられる（今後の拡張想定）。

もし特定ファイルや機能ごとに詳細な変更点やコミット単位の履歴が必要であれば、さらにコード差分や Git コミットログを提供してください。これに基づいてより細かい CHANGELOG（機能追加日時、影響範囲、移行手順など）を作成できます。