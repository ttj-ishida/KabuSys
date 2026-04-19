# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベース（src/kabusys/）の内容から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 今後の作業用（現時点では空）
- 各リリースは機能追加・変更・修正などのカテゴリで整理

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションの初期実装を追加
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行用スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度の設定（High）を起動時に適用。
    - 環境に応じて paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db、KABUSYS_ENV=paper_trading 時）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御。
  - 監視（モニタリング）起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production の sqlite_path を使用して接続。
    - stop フラグ検知でループ終了、例外発生時はロギングして次ループに継続。
- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 多数のプロパティを提供（J-Quants トークン、kabu API、DB パス、paper_trading 用パス、監視しきい値、環境種別判定等）。
    - PAPER_FILL_MODE のバリデーションおよび有効値チェック。
- .env ウィザード
  - 対話式設定ウィザード (src/kabusys/config_setup.py)
    - .env の生成・更新を対話形式で支援。シークレット項目はマスク表示。
    - デフォルト・選択肢・説明を持つ設定項目群を提供し、.env を安全に書き込む。
- 設定検証 CLI
  - validate_config CLI (src/kabusys/validate_config.py)
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パースチェック（PyYAML 未インストール時はスキップ）。
    - --strict モードで警告を失敗扱いにできる。
- ロギングユーティリティ
  - 統一ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保存）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR 経由での設定・引数優先の解決ロジック。
- プロセス優先度 / CPU affinity ユーティリティ
  - (src/kabusys/utils/process_priority.py)
    - Windows / POSIX を抽象化してプロセス優先度を設定する set_process_priority() を提供。
    - set_cpu_affinity() によるコア固定機能（設定不可時は警告でスキップ）。
- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み付け (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等金額にフォールバック）。
  - リスク調整 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: セクターごとの保有比率上限チェック（売却予定銘柄の除外対応、unknown セクターは適用外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバックで 1.0。
  - ポジションサイジング (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残余キャッシュでの端数補正ロジック。
- Paper Trading 検証ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性・注文成功率・レイテンシ等を集計してレポート出力。
    - P95 計算、稼働率・成功率・送信率・P95 レイテンシに対する閾値判定を実装（閾値はソース内定数で定義）。
    - CLI 引数で期間指定（--from / --to）と DB パス (--db) 指定可能。
- 監視用 DB 初期化
  - init_monitoring_db 呼び出しを実行起動時に行い、監視テーブルの存在を保証（冪等）。
- research / factor 計算の骨組み
  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - Momentum / Value / Volatility / Liquidity 等の計算方針と定数を定義。DuckDB を用いた計算設計。
    - （注）ファイル末尾で calc_momentum 実装の途中で終わっている箇所があり、作業中の状態で追加。

### Changed
- なし（初期リリース）

### Fixed
- 環境変数の数値パースにおける安全性向上
  - MONITOR_POLL_INTERVAL の不正値（0以下や非整数）に対してデフォルトへフォールバックし、警告ログを出力するように実装（run_monitoring.py）。
- .env 読み込みの堅牢化
  - シングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、インラインコメント等を扱えるように .env パーサを実装（src/kabusys/config.py）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- research/factor_research.py の calc_momentum 関数は途中で切れているように見えます（末尾に未完の識別子あり）。この部分は未完成の可能性があるため、本番利用前に実装完了・レビューが必要です。
- 実行・監視用スクリプトはファイルベースの停止フラグ / PID 管理に依存しています。運用環境によっては systemd 等のプロセス管理と合わせて運用することを推奨します。
- .env ファイルには機密情報が含まれるため、README 等に従い決してリポジトリにコミットしないでください（config_setup.py 内にも注意書きあり）。

もし特定のファイル・機能について詳細な変更説明や別バージョンの履歴を作成したい場合は、対象箇所を指定してください。