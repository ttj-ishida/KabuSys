CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 基本的なアプリケーション構成を追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン "0.1.0" を追加。
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。paper_trading モードでは専用の SQLite（data/paper_trading.db）を使用する。BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行および停止フラグ検出をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: .env 自動ロード（プロジェクトルート検出含む）、細かな .env パース（export 形式、クォート・エスケープ、コメント対応）、Settings クラス（環境変数アクセスラッパー）を実装。環境値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行うプロパティを提供。
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを追加。既存 .env の読み込み、項目定義、書き出しロジックを含む。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）などをチェック。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連の純関数群を追加（DB 参照なし、メモリ内計算）
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア重み配分(calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた資金乗数(calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py: 株数決定ロジック(calc_position_sizes) を実装。risk_based / equal / score の割当方式、単元株（lot_size）、コストバッファ、aggregate cap によるスケール調整、端数処理（lot 単位での追加配分）等をサポート。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティを追加
  - utils/logging_setup.py: 全起動スクリプトで共通利用できるロギング設定ユーティリティを実装。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収したプロセス優先度設定ユーティリティを実装。psutil を利用し優先度設定および CPU affinity 設定を提供。権限不足時は警告でスキップ。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: paper_trading 用 SQLite から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95））を集計してレポート出力。閾値に基づく PASS/FAIL 判定ロジックを実装。コマンドラインから期間指定や DB パス指定を可能にする。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details / 注意事項
- .env 自動読み込み
  - config._find_project_root() により __file__ を起点にプロジェクトルートを探索し、.env/.env.local を自動ロードする。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の読み込みは OS 環境変数を保護し、.env.local は上書きモードで読み込まれる（OS 環境変数は上書きされない）。
- run_monitoring の挙動
  - 監視プロセスは MONITOR_POLL_INTERVAL によりポーリング間隔を制御。0 以下や不正な値はデフォルトの 60 秒にフォールバックする。
  - 監視は Settings.sqlite_path（本番用設定）を使用する設計のため、環境変数 KABUSYS_ENV に関わらず monitoring は本番 DB パスを見に行く点に注意。
- run_execution の挙動
  - KABUSYS_ENV=paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計。
  - ExecutionEngine は別スレッドで run_session を実行し、data/stop_requested.flag の存在で安全停止させる。
- ロギング
  - setup_logging() は既存ハンドラをクリアしてから再設定するため、複数回呼び出しても重複登録されない。
  - ログディレクトリの作成に失敗した場合は標準エラーに警告を出力し、ファイルハンドラは無効化される（コンソール出力は継続）。
- 研究用ファクターモジュール
  - research/factor_research.py を追加（設計コメントおよび多くの実装が含まれる）が、ファイル末尾で実装が途中で終わっている箇所が見られます（WIP）。今後の追加実装・テストが必要です。

今後の TODO / 既知の改善点
- research/factor_research.py の未完部分を完成させる（target_date 周りの SQL 実行・結果整形など）。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）を実装して過少見積りの問題を改善する。
- tests（ユニット・統合）を追加して portfolio ロジック、config パーサ、起動スクリプトの主要フローを自動検証する。
- ドキュメント（README、PortfolioConstruction.md 等）と CLI のマニュアル強化。

以上。