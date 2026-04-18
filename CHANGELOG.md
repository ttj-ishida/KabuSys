CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- なし

0.1.0 - 2026-04-18
------------------

Added
- 初回リリースを公開。
- 実行・監視用の起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient を利用することで本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag ファイルで制御。
- 設定管理・ユーティリティ:
  - config.py: 環境変数と .env ファイルの自動読み込み、強制取得ヘルパー（_require）や Settings クラスを提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py: 対話式 .env 作成／更新ウィザード（秘密値のマスク表示、デフォルト／選択肢サポート、.env 出力テンプレートを生成）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性チェックを行う CLI。--strict モードで警告をエラー扱いにできる。PyYAML が未インストールの環境では YAML 検証をスキップして警告を出す。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）:
  - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数計算 (calc_regime_multiplier)。
  - portfolio.position_sizing: position sizing ロジック (calc_position_sizes)。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を使った保守的見積りを実装。
- 監視・実行共通ユーティリティ:
  - utils.logging_setup: stdout ストリームと日次ローテーションファイルハンドラ（TimedRotatingFileHandler）を組み合わせた統一ロギング設定。ログディレクトリ自動作成、失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: Windows / POSIX の差を吸収したプロセス優先度設定（high/normal/low）、および CPU affinity 固定ユーティリティ。権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。
- Paper Trading 検証ツール:
  - tools.paper_verification_report: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、API レイテンシ等を集計して人間向けレポートを出力。閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。--from/--to/--db コマンドライン引数をサポート。
- リサーチ（ファクター計算）スケルトン:
  - research.factor_research: モメンタム等のファクター計算を行うモジュールの実装を開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（実装は引き続き拡張予定）
- パッケージメタ:
  - パッケージ初期化で __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed / Robustness improvements
- .env パーサーの強化（config._parse_env_line）:
  - export プレフィックス対応、シングル/ダブルクォートされた値のバックスラッシュエスケープ処理、インラインコメント処理、クォートなしのコメント認識ロジックなどを実装し、より多様な .env フォーマットに耐えるようにした。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL の値検証を追加。1 未満や非整数入力は警告を出してデフォルトにフォールバックするように処理。
- utils.logging_setup:
  - ログディレクトリの作成に失敗した場合でもコンソール出力のみで継続するフォールバックを実装し、起動時にログ出力が致命的に失敗するのを防止。
  - StreamHandler を stdout に固定（stderr ではなく）して、cron/task scheduler と出力の一貫性を保つ。
- utils.process_priority:
  - OS 判定や psutil の環境差を考慮して例外をキャッチし、設定不能時は警告を出してスキップする安全な実装。
- run_execution.py:
  - paper_trading モード時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番データと分離するように実装。監視テーブルの初期化は冪等に行う。

Security
- 秘密情報の扱いに配慮:
  - config_setup.py のウィザードでシークレット項目は表示をマスク。
  - .env テンプレート作成時に "絶対に Git にコミットしないこと" を明記。

Notes / Known limitations
- research.factor_research は主要なファクター計算方針とスケルトンを実装しているが、完全実装（全てのファクター計算ロジックの整備）は今後の作業となる。
- position_sizing の lot_size は全銘柄共通で処理している（将来的に銘柄別単元対応を検討）。
- apply_sector_cap は price_map に欠損（0.0）が存在する場合にエクスポージャーを過小評価する可能性がある旨を注記している（フォールバック価格の導入を検討）。
- validate_config の YAML 内容検証は PyYAML を必要とする（未インストール時は検証をスキップして警告を出す）。

開発者メモ
- 起動スクリプトは stop flag / pid file / kill flag 等のファイルベースのオペレーションガードを採用しており、外部プロセスや運用手順から簡単に停止・監視が可能。
- DuckDB と SQLite の併用を想定した設計。分析用途は DuckDB、監視・トレードログは SQLite（paper_trading 用 DB を含む）を使い分ける。
- 今後の優先タスク: research モジュールの完成、単体テスト整備、銘柄別 lot_size 対応、ログの構造化（JSON 出力）検討。