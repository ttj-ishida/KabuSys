# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（src/ 以下）の内容から推測して作成しています。実際のコミット履歴ではなく、現状実装されている機能・修正点のサマリです。

※バージョン番号は package の __version__ に合わせて 0.1.0 を初回リリースとみなしています。

## [Unreleased]

### Added
- research/factor_research モジュールの骨組みを追加（モメンタム、ボラティリティ、リクイディティ等のファクター計算を想定）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。
  - P95 計算等のユーティリティも含意（未完の実装あり）。
- portfolio モジュールのユーティリティを拡張・安定化予定（ドキュメント参照: PortfolioConstruction.md / StrategyModel.md に準拠）。

### Changed
- 一部関数に TODO / 拡張メモを残し、将来的な拡張点（個別銘柄の lot_size 対応、価格フォールバックなど）を明示。

### Known issues / TODO
- research/factor_research の実装が途中で終端している（calc_momentum の途中）。完成・テストが必要。
- position_sizing の price フォールバック（price が 0 の場合の挙動）に関する注意が残っているため、実運用前の検証推奨。
- 一部の外部依存（psutil、PyYAML、duckdb、sqlite3）に対する環境準備が必要。

---

## [0.1.0] - 2026-04-24

安定稼働を目指した初期リリース。運用用の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティを含む。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV に応じて paper_trading（専用 SQLite）と本番 DB を分離して接続するロジックを実装。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - ExecutionEngine の起動・スレッド監視、停止フラグ（data/stop_requested.flag）検知による安全停止処理。
    - 実行 PID 管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知によるループ終了、monitor.check_once() の例外をログに残し継続する堅牢化。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境管理
  - config.py
    - Settings クラスでアプリケーション設定（環境変数アクセス）を一元化。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml）、.env と .env.local の読み込み順（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - 各種設定プロパティ（DB パス、LINE トークン、環境種別、しきい値など）を実装。
    - PAPER_FILL_MODE の検証・バリデーション実装。
  - config_setup.py
    - .env の対話式ウィザード（初期作成・更新）を実装。
    - シークレットマスク、選択肢提示、既存値再利用、保存確認の対話フローを提供。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の基本的な妥当性チェックを実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config YAML の存在と簡易パース検証（PyYAML がある場合）。
    - --strict モードを追加（警告を FAIL 扱いにして exit(1)）。
    - 本番環境向けガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START の危険設定の警告）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（スコア順ソート・上位抽出）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコア 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。既存ポジションのセクター露出を計算し、上限超過セクターの候補銘柄を除外）
    - calc_regime_multiplier（market regime による投下資金乗数。bull/neutral/bear のマッピングと未知レジームでのフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes（リスクベース / 等金額 / スコア方式に基づく発注株数決定、lot_size による丸め、aggregate cap によるスケールダウンロジック、cost_buffer を用いた保守的見積り、残差処理による追加割当てロジック）

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化ユーティリティを提供（コンソール stdout と TimedRotatingFileHandler 日次ローテーション）。
    - ログディレクトリ作成の失敗に対する graceful fallback（コンソール出力のみ）。
    - LOG_LEVEL / LOG_DIR の解決順を明確化。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを実装（psutil 利用）。
    - 権限不足などの失敗時は警告を出してスキップする堅牢化。
  - utils.__init__ 用意。

- 監視関連
  - monitoring.monitoring_db: 監視用 SQLite DB の初期化関数（init_monitoring_db）を参照して各起動時に監視テーブル存在を保証（冪等）。
  - SystemMonitor（モジュール参照）を用いた稼働状態チェックの呼び出し箇所を整備。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI を実装。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを算出して PASS/FAIL を判定する基準を定義。
    - P95 計算、日付フィルタ（--from / --to）、DB 検査ロジックを実装。

### Changed
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

### Fixed
- .env パーサの強化（config._parse_env_line）
  - export 形式、クォート・エスケープ、インラインコメントの扱い、コメント判定の改善など、実用上の多くのケースをカバー。
- ログ処理の改善
  - StreamHandler を stdout に固定（cron / scheduler でのリダイレクト運用を想定）。
  - 既存ハンドラがある場合はクリアしてから再設定し、二重出力を回避。

### Documentation / Misc
- 各モジュールに docstring と使用例・設計方針のコメントを充実させ、将来的な運用・拡張のヒントを明記。
- config_setup の .env 出力テンプレートにセクション分け・警告（.env を Git にコミットしない）を追加。

### Security
- シークレット値（トークン、パスワード）は CLI でマスク表示。保存先は .env（運用上の取り扱い注意を README 等で追加推奨）。

---

## 参考 / 実装上の注意
- 本リリースはシステム設計に沿った多くのツールとユーティリティを含むが、外部依存（psutil, duckdb, PyYAML 等）のインストール確認と環境（.env、ディレクトリ作成権限、データベースファイルパス等）の事前整備が必要です。
- 一部モジュールに未完成の箇所や将来の拡張点が明記されています（research モジュールの未完、価格フォールバック処理、銘柄別 lot_size の対応など）。本番運用前に追加実装・テストを推奨します。

もし特定ファイルごと、もしくはコミット単位のより詳細な CHANGELOG を希望される場合は、どの粒度（ファイル一覧・機能ごと・想定コミット）で作成するかを教えてください。コードからさらに細かく推測して更新します。