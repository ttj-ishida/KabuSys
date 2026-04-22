CHANGELOG
=========

すべての重要な変更点は「Keep a Changelog」規約に従って記録しています。  
日付はコード内の参照や現在時点の想定日付を基にしています（推定）。

Unreleased
----------
- なし

[0.1.0] - 2026-04-22
--------------------

Added
- コア実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離する設計。  
    - ブローカークライアントの抽象化 (BrokerClientFactory) により本番／モックの切替をサポート。  
    - エンジン停止用の stop フラグ（data/stop_requested.flag）・PID ファイル管理を実装。スレッドでエンジンをデーモン実行し、外部停止フラグを監視して安全に停止する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境設定にかかわらず本番 sqlite_path を利用する挙動（意図的設計として明記）。  
    - 停止フラグ検知時の安全終了処理を実装。

- 設定関連
  - config.py: 環境変数 / .env の読み込み・ラッパーを実装。  
    - プロジェクトルートの自動検出 (.git / pyproject.toml) に基づく .env 自動読み込み機能。  
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応（堅牢化）。  
    - Settings クラスを提供し、各種設定（パス、閾値、Paper Trading 用設定、ログレベル判定等）をプロパティ経由で取得可能。  
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH の専用プロパティを追加。  
  - config_setup.py: 対話式ウィザードを実装し .env の初期作成/更新をサポート。  
    - シークレット項目は表示マスク、既存値の再利用、確認プロンプト、.env 出力テンプレートを提供。

- 検証ツール
  - validate_config.py: 起動前の環境変数・config/*.yaml の検証 CLI を実装。  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がなければ YAML 検証をスキップする挙動、本番時の追加警告などを含む。  
    - --strict オプションで警告をエラー扱いにするモードをサポート。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーへ設定。既存ハンドラを一度クリアして再設定するため二重登録を防止。  
    - LOG_DIR 環境変数や引数でログディレクトリ・ログレベルを上書き可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を追加。  
    - Windows / POSIX(Linux, macOS, FreeBSD) の差分を吸収。失敗時は警告を出してフォールバック。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と配分重み（等金額・スコア加重）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジームに応じた乗数（calc_regime_multiplier）を実装。  
    - セクター不明 ("unknown") は上限適用対象外にする旨を明記。  
    - 市場レジーム (bull/neutral/bear) に対する乗数を定義、未知レジームはフォールバック（1.0）し警告を出す。
  - portfolio/position_sizing.py: 単元株丸め、リスクベース／等配分／スコア配分の株数決定ロジックを実装。  
    - max_position_pct、max_utilization、lot_size、cost_buffer による上限・保守的見積りを考慮。  
    - aggregate cap 超過時のスケールダウンロジックと残差に基づく追加配分アルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計。閾値を定義して PASS/FAIL を判定。  
    - --from / --to / --db オプションにより期間・DB を指定可能。DB が存在しない場合はエラー表示。

- research/factor_research.py
  - ファクター計算モジュールの骨格を追加（モメンタム等の定数定義、calc_momentum の設計・API を開始）。DuckDB 経由で prices_daily/raw_financials を参照する設計方針を明記。

Changed
- デフォルト挙動・安全性の向上
  - run_monitoring.py / run_execution.py 起動時に最初にプロセス優先度を "high" に設定するようにして、重要プロセスの優先度を確保する設計に変更（ただし権限不足時は警告でフォールバック）。  
  - logging_setup: 既存ハンドラを明示的に flush/close して削除してから新規ハンドラを追加するようにし、重複出力を防止。
  - .env 自動読み込みでは OS 環境変数を保護し、.env.local は .env より優先して上書き可能にした（既存 OS 環境変数は保護）。

Fixed
- .env パーサの堅牢化
  - 引用符付き値でのバックスラッシュエスケープ処理や行内コメントの扱いを正しく処理するよう改善。export プレフィックスのサポートを追加。
- file handler 作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合はファイルハンドラ生成をスキップし、ストリームのみで継続するようにして起動失敗を回避。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装は骨格が含まれていますが、（ファイル末尾に一部断片的なコードが残っているなど）実装未完の箇所があります。ファクター計算の SQL 実装や端数処理の追加が今後の作業課題です。  
- monitoring のドキュメントにある通り、監視プロセスは「環境にかかわらず本番 sqlite_path を使用する」仕様になっています。デプロイ運用時に意図しない DB を参照しないよう注意してください。  
- process_priority / cpu_affinity の設定は権限が必要な操作を含みます。権限不足時は警告でフォールバックしますが、期待どおりに優先度が反映されない場合があります。

Authors
- KabuSys 開発チーム（コードベースの記述から推定）

License
- プロジェクトルートのライセンスファイルに従ってください（ここではコードから特定できません）。