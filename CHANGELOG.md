# Changelog

すべての重要な変更履歴はここに記載します（Keep a Changelog 準拠）。  
このプロジェクトのバージョニングは SemVer に従います。

## [0.1.0] - 2026-04-19

### Added
- 基本機能の初回リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行スレッドで engine.run_session() を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行用 pid ファイル（data/execution.pid）対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず production 相当の sqlite_path を使用（監視テーブルの初期化を実施）。
    - 停止フラグでループを終了。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数経由で各種設定を取得（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境等）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env を自動ロード（オーバーライド挙動・保護機構あり）。
    - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成／更新する CLI。
    - デフォルト値・シークレットマスキング・保存確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML ファイルの存在とパースチェック（PyYAML が無ければ警告）。
    - --strict モードで警告も FAIL 扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - ログレベル・ログディレクトリ解決ルールを実装し、ディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定 set_process_priority(level)。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を提供（権限や未対応 OS の場合は警告を出してスキップ）。
    - psutil 利用、アクセス権限不足や未実装 API の例外を安全にハンドリング。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順に並べ上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用して候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 等）を返す。未知レジームは警告のうえフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて銘柄別発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、スケーリング後の残差配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を集計して検証レポートを生成する CLI。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、閾値の定義を実装。
- 研究用ファクター計算モジュール（下地）
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤（モメンタム / MA / ATR / 流動性等を想定）。関数設計・定数を定義（calc_momentum 等、部分実装あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 監視（monitoring）実行では監視用 DB テーブルの初期化（init_monitoring_db）を行い、環境にかかわらず settings.sqlite_path を使用する設計。実行 (execution) は paper_trading モード時に DB を分離するため、運用上の DB 分離が容易。
- .env パーサーはシングル/ダブルクォート内のバックスラッシュエスケープや inline コメント処理をサポート。export プレフィックスも許容。
- logging_setup は標準出力に stdout を使う設計（cron 等で stdout/stderr をまとめてリダイレクトする運用想定）。
- process_priority はプラットフォーム差分や権限不足を考慮して安全にフォールバックするよう実装。
- position_sizing の aggregate スケーリングは lot_size 単位での再分配を行い、端数処理で再現性を保つためソート基準を安定化している。

### Known issues / TODO
- portfolio/position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の扱いについて注記があり、将来的に前日終値等のフォールバック実装を検討する旨が記載されています。
- research/factor_research.py:
  - ファイル末尾で calc_momentum の実装が途中で切れている（部分実装）。完全実装が必要。
- .env に関する自動読み込みはプロジェクトルートの自動検出に依存するため、配布後やパッケージ化環境で動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD に注意。

---

（初回リリース: 基盤ライブラリ・運用ツール・CLI・ポートフォリオ構築ロジックを含む包括的な機能群を提供します。今後はテストの追加、factor_research の完成、ドキュメント整備、例示的設定ファイルの追加等を予定しています。）