CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット
- Unreleased: 今後のリリース向けの変更（現在は空）
- 各リリースは日付付きで記載

Unreleased
----------
（なし）

0.1.0 - 2026-04-18
-----------------

Added
- パッケージ初期公開: 基本的な自動売買フレームワークを追加。
  - バージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止に対応。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する設計。
    - BrokerClientFactory 経由でブローカークライアントを生成（テスト用 Mock をサポートする想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler などの依存コンポーネントを組み立て、ExecutionEngine を別スレッドで実行する制御ロジックを実装。
    - RiskManager の初期設定例（max_position_pct, max_utilization, rate_limit_per_sec 等）を初期値として導入。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の一貫性確保）。
    - 停止フラグ検知、例外捕捉（check_once 内の予期しない例外はログ出力して次ポーリングへフォールバック）、KeyboardInterrupt ハンドリングを実装。
- 設定関連
  - src/kabusys/config.py
    - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの考慮）。
    - .env の読み込みは OS 環境変数を優先し、.env.local で上書き可能（保護対象キーは OS 環境変数として保護）。
    - Settings クラスを提供し、各種設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、ログレベル、KABUSYS_ENV、各種しきい値 etc.）をプロパティ経由で安全に取得。値検証（例: KABUSYS_ENV / PAPER_FILL_MODE / LOG_LEVEL の妥当性チェック）を行う。
    - settings = Settings() をモジュール末尾で提供。
- 設定ユーティリティ・CLI
  - src/kabusys/config_setup.py
    - 対話式 .env 作成・更新ウィザードを実装。既存値の再利用、シークレット値のマスク、選択肢/デフォルト提示、最終確認後に .env を書き込み。
    - 書き込まれる .env にヘッダコメントを付与し、Git コミットしない旨を明記。
  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML があれば深堀り）、本番環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。score が全て 0 の場合は等金額にフォールバックして警告出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄を除外可、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ決定ロジックを実装。allocation_method="risk_based" / "equal" / "score" をサポート。
    - 損切り率・リスク許容率ベースの算出、単元株（lot_size）での丸め、1銘柄上限および aggregate cap のスケールダウンロジック、cost_buffer を使った保守的コスト見積り、端数の公平配分アルゴリズムを実装。
  - src/kabusys/portfolio/__init__.py で上記 API をエクスポート。
- ログ・プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定する setup_logging を実装。既存ハンドラのクリーンアップ、ログレベル解決順（引数 > 環境変数 > デフォルト）、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を提供。
    - stdout を利用することで cron 等で stdout/stderr を一元化した運用を想定。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、失敗時は警告を出してスキップ。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。日付フィルタ (--from / --to) と DB 指定オプション (--db) をサポート。
    - P95 算出と N/A 表示を含む堅牢な出力フォーマットを実装。
- 研究用モジュール（骨格）
  - src/kabusys/research/factor_research.py
    - Momentum などのファクター計算に向けた計算ユーティリティ（calc_momentum 等の設計・定数）を追加（DuckDB 接続前提、prices_daily / raw_financials を参照）。

Changed
- 初期設計として次の運用上のフォールバック・保護を導入:
  - .env ロード時に OS 環境変数を保護対象とすることで意図しない上書きを防止。
  - .env のクォート付き値やエスケープに対応し、より柔軟な値記述を許可。
  - ログディレクトリ作成に失敗した場合でもコンソールログ出力で継続できるように変更。
  - run_monitoring と run_execution で DB 接続の確実なクローズを finally ブロックで保証。

Fixed
- 例外ハンドリング改善:
  - monitoring のポーリングループ内で check_once が例外を投げてもループ継続し、例外ログを出力するように対応（運用継続性の向上）。
  - 各種ファイル/ディレクトリ操作で失敗した場合に警告を出し、安全にフォールバックする挙動を追加。

Security
- config_setup の出力確認時にシークレット項目（JQUANTS_REFRESH_TOKEN 等）をマスク表示するように実装。

Notes / Known limitations
- research/factor_research.py はモジュール設計と一部実装（calc_momentum の導入）を含むが、ファイル末尾で切り出し・未完の箇所があり、まだ完全実装されていない箇所があります。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map に拡張する予定（TODO コメントあり）。
- apply_sector_cap の exposure 計算で price が 0.0 の場合に過小評価される可能性があり、将来的にフォールバック価格導入を検討中（TODO コメントあり）。
- ブローカークライアントの実装詳細（実ブローカ/Mock の切替など）は別モジュール（BrokerClientFactory）に依存しており、運用環境に合わせた実装が必要。

---

今後の予定（例）
- research モジュールの完成（ファクター計算の全実装）
- ExecutionEngine と監視の相互連携の強化（アラート送信、より詳細なメトリクス収集）
- 単体テストと CI の追加、ドキュメント整備（API ドキュメント・運用手順）