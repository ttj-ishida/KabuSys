# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - KabuSys 初期リリース。一連の起動スクリプト、設定管理、運用ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどを追加。
  - パッケージのメタ情報: `kabusys.__version__ = "0.1.0"` を設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成（Mock vs 実ブローカー）。
    - エンジンは別スレッドで実行し、`data/stop_requested.flag` の存在で安全に停止できる仕組みを実装。
    - PID ファイル保存（`data/execution.pid`）対応。
    - プロセス優先度を起動直後に "high" に設定（`utils.process_priority.set_process_priority` を使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを開始する起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告ログを出してデフォルトにフォールバック。
    - 監視用 DB 接続は環境にかかわらず production の `sqlite_path` を使用する設計。
    - 停止フラグ（`data/stop_requested.flag`）でループを終了。

- 設定管理・セットアップ
  - config.py
    - 環境変数の読み込みと Settings クラスを追加。
    - 自動 .env ロード機能を実装（プロジェクトルートの検出は `.git` または `pyproject.toml` を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースは `export KEY=val`、クォート・エスケープ・インラインコメントを考慮した堅牢な実装。
    - `PAPER_FILL_MODE` の許容値チェック、`PAPER_TRADING_SQLITE_PATH` など各種パス・閾値設定、`KABUSYS_ENV` の妥当性チェックなどを提供。
    - settings インスタンスをエクスポート。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - 秘密値はマスク表示、選択肢・デフォルト値の提示、既存 .env の読み込み・Enter で再利用などをサポート。
    - 書式化されたテンプレートで .env を出力（.env を絶対に commit しないよう注意喚起）。

  - validate_config.py
    - 起動前に環境変数・config YAML・パス等の妥当性を検証する CLI を追加。
    - 必須環境変数のチェック、`KABUSYS_ENV` / `LOG_LEVEL` の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合は）パース検証を実施。
    - `--strict` オプションにより警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 全アプリで共通利用するロギング設定を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - ログディレクトリの作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続。
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。

  - utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - アクセス権限不足や未対応プラットフォーム時は警告ログを出し安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、シグナルランクでタイブレーク）、等金額配分、スコア加重配分を提供。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存ポジションのセクターエクスポージャーを計算し超過セクターの候補除外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。

  - portfolio/position_sizing.py
    - 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer（スリッページ・手数料見積り）を考慮した調整を実装。
    - 負荷分散のための端数処理（残差に基づく追加配分）も実装。

  - portfolio/__init__.py
    - 各関数を外部向けにエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、レイテンシ (avg/max/P95)、リスク却下数 を集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`。CLI で `--from` / `--to` / `--db` を指定可能。
    - P95 の独自実装を含む。閾値はソース内定数で調整可能。

- 監視（monitoring）
  - run_monitoring.py で SystemMonitor を初期化・起動。監視 DB 初期化（`init_monitoring_db`）を実行。
  - 監視ループでは `monitor.check_once()` を呼び例外をキャッチして次ポーリングへ継続。

- リサーチ
  - research/factor_research.py（骨格）
    - モメンタム、ボラティリティ、流動性、バリュー等のファクター計算のためのモジュール追加（DuckDB 接続を利用する設計）。
    - 関数 calc_momentum の記述開始（引数・目的の説明あり）。（注: 実装途中）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境設定ファイル (.env) を出力する際に「絶対に Git にコミットしないこと」を README/コメントで明示。

### Notes / Known issues
- research/factor_research.py の calc_momentum 実装は途中で終端しており、完全実装は未完。今後のリリースで継続実装予定。
- position_sizing の注釈にある通り、将来的には銘柄ごとの lot_size を stocks マスター等から取得する拡張を検討中。
- apply_sector_cap は "unknown" セクターの銘柄に対しては上限適用を行わない設計（注意点としてコメントあり）。
- process_priority の適用は OS 権限依存（AccessDenied が発生する場合は警告を出してスキップ）。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後の動作や非標準配置のケースでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に管理することを推奨。

---

その他の詳細や CLI の使い方は各モジュールの docstring / モジュールヘッダを参照してください。