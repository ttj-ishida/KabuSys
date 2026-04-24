CHANGELOG
=========

すべての重要な変更点を記録します。本書式は「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

v0.1.0 - 2026-04-24
-------------------

Added
- 初期リリースを追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を利用し（data/paper_trading.db、環境変数で上書き可）、BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモン実行ループと stop フラグ検出を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番用 sqlite_path を利用。停止フラグ（data/stop_requested.flag）検知で安全終了。
- 設定管理
  - config.py: 環境変数 / .env の自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。.env / .env.local の読み込み優先度と OS 環境変数保護（上書き禁止）を実装。値のパースは export プレフィックス、クォート文字列、インラインコメント等を考慮。Settings クラスで各種設定値（DB パス、API トークン、ペーパートレード設定、しきい値、ログレベル、KABUSYS_ENV 判定等）を提供。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。入力のマスク表示、デフォルト・選択肢サポート、保存前確認を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の整合性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がない場合はスキップ）や本番向けのガードチェックを実装。--strict により警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル候補の選別（スコア降順・タイブレーク条件）と重み付けロジック（等配分、スコア加重）を実装。スコア全0 の場合は等配分にフォールバックして警告発行。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクター扱いやフォールバック挙動を明記。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングと端数処理を実装。
- 解析・リサーチ
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity といったファクター計算の設計を導入（prices_daily / raw_financials テーブル参照）。モジュール設計、定数定義、P95 計算等のユーティリティを追加（実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加。システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。DB パスの解決（--db、環境変数、デフォルト）をサポート。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler, 30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ継続。ログレベル・ログディレクトリの解決順を定義。
  - utils/process_priority.py: プロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを追加。対応 OS の差分吸収、権限不足・未対応環境でのフォールバックと警告を実装。
- 監視 DB 初期化
  - monitoring.monitoring_db (参照): run_* スクリプトは起動時に init_monitoring_db を呼び、監視テーブルが存在することを保証（冪等）。
- パッケージ情報
  - __init__.py: パッケージ名とバージョンを定義（__version__ = "0.1.0"）。公開 API の __all__ を設定。

Changed
- n/a（初回リリースのため過去変更なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Notes / 実装上の注意
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすることで無効化可能（テスト時など）。
- run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようと試みるが、権限がない環境では警告ログを出してスキップする。
- paper_trading と本番データベースは分離される設計（paper_sqlite_path の使用）。ペーパートレードの振る舞いは設定で細かく制御可能（PAPER_FILL_MODE 等）。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソールログのみで継続するため、運用環境では logs ディレクトリの作成権限を事前確認することを推奨。
- position_sizing では価格欠損時のフォールバックが未実装（TODO コメントあり）。実運用では前日終値等のフォールバックを検討してください。
- research/factor_research は全面実装が完了していない箇所が存在するため、利用前に実装状況を確認してください。

作者 / Contributing
- このリポジトリの初期実装に含まれる CLI とモジュール群は、ローカル実行・ペーパートレード検証・本番実行（KABU API 連携）を想定しています。バグ報告・改善提案は Issue を作成してください。

ライセンス
- ソースに別途表記がない限り、プロジェクトの許諾条件に従ってください。