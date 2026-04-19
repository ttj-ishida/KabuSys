CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

[Unreleased]
-------------

- なし（初期リリースに向けた状態）


[0.1.0] - 2026-04-19
--------------------

Added
- 基本アーキテクチャと CLI 起動スクリプトを追加
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用して paper_trading DB（デフォルト: data/paper_trading.db）を利用する仕組みを導入。起動・停止に stop flag と PID ファイルを利用。
  - src/kabusys/run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。

- 環境設定 / 検証 / ウィザード
  - src/kabusys/config.py: 環境変数/ .env の読み込みと Settings クラスを実装。自動 .env ロード（プロジェクトルート検出: .git / pyproject.toml 基準）、高度な行パーサ（export 形式、クォート、インラインコメント対応）を実装。PAPER_FILL_MODE の検証、各種パスや閾値のプロパティを提供。
  - src/kabusys/validate_config.py: 起動前に .env と config/*.yaml の不備を検出する CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML 非インストール時は YAML 検証をスキップして警告。
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。既存 .env の読み込み・編集、保存前の確認をサポート。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合に等配分へフォールバックする挙動を含む。
  - src/kabusys/portfolio/position_sizing.py: 発注株数決定関数 calc_position_sizes を実装。allocation_method（risk_based / equal / score）対応、lot_size（単元）丸め、aggregate cap によるスケールダウンロジック、cost_buffer を考慮した保守的推定を実装。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中管理 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジーム時はフォールバックと警告出力。

- ログとプロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py: ルートロガーの共通設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定する。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックあり。
  - src/kabusys/utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）を吸収し、権限不足や未対応 OS 時は警告を出してスキップする安全設計。

- 監視 DB 初期化 API
  - src/kabusys/monitoring/*（呼び出し元として init_monitoring_db, SystemMonitor を使用）により、監視用テーブルの冪等な初期化を実行可能。起動スクリプトから確実に監視テーブルが存在することを保証。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading DB（デフォルト: data/paper_trading.db）からシステム安定性・注文成功率・レイテンシ等を集計し、PASS/FAIL 判定付きのレポートを標準出力へ出力するスクリプトを追加。P95 計算、閾値（稼働率/成功率/送信率/レイテンシ）を定義。

- リサーチ用ファクターモジュール（初期実装）
  - src/kabusys/research/factor_research.py: DuckDB 接続を受け取ってモメンタム等のファクターを計算する骨子を追加（モメンタム期間等の定数設定を含む）。（ファイル末尾は一部未完の箇所あり、今後の実装継続予定）

Changed
- ルートパッケージのバージョンを設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加（パッケージバージョン管理を明示）。

Fixed
- 起動/監視ループの堅牢性向上
  - run_monitoring.py: monitor.check_once() 内で例外が発生してもループを継続するように例外キャッチを追加（ログ出力して次のポーリングへ）。
  - run_execution.py: 起動時に既に停止フラグが立っている場合は起動を中止してログ出力する安全策を追加。スレッド停止時は engine.stop() を呼び出して安全に終了させる仕組み。

- DB 接続とクリーンアップ
  - run_monitoring.py / run_execution.py: 終了時に sqlite3 / duckdb 接続を必ずクローズする finally ブロックを導入。

Security
- 環境変数の取り扱いにおける注意点
  - config_setup.py の生成する .env に対して「.env は絶対に Git にコミットしないこと」を明記。
  - config.py の _require() は必須環境変数が未設定の場合に ValueError を投げ、起動前に明確に失敗させることで秘密情報の未設定を早期に検出。

Notes / Implementation details（実装上の注記）
- .env 自動読み込みはデフォルトで有効だが、テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能。
- logging_setup は stdout を用いる設計（cron/スケジューラ環境で stdout/stderr を一本化しやすくするため）。
- process_priority は権限やプラットフォームによっては効果がない場合があり、その場合は警告ロギングを行ってスキップする。
- portfolio/position_sizing の aggregate cap スケールダウンは lot_size（単元）を考慮した再配分ロジックを持つ。price が欠損（0.0）の場合、該当銘柄はスキップされる点に注意（将来的にフォールバック価格の導入を検討中）。
- risk_adjustment.apply_sector_cap は sector が "unknown" の銘柄には上限を適用しない（既知セクターのみブロック対象）。

Acknowledgements
- 本リリースは初期実装のため、今後以下の点を継続的に改善予定：
  - factor_research の完全実装（SQL/集計ロジックの追加）
  - 単体テストの整備と CI の追加
  - 各エンジン・ブローカークライアントのエラーケースとリトライ戦略の強化
  - ドキュメント（Usage / Deployment / Operational runbooks）の充実

----