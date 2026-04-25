# Changelog

すべての重要な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。  

注: 以下の履歴は提供されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-25

### Added
- 主要コンポーネントを含む初回リリース相当の実装を追加。
  - パッケージ情報
    - src/kabusys/__init__.py: __version__ = "0.1.0"
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
      - 監視は環境にかかわらず本番用 sqlite_path を使用（監視用テーブルの初期化を実行）。
      - duckdb を併用して分析 DB に接続。
      - 起動時にプロセス優先度を "high" に設定。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient 想定）。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止フラグで実行エンジンを安全に停止。PID ファイル管理（data/execution.pid をデフォルト）。
  - 設定・環境管理
    - src/kabusys/config.py
      - .env の自動読み込み機能（.env, .env.local）。OS 環境変数を保護するためのオプションを実装。
      - 複雑な .env パース対応（export 形式、シングル/ダブルクォート内のエスケープ、コメント処理）。
      - Settings クラスを提供し、環境変数をプロパティとして安全に取得（必須チェック・デフォルト値・バリデーション含む）。
      - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。
      - 監視閾値（CPU/MEM/DISK）や PID / kill flag のパス等のプロパティを提供。
      - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - src/kabusys/config_setup.py
      - 対話式 .env 作成・更新ウィザードを追加。複数の設定項目（環境、トークン、DB パス、ログレベル等）をガイド。
      - 既存 .env の読み込み、入力時のマスク表示、保存前の確認を実装。
    - src/kabusys/validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が利用可能な場合）等をチェック。
      - --strict オプションで警告も失敗扱いに変更可能。
  - ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日分保持）をルートロガーに設定。
      - LOG_LEVEL / LOG_DIR の解決順とファイル出力失敗時のフォールバック処理を実装。
    - src/kabusys/utils/process_priority.py
      - プロセス優先度設定と CPU affinity 設定のユーティリティを追加。
      - Windows と POSIX (Linux/Mac/FreeBSD) に対応。権限不足などは警告でスキップ。
  - ポートフォリオ構築ライブラリ（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分の重み計算（スコア全体が 0 の場合は等金額にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限の適用（既存ポジションのセクター比率に基づく候補除外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数(bull/neutral/bear) を提供（未知レジームはフォールバックと警告）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: 各銘柄の発注株数算出ロジック（risk_based / equal / score の allocation_method、lot の丸め、個別上限・ aggregate cap のスケーリング、cost_buffer を考慮）。
      - aggregate cap 超過時のスケールダウンと余剰キャッシュを用いた lot 単位での再配分アルゴリズムを実装。
  - リサーチ / ツール
    - src/kabusys/research/factor_research.py
      - ファクター計算モジュールの骨組みを追加。Momentum / Value / Volatility / Liquidity の設計と定数を定義。DuckDB の prices_daily / raw_financials を用いた計算を想定。
      - モメンタム計算関数 calc_momentum の実装開始（コードは途中まで含まれる）。
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード検証レポート生成スクリプトを追加。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を行う。
      - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間や DB パスを指定可能。
  - DB 初期化ヘルパー
    - src/kabusys/monitoring/monitoring_db.py （参照されているが今回コード一覧には未表示）
      - init_monitoring_db を run_* スクリプトが呼び出して監視テーブルが存在することを保証（冪等）。

### Changed
- （初回リリースのため該当なし）  

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 重要なシークレット（J-Quants リフレッシュトークン、kabu API パスワード等）は .env に保存する前提だが、config_setup の注意書きで .env を Git にコミットしないよう明示。

### Notes / Known limitations / TODO
- research/factor_research.py は実装が途中で一部欠けているファイルが存在（calc_momentum の途中）。リサーチ系の完全実装は今後の作業。
- position_sizing.calc_position_sizes では lot_size を全銘柄共通で扱っている。将来的に銘柄別 lot_map を受け取る拡張が想定されている（TODO コメントあり）。
- apply_sector_cap はセクター不明 ("unknown") の銘柄に対しては上限を適用しない設計。price が欠損（0.0）の場合、エクスポージャーが過少評価されてブロックが外れる可能性がある旨の注意あり。
- run_monitoring / run_execution といった長時間デーモン向けプロセスは、stop フラグ / kill flag 等の外部制御を前提とする。運用時は kill フラグ運用ルールに注意。
- process_priority の操作は権限依存であり、権限不足時は警告を出してスキップする実装。

---

今後のリリースでは以下の項目が想定されます（例）:
- research/factor_research の完成（全ファクター実装）
- テスト・ドキュメントの拡充
- ブローカークライアント実装の詳細化とエンドツーエンドの統合テスト
- 銘柄別 lot_size 対応、手数料・スリッページモデルの明確化

もし特定ファイル単位でさらに詳しい変更点（例えば関数単位の挙動や想定ユースケース）を反映した Changelog を希望される場合は、対象ファイル名を指定して下さい。