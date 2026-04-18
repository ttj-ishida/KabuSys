CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

フォーマット:
  - Added: 新機能
  - Changed: 既存機能の変更
  - Fixed: バグ修正
  - Deprecated / Removed / Security: 必要に応じて記載

Unreleased
----------
（ありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。thread ベースでエンジンを実行し、
    停止フラグ (data/stop_requested.flag) の検出で安全に停止する。paper_trading 環境では専用の
    paper_trading.db を使用して本番 DB と分離する仕組みを備える。
    - 起動例: python -m kabusys.run_execution
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL
    環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。監視は環境にかかわらず本番の
    sqlite_path を使用する設計。
    - 停止は data/stop_requested.flag の検出で行う。

- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレット項目は
    マスク表示・既存値の再利用に対応。
    - 起動例: python -m kabusys.config_setup
  - validate_config.py: .env と config/*.yaml の基本的な妥当性検証を行う CLI を追加。--strict を
    指定すると警告も失敗扱いにできる。
    - 起動例: python -m kabusys.validate_config

- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の SQLite DB を読み、稼働率・注文成功率・
    レイテンシ等を集計して PASS/FAIL 判定付きレポートを出力するツールを追加。日付フィルタと
    DB パス指定オプションに対応。
    - 起動例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 設定管理・自動ロード機能を追加
  - config.py:
    - プロジェクトルートを .git または pyproject.toml から検出し、.env/.env.local を自動ロード。
      OS 環境変数は上書き保護される（.env.local は override が可能）。
    - 独自の .env パーサを実装（export 形式、クォート文字列・バックスラッシュエスケープ、
      インラインコメントの扱いに対応）。
    - Settings クラスを実装し、各種設定（パス、閾値、API トークン、環境種別など）をプロパティ化。
      値のバリデーション（KABUSYS_ENV/LOG_LEVEL/PAPER_FILL_MODE 等）を行う。

- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、
    スコア加重（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに基づく
    投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく
    株数計算（calc_position_sizes）を実装。単元株丸め、1 銘柄上限、aggregate cap（現金超過時の
    スケールダウン）、cost_buffer（手数料/スリッページ見積り）などを考慮。

- ユーティリティを追加/改善
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次）を
    設定する共通ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力を自動で
    無効化し、コンソール出力のみで継続する。
  - utils/process_priority.py: psutil を用いたプラットフォーム非依存のプロセス優先度設定と CPU
    affinity 設定のユーティリティを追加（Windows / POSIX を吸収）。アクセス権限不足等は警告で
    スキップする実装。

- DuckDB / SQLite の初期化補助
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等に作成）。

- Execution 側の既定値・リスク設定
  - run_execution.py 内で RiskConfig のデフォルト値を設定（max_position_pct, max_utilization,
    rate_limit_per_sec, circuit_breaker 等）し、RiskManager を初期化する例を追加。

Changed
- ロギング挙動の明確化
  - logging_setup で stdout を採用（stderr ではない）し、ログ出力先解決順とフォールバック動作を明記。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重設定を防止。

- .env 自動読み込みの挙動を決定
  - OS 環境変数 > .env.local (override) > .env の順で読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    により自動読み込みを無効化可能。

- モニタリングプロセスのポーリング挙動
  - MONITOR_POLL_INTERVAL 環境変数を数値で受け取り、1 未満や不正値はデフォルト（60 秒）へ
    フォールバック。ログに警告を出す。

Fixed
- .env パーサの堅牢性向上
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、
    インラインコメント処理、空行/コメント行の無視などに対応し、実運用での .env 値取り込みの
    不具合を解消。

- プラットフォーム差分による例外の扱いを改善
  - process_priority.set_process_priority / set_cpu_affinity で psutil の環境差（定数未定義等）や
    アクセス権限不足を捕捉し、例外で停止させずに警告ログを出すよう変更。

Notes / その他
- 本リリースでは research.factor_research.py のモジュール実装（ファクター計算の枠組み）が導入されているが、
  一部実装が続き（未完）となっている箇所があります。今後のリリースで計算ロジックの完成・最適化を行う予定です。
- .env はセキュリティ上 Git にコミットしないことを README 等で再度明記してください（config_setup.py の
  ヘッダーにもその旨を記載済み）。
- 実行スクリプトは外部依存（kabuステーション API、J-Quants トークン、psutil、duckdb、PyYAML 等）を
  要します。validate_config.py で依存や設定の確認を行ってから本番運用してください。

今後の予定（予定的項目）
- research モジュールのファクター計算完備とテスト追加
- ExecutionEngine / RiskManager の単体テスト強化
- ログの構造化（JSON）やメトリクス出力（Prometheus 等）対応検討

---