# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### Added
- 基盤設定・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を用いることで本番 DB と完全分離。
    - エンジンは別スレッドで実行し、data/stop_requested.flag を検出すると正常停止する。
    - 実行 PID を data/execution.pid に書き込む仕組み（pid_file を指定）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番の sqlite_path（data/monitoring.db）を使用する仕様。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt による終了対応。
  - validate_config.py: .env と config/*.yaml の静的検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パス・config ファイル存在チェック、live 環境向けの追加ガードなど。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabuAPI / DB パス / LINE 通知設定など主要項目の対話入力と .env ファイル生成をサポート。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能（テスト用）。
    - .env 解析の強化:
      - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートなしは '#' の前が空白の場合コメントと判定）など。
    - Settings クラスを追加して環境変数のアクセス・バリデーションを集中管理。
      - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須取得メソッド。
      - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
      - DB パス（duckdb_path / sqlite_path / paper_sqlite_path）、監視閾値、PID / kill flag パスなどをプロパティ化。
      - env/log_level の妥当性検査（許容値を明示）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の判定ロジックを追加（既存保有を基に新規候補を除外）。
      - "unknown" セクターは制限の対象外（除外しない）。
      - sell_codes（当日売却予定）をエクスポージャ計算から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
      - リスクベース（risk_based）で risk_pct, stop_loss_pct を考慮した株数算出。
      - 単元株（lot_size）への丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウンを実装。
      - cost_buffer を用いて手数料・スリッページ見積りを保守的に加味。
      - スケーリング時の端数処理で残余キャッシュを再配分するロジックを導入（再現性のため安定ソート）。

- 研究・因子計算
  - research/factor_research.py:
    - DuckDB（prices_daily / raw_financials）を使ったファクター計算機能を追加。
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率を計算。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率などを計算する（スキャン範囲のバッファ考慮）。
    - 設計方針: DuckDB 上のテーブルを参照し、外部 API に依存しない純粋な計算を行う。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): psutil を用いて Windows/Linux（および対応 POSIX）でプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定。権限不足や未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 指定数の最初のコアにプロセスをピン留めする機能（権限不足や未対応環境は警告でスキップ）。
  - run_* スクリプトでプロセス起動時に優先度を "high" に設定する挙動を導入。

- 監視関連
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db）を実装呼び出し箇所へ追加（冪等で監視テーブルを保証）。
  - kill/stop フラグ（data/stop_requested.flag、KILL_FLAG 等）による外部制御をサポート。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポートを生成する CLI を追加。
    - システム稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - P95 計算、日付範囲フィルタ（ISO8601 UTC 文字列化）、DB 存在チェックなどを実装。

- パッケージ情報
  - __init__.py: __version__ = "0.1.0" として初期バージョンを設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
  - ただし各モジュールは以下のような堅牢性対策を含む:
    - .env の読み込みでファイルオープン失敗時に警告を出して継続。
    - process_priority / cpu_affinity は権限不足や未実装例外を捕捉してスキップし、起動を阻害しない。
    - DB クエリでテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値を使用する（レポート生成時など）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし特記。ただし .env は生成時に「絶対に Git にコミットしないこと」を注意書きで明示。

---

注記:
- この CHANGELOG はソースコードから推測してまとめた初期の変更履歴です。リリースノートには実際のコミット履歴や公開時の運用メモ（マイグレーション手順や既知の制限）を追記することを推奨します。