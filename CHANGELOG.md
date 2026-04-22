CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更・振る舞いの明示
- Fixed: バグ修正／堅牢化
- Deprecated / Removed / Security: 該当なしの場合は記載しません

Unreleased
----------

（なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初回リリースを追加。
- 実行用エントリポイントを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用する挙動をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで検知。
- 設定管理:
  - config.py: 環境変数／.env 自動ロード機能を実装。プロジェクトルート (.git または pyproject.toml を基準) を探索し、.env/.env.local を読み込む。Settings クラスを通じて型付きの設定プロパティ（DB パス、API トークン、しきい値等）を提供。
- 設定ユーティリティ:
  - config_setup.py: 対話式 .env 作成ウィザードを追加（対話入力・既存値読み込み・.env への書き出し）。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在＆パース（PyYAML がある場合）などを検証。--strict モードで警告も失敗扱いにできる。
- ロギング／プロセス管理ユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux/macOS を抽象化したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。psutil を利用し、権限や未サポートプラットフォーム時は警告を出して安全にスキップする。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と配分重み（等金額 calc_equal_weights、スコア加重 calc_score_weights）の純粋関数を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 株数算出ロジック（risk_based / equal / score の allocation_method、単元丸め、aggregate cap によるスケールダウン・端数補正）を実装。
  - portfolio/__init__.py: 上記をまとめてエクスポート。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）などを SQLite のペーパートレード DB から集計して判定（PASS/FAIL）する。
- 研究モジュール（スケルトン）:
  - research/factor_research.py: ファクター計算モジュールのスケルトン（モメンタム、ATR、流動性などの計算方針、関数署名の下地）を追加。DuckDB を介して prices_daily/raw_financials を参照して計算する設計。

Changed
- .env 読み込みの挙動を明確化:
  - デフォルトで OS 環境変数より .env の読み込み優先度を調整（OS > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースを堅牢化（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理を考慮）。
- ロギング:
  - StreamHandler は stdout を用いる（stderr ではなく）。ログレベルやログディレクトリは引数・環境変数で上書き可能。
  - 既存ハンドラを一旦 flush/close してから再設定することで、二重ハンドラ設定を防止。
- 実行時挙動:
  - run_execution と run_monitoring 両方で起動直後にプロセス優先度を "high" に設定する呼び出しを行う（set_process_priority("high")）。
  - run_execution は paper_trading の場合、専用 SQLite（settings.paper_sqlite_path）を使用して監視テーブル等を分離する。init_monitoring_db は冪等に監視テーブルを確保するため呼び出される。
  - run_monitoring は KABUSYS_ENV に依らず「本番用の sqlite_path（settings.sqlite_path）」を監視 DB として使用する旨を明示。
- エラー処理:
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合でも例外を捕捉してログ出力し、ループ継続するように変更（堅牢性向上）。
  - run_execution のスレッド監視ループで stop flag を検知した際に engine.stop() を呼んで安全に停止するロジックを追加。

Fixed
- ファイル/ディレクトリ操作失敗時のフォールバック:
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ生成をスキップし、コンソール出力のみで継続するように安全化。
  - .env ファイル読み込み失敗時は warnings.warn で通知してプロセスを続行する。
- 外部ライブラリ利用に伴う互換性と権限問題をハンドリング:
  - process_priority: psutil による優先度設定や cpu_affinity 設定が AccessDenied / NotImplementedError / AttributeError を出す場合に警告を出してスキップするようにして、実行環境に依存せず安全に動作するよう改善。
- .env パーサ:
  - クォート内のバックスラッシュエスケープ処理やコメント判定を改良し、より実用的な .env 解析を実現。
- Paper Trading レポート:
  - データが存在しないケース（テーブルがない・行がない）を sqlite3.OperationalError や None によって保護し、レポート生成を途中で失敗させないように対策。

Notes / Implementation details
- データベース接続:
  - SQLite（標準 library sqlite3）と DuckDB（duckdb パッケージ）を併用する設計。duckdb は分析・ファクター算出用途、SQLite は監視・トレードログ用途を想定。
- PID / 停止フラグ:
  - 実行系では data/execution.pid、停止フラグは data/stop_requested.flag / data/kill.flag 等のファイルベース制御を採用。
- ポートフォリオ関連:
  - 単元（lot_size）丸め、ポジション上限（max_position_pct）、利用可能資金による aggregate cap、cost_buffer によるコスト見積りなど現実的な制約を組み込んだ設計。スケールダウン時の余剰分配も実装。
- 研究モジュールは途中の実装箇所（ファイル末尾が切れている）あり。今後モメンタム等の詳細実装が続くことを想定。

Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保管する想定。config_setup は .env に関して「絶対に Git にコミットしないこと」を明記している。

今後の改善案（参考）
- research/factor_research.py の完全実装（DuckDB SQL クエリと Z スコア正規化の統合）。
- 単体テストの追加（.env パーサ、position sizing、risk adjustment、reporting 等）。
- Windows サービスや systemd 連携のための起動スクリプト／ユニットファイル提供。
- ログの構造化（JSON）出力やメトリクス収集（Prometheus 等）との統合。

以上。必要であれば、各ファイルごとのより詳細な変更点（行単位の抜粋や想定される API 仕様書）を生成します。どの粒度で出力しますか？