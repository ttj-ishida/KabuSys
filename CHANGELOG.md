# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
本ファイルはコードベースの内容から推測して作成しています。

フォーマット:
- Unreleased: 開発中/次回リリース向けの変更
- 各バージョン: 主要な追加・変更・修正をカテゴリ別に列挙

## [Unreleased]

Added
- research.factor_research モジュールの実装継続（モメンタム等ファクター計算の実装が進行中）。一部関数が未完（解析対象日付の扱いなど）であるため、今後完成予定。

Changed
- なし

Fixed
- なし

## [0.1.0] - 2026-04-23

Added
- 基本アプリケーション構成を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として初期化。
- 起動スクリプト・長時間動作プロセス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite を使用する（本番 DB と分離）。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）をサポートし、安全に停止可能。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグを検知してループを終了。
    - Monitoring は環境に依らず本番の sqlite_path を使用（監視用 DB を保証して初期化）。
- 設定・環境管理
  - config.py: Settings クラスを追加し、環境変数から各種設定値を取得する共通 API を提供。
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）を実装。
    - .env パース: export 前置対応、クォート文字とバックスラッシュエスケープ処理、インラインコメントの扱いなどをサポート。
    - paper_trading 用の PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH などをサポート。値検証（PAPER_FILL_MODE の有効値チェック）を実装。
    - kill/ pid / 監視閾値などのプロパティを提供。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（選択肢・デフォルト値・シークレットマスク対応）。生成テンプレートの書き出し機能を含む。
  - validate_config.py: 起動前の設定検証 CLI を追加
    - 必須/任意環境変数確認、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合は警告）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ動作。
    - 引数 / 環境変数（LOG_LEVEL / LOG_DIR）に基づく柔軟な解決。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加
    - Windows / POSIX の差分吸収（psutil 利用）、安全に失敗を無視するワーニング挙動を実装。
    - set_process_priority(level) により high/normal/low を指定可能。set_cpu_affinity(n) で先頭 N コアにピン留め可能（権限やプラットフォームによりスキップ）。
- 監視・モニタリング基盤
  - monitoring パッケージ（初期化関数呼出しをスクリプトに統合）
    - 起動スクリプトからモニタリング DB 初期化（init_monitoring_db）を呼ぶことで、監視テーブルの存在を保証（冪等処理）。
- Paper Trading / レポート
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加
    - 指定期間内のシステム稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定（閾値判定付き）。
    - DB パスは引数 `--db` / 環境変数 PAPER_TRADING_SQLITE_PATH を優先して解決。
    - P95 計算、null 安全性（テーブル不存在・データ不足時のフォールバック）を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順での候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア正規化による重み計算。スコア合計が 0 の場合は等分配へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジックを実装（unknown セクターは上限適用外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告して 1.0 フォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式を提供。単元株丸め、per-stock 上限、aggregate cap のスケーリング（cost_buffer を考慮）を実装。残差の分配アルゴリズムを含む。
- research/factor_research.py
  - ファクター計算モジュールを追加（モメンタム / MA200 / ATR / 出来高等の設計と定数を定義）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム計算関数の雛形を含むが、実装が中断している箇所あり（今後完成予定）。

Changed
- デフォルトのログ出力先を stdout に明示的に設定（logging_setup）。
- .env の自動ロードポリシー: OS 環境変数を保護して .env/.env.local を読み込むロジックを導入（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート）。

Fixed
- プロセス優先度設定や CPU affinity 設定時の権限不足や未対応プラットフォームでの例外を捕捉して安全にスキップする挙動を実装（警告ログ）。

Documentation
- 各 CLI スクリプト（validate_config, config_setup, paper_verification_report）に使用方法の docstring を追加。
- 各モジュールに関数説明・引数説明を追加して内部ドキュメントを充実。

Known issues / Notes
- research.factor_research.py はモメンタム計算の実装途中でファイル末尾が未完（トークン切れ）。このモジュールは今後の実装完了が必要。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的には銘柄ごとの lot_map へ拡張予定（TODO コメントあり）。
- apply_sector_cap のエクスポージャー算出は price が欠損（0.0）の場合に過少推定となる可能性がある（コメントでフォールバック検討を記載）。

---

作成元: リポジトリ内のソースファイル（src/kabusys/**）の内容から推測してまとめました。実際のリリースノート作成時はコミット履歴や CHANGELOG のルールに基づいて調整してください。