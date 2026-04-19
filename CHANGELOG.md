CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

なし

0.1.0 - 2026-04-19
------------------

Added
- 実行用スクリプト・監視用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 専用 DB を使用し、MockBroker を利用して本番 DB と分離して実行可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag を監視して行う。
- 環境設定管理・検証・ウィザード
  - config.py: Settings クラスを提供。.env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）と高度な .env パース（export 形式、クォート文字列、エスケープ、インラインコメント処理など）を実装。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI。
  - validate_config.py: .env や config/*.yaml の検証 CLI。--strict で警告も失敗扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio.portfolio_builder: 候補選定と等比／スコア加重配分（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター上限フィルタとレジーム乗数（apply_sector_cap, calc_regime_multiplier）。未知セクターは上限制約を適用しない挙動。
  - portfolio.position_sizing: ポジションサイズ計算（risk_based / equal / score）。単元株（lot_size）に丸め、全体投資額が利用可能現金を超える場合はスケールダウンして端数処理（fractional remainder を使ったロット単位再配分）を行う。
- 運用ユーティリティ
  - utils/logging_setup.py: stdout へ StreamHandler、日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一して設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティ。アクセス権限不足等は警告でスキップする。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から期間フィルタで集計し、稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算して PASS/FAIL 判定を出力する CLI。
    - P95 計算、閾値（稼働率 99%、成立率 90% 等）に基づく判定を実装。
- リサーチ用スケルトン
  - research/factor_research.py: モメンタム等ファクター計算の骨格を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。

Changed
- なし（初回リリース）

Fixed / Robustness improvements
- .env の解釈を強化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォートなしでのインラインコメント解釈などに対応し、より実運用に耐えるパーサーに。
- ロギングの堅牢化
  - ログディレクトリ作成に失敗した場合でもプロセスを継続し、コンソール（stdout）のみでログを出すようにフォールバック。
- DB 初期化の冪等性確保
  - run_execution/run_monitoring 起動時に monitoring テーブル群の初期化（init_monitoring_db）を行い、テーブル未作成状態でも安全に起動できるように。
- validate_config: PyYAML の有無を検出して YAML 検証をスキップ可能にし、未インストール時は警告のみ出すように。

Security
- config_setup.py のウィザードで「secret」として定義された項目（J-Quants トークン、kabu API パスワード）は表示時にマスク（****）して表示。`.env` の Git コミット禁止を注意書きで明示。

Notes / Known limitations
- run_monitoring は「環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（settings.sqlite_path）を使用する」旨の設計。監視 DB を環境ごとに分離したい場合は設定を変更してください。
- run_execution は paper_trading の際に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離する設計。
- portfolio/risk_adjustment.py の apply_sector_cap は price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある（TODO コメントあり）。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing の将来的改善点: lot_size を銘柄ごとに持たせる（現在は一律 lot_size=100 を想定）。（TODO コメントあり）
- research/factor_research.py はモジュール骨格と多くの定数・関数の設計を含むが、ファイル末尾に未完の箇所がある（calc_momentum の実装が途中で切れている）。今後の実装が必要。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で失敗する場合があり、失敗時はログに警告を出して処理を続行する。
- paper_verification_report の日付フィルタは内部で ISO8601 UTC 形式に変換して比較しているため、運用上 UTC/ローカルの扱いに注意が必要。

History / Versioning
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

参考: 主な環境変数（抜粋）
- KABUSYS_ENV (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒数)
- PAPER_FILL_MODE (paper_trading 時の fill 挙動: instant | partial | never | reject)

--- 

この CHANGELOG は、リポジトリ内のソースコードとコメントから推測して作成しています。実際の変更履歴やリリースノートはコミット履歴やプロジェクト運用ポリシーに合わせて調整してください。