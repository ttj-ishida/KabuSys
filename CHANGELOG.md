# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

注: 以下はリポジトリ内のソースコードから機能・設計を推測して作成した変更履歴です。実際のコミット履歴に基づくものではありません。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初版リリース。

### 追加 (Added)
- アプリケーション基本機能
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - Settings クラスによる環境変数/設定管理を実装。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env のパースは quotes, export 形式、インラインコメント等に対応。
    - 各種設定プロパティ（DB パス、API トークン、ログレベル、環境種別、Paper Trading 関連設定など）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて broker クライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てて実行。
    - エンジンは別スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - 実行時にプロセス優先度を設定（High をデフォルトで要求）。
    - PID ファイル出力サポート（data/execution.pid）。
    - 監視テーブルの初期化（init_monitoring_db）を起動時に冪等に実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず監視は本番 sqlite_path を使用（監視 DB を本番と同じ場所に維持）。
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - stop フラグ（data/stop_requested.flag）を監視してループ終了。
    - 起動時にプロセス優先度を High に設定。
- 設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - J-Quants / kabuAPI / DB パス / LINE 設定等の項目を網羅。
    - シークレット項目はマスク表示、保存前に確認プロンプトあり。
    - 保存先ファイルはデフォルトでプロジェクトルートの .env。
  - validate_config.py
    - 環境変数および config/*.yaml の存在や妥当性をチェックする CLI を追加。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
    - 本番環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
- ポートフォリオ構成（Portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank の昇順でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull" / "neutral" / "bear" に応じた投下資金倍率を提供。未知のレジームは警告を出して 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（合計投下金額のスケールダウン）を実装。
    - aggregate スケールダウン時の小数端数処理ロジック（lot 単位で残差の大きい順に割付）を実装。
    - risk_based では risk_pct / stop_loss_pct を用いたポジションサイズ算出。
- ユーティリティ
  - utils/logging_setup.py
    - 統一されたロギング設定を提供（StreamHandler → stdout、TimedRotatingFileHandler 日次ローテーション、30日保持）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、標準出力のみで継続。
    - 既存ハンドラをクリアして重複を防ぐ実装。
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定（権限不足などは警告してスキップ）。
    - set_cpu_affinity: プロセスを最初の N コアに固定する機能を追加（未対応/権限不足時には警告してスキップ）。
- モニタリング / DB
  - 監視 DB 初期化用の init_monitoring_db 呼び出しが各起動スクリプトで行われるように実装。
  - duckdb を分析用データベースとして利用するための接続を各スクリプトで確立。
- その他ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL 判定を行う。
    - CLI オプションで期間（--from/--to）と DB パス（--db）を指定可能。
    - デフォルト閾値を定義（稼働率 99% 等）し、結果の要約を標準出力に表示。
- 研究用（WIP）
  - research/factor_research.py を追加（モメンタム、ボラティリティ、バリュー等のファクター計算基盤を実装予定）。
    - DuckDB を用いて prices_daily / raw_financials のみ参照する設計。
    - ただし現状コードは途中（WIP）であり未完の箇所あり。

### 変更 (Changed)
- ログの標準出力は stderr ではなく stdout を使用するように変更（cron / スケジューラでの取り扱いを考慮）。
- .env 読み込みの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数は保護（上書き不可）に。

### 修正 (Fixed)
- env 値や設定ファイルの存在チェック、YAML パースエラーなどの検出を強化（validate_config にて報告）。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理を実装（0 以下や非整数は警告してデフォルト 60 秒を使用）。

### 既知の問題・注意点 (Known issues / Notes)
- research/factor_research.py は現状 WIP（途中の関数や未完のコードの断片が存在）。実運用前に完成が必要。
- apply_sector_cap:
  - price_map に価格が無い（0.0）の場合はエクスポージャーが過少見積りされる可能性がある旨がコメントで記載されている（将来的にフォールバック価格を導入する予定）。
- process_priority / set_cpu_affinity:
  - 権限不足（root/管理者権限が必要）や OS 非対応時は警告を出し処理をスキップする実装になっている。
- logging_setup:
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソールのみで継続する。ログ出力先に関する権限/ディスク容量の監視が必要。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で明示的に無効化可能）。
- run_monitoring は監視用 DB として常に settings.sqlite_path を使用するため、環境分離を厳密に行いたい場合は設定に注意が必要。
- Paper Trading では MockBrokerClient のふるまいが PAPER_FILL_MODE に依存する。無効値は Settings で例外になるため起動前に確認が必要。
- ExecutionEngine の実装詳細（リトライやネットワーク障害時の振る舞い等）は本 CHANGELOG からは推測できないため、運用時はログと validate_config の警告に注意。

### セキュリティ (Security)
- なし

---

今後の予定（推測）
- research/factor_research の完成とユニットテスト追加。
- price フォールバックロジック（apply_sector_cap）や銘柄ごとの lot_size 拡張。
- より詳細な監視アラート（LINE 通知など）の実装強化。