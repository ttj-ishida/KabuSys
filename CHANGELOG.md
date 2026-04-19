Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在差分はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース（0.1.0）。
- 実行および監視用の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使って本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - 停止フラグ (data/stop_requested.flag) の検知による安全停止処理を実装。
    - PID ファイル出力（data/execution.pid）サポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告ログ出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt による終了処理を実装。
- 設定関連
  - config.py
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の高度なパース実装（export プレフィックス、クォート内エスケープ、インラインコメント処理の取り扱いなど）。
    - Settings クラスを追加し、環境変数アクセスをラップ（J-Quants / kabu API / DB パス / 各種閾値 / 環境判定プロパティ等）。
    - 環境変数の必須チェック用 _require() 実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - デフォルト値・選択肢・シークレット入力等をサポートし、最終的に .env を安全に書き込む機能を提供。
  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検証。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_DIR 作成失敗時はファイル出力をスキップしコンソールのみで継続するフェールセーフ実装。
    - ログレベル解決の優先順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity の設定ユーティリティを提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順 + signal_rank によりタイブレークして候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重（スコア合計が 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中を監視し、既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 (bull=1.0, neutral=0.7, bear=0.3)。未知のレジームは 1.0 にフォールバックして警告。
      - 注記: 価格が欠損した場合のフォールバックは TODO コメントで指摘（将来的な改善点）。
    - position_sizing.py
      - calc_position_sizes: allocation_method に応じた発注株数算出（"risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク率・stop_loss に基づく株数計算、lot_size（単元株）で丸め。
      - aggregate cap（利用可能現金を超える場合）のスケーリング、lot 単位での再配分ロジックを実装。
      - cost_buffer を考慮した保守的な見積りを実装。
- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), レイテンシ（avg, max, P95）。
    - デフォルト閾値を定義し PASS/FAIL 判定を行う（稼働率 >=99.0%, fill >=90%, send >=95%, P95 <=200ms）。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。テーブル未存在時は安全に N/A を扱う。
- 研究用モジュール（骨組み）
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算の方針と一部定数・関数骨子を追加（モメンタム / MA / ATR / Volume 指標）。処理設計と定数（例: 1M/3M/6M、MA200、ATR20 等）を定義。
    - （注）ファイル末尾が途中で切れているため、実装は継続中・拡張予定。

Fixed / Robustness
- config._load_env_file / _parse_env_line
  - export プレフィックス、引用符付き値のエスケープ、コメントの解釈などを考慮して .env をより堅牢にパース。
- logging_setup
  - ログディレクトリ作成失敗時に FileHandler 作成をスキップすることで、起動環境に依存しない安全な動作を実現。
- process_priority
  - 権限不足や未対応プラットフォームで例外を吸収し、警告を出して処理を継続。

Known issues / Notes
- research/factor_research.py は現状で実装が途中（ファイル末尾が途切れている）。本格利用前に完成させる必要あり。
- apply_sector_cap の価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積りされる可能性）は TODO コメントで指摘。前日終値等のフォールバックを実装するとより安全。
- run_monitoring は「監視用 DB を環境にかかわらず本番 sqlite_path を使用する」設計になっているため、paper_trading 環境で監視を分離したい場合は運用上の注意が必要。
- calc_position_sizes の将来拡張案として、銘柄別の lot_size 管理を導入する旨の TODO がある（現在は共通 lot_size を想定）。
- ログファイルの未作成やディレクトリ作成失敗時は標準出力のみになり得るため、運用環境でログディレクトリ権限を確認することを推奨。

Environment / Defaults
- .env 自動読み込み: プロジェクトルートが検出できる場合、自動で .env と .env.local を読み込む（OS 環境変数は上書きされない）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要環境変数のデフォルト:
  - KABUSYS_ENV: development
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - MONITOR_POLL_INTERVAL: 60 (秒)

その他
- パッケージバージョン: __version__ = "0.1.0"

脚注
- 本 CHANGELOG はソースコードから推測可能な変更点・設計方針・既知の注意点をまとめたものです。実際のコミット履歴がある場合はそれに基づく詳細な変更履歴（個別コミットや PR 単位）を別途付記することを推奨します。