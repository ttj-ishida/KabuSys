CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
このリポジトリのリリースノートはコードベース（ソース内容）から推測して作成しています。

Unreleased
----------

Added
- run_monitoring スクリプトを追加
  - SystemMonitor のポーリングループを起動するエントリポイント（src/kabusys/run_monitoring.py）。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視処理は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用する。
  - 起動時にプロセス優先度を "high" に設定。

- run_execution スクリプトを追加
  - ExecutionEngine を起動するエントリポイント（src/kabusys/run_execution.py）。
  - paper_trading 環境時は MockBrokerClient を使用し、専用の paper_trading DB（data/paper_trading.db）で本番と分離。
  - OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせてセッション実行。
  - 起動時にプロセス優先度を "high" に設定。

- 設定管理を強化（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - OS 環境変数を保護するための上書き制御（protected set）。
  - 複雑な .env 行パース対応（export、クォート内エスケープ、コメント処理など）。
  - 各種設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など）を提供。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を実装。

- Paper Trading 向け検証ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - paper_trading DB から稼働率・注文成功率・送信率・レイテンシなどを集計してレポート出力。
  - 日付フィルタ（--from / --to）や --db オプションをサポート。
  - P95 計算、閾値判定（PASS/FAIL）を実装。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - ポジションサイズ決定（calc_position_sizes）：リスクベース / 等分配 / スコア加重、単元株丸め、集約キャップのスケーリング。
  - 各関数は純粋関数で DB 非依存（メモリ内計算）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続経由で prices_daily / raw_financials を参照）。
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約、ランク関数等。
  - DuckDB を用いた大規模データ集計を前提とした実装。

- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から銘柄単位に集約し、OpenAI API（gpt-4o-mini）でセンチメント（-1.0〜1.0）を計算して ai_scores に書き込む。
  - バッチ送信、トークン肥大化対策、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ等を実装。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は例外を発生。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）。
  - CPU affinity 設定機能（set_cpu_affinity）。
  - 権限不足や未対応環境では安全にスキップして警告ログ出力。

Changed
- DuckDB と SQLite を併用する設計を採用
  - DuckDB は時系列・ファクター計算向けの分析 DB、SQLite はモニタリングや order/replay 用の永続化に使用。

Fixed
- .env パーサの堅牢性向上（クォートやエスケープ、コメント処理の改善）。

Security
- OpenAI API キーの未設定チェックを追加（news_nlp）。

0.1.0 - 2026-04-12
------------------

Added
- 初回公開リリース（バージョン 0.1.0、src/kabusys/__init__.py にて __version__="0.1.0" を定義）。
- 基本アーキテクチャ実装：
  - 実行エンジンと発注フロー（ExecutionEngine / OrderManager / OrderRepository / BrokerClientFactory 等）。
  - 監視コンポーネント（SystemMonitor、監視 DB 初期化 utilities）。
  - 設定管理（自動 .env ロードおよび Settings 抽象）。
  - ポートフォリオ構築・リスク調整・ポジションサイジングのコアロジック。
  - リサーチ用ファクター計算モジュール（momentum / volatility / value）。
  - ニュース NLU による AI スコアリング基盤（OpenAI 連携の下地）。
  - ツール: Paper Trading 検証レポート出力スクリプト。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。
  - DuckDB を用いた分析ワークフローと、SQLite を用いた軽量永続化の混在設計。

Documentation
- 各モジュールに実装方針や注意事項をドキュメンテーション文字列として追加（ファクター定義・時間ウィンドウ等）。

Fixed
- -（初回リリースのため後続で修正予定の既知の TODO をソース内に記載）。

Deprecated
- -（該当なし）。

Removed
- -（該当なし）。

Security
- OpenAI API キー等、秘匿情報は環境変数から取得する設計。未設定時はエラー明示。

Notes / Migration
- paper_trading モードでは data/paper_trading.db に完全分離して記録するため、本番 DB を上書きしません。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効化できます。
- MONITOR_POLL_INTERVAL に不正な値（0 / 負数 / 非数）を与えるとデフォルト（60 秒）にフォールバックして警告を出力します。
- PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL は許可値チェックを行うため、環境変数の値に注意してください。

Contributing
- 変更履歴は今後の変更に合わせて Unreleased セクションに追記し、リリース時にバージョン名と日付を付与してください。

----- End of CHANGELOG -----