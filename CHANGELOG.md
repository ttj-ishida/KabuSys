CHANGELOG.md

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
- （現在のコードベースに基づく最初のリリース: 0.1.0）

[0.1.0] - 2026-04-23
Added
- 実稼働ベースラインとなる初期実装を追加。
  - 実行系・監視系の起動スクリプトを追加:
    - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は MockBrokerClient（専用 SQLite: data/paper_trading.db）を使用して本番 DB から分離して実行。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検知による安全停止をサポート。
  - 環境設定/検証関連 CLI を追加:
    - config_setup.py: 対話式ウィザードで .env を作成/更新するユーティリティ。秘匿項目のマスク表示・デフォルト選択肢をサポート。
    - validate_config.py: .env と config/*.yaml の起動前チェック。必須環境変数、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML パース検証を実施。--strict オプションで警告を失敗として扱う機能を追加。
  - Paper Trading 検証ツールを追加:
    - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL 判定を出力。閾値を定義（稼働率 99%、成功率 90% 等）。
  - ポートフォリオ構築ライブラリを追加（純粋関数群、DB 非依存）:
    - portfolio/portfolio_builder.py:
      - select_candidates(): スコア降順＋タイブレークで候補選定。
      - calc_equal_weights(): 等金額配分。
      - calc_score_weights(): スコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap(): セクター集中の上限チェック（既存保有を考慮）、"unknown" セクターは無視。
      - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知レジームはフォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes(): allocation_method ("risk_based"/"equal"/"score") に応じた発注株数計算。単元株丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料/スリッページ見積り）対応。
  - 研究モジュールの骨子を追加:
    - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算方針と一部定数を実装（DuckDB 接続での計算を想定）。（ファイル末尾で実装途中の箇所あり）
  - 設定管理と自動読み込み:
    - config.py: .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml 基準）、export 形式やクォート付き値・エスケープ、インラインコメントの扱いを考慮した堅牢なパーサーを実装。各種設定プロパティ（DB パス、Paper Trading 用パス、しきい値、PID/kill flag パス、env/log level 判定等）を提供。
  - ユーティリティ:
    - utils/logging_setup.py: stdout (StreamHandler) と 日次ローテート（TimedRotatingFileHandler）をルートロガーにセットする共通セットアップ。LOG_DIR 作成失敗時にファイル出力をスキップするフォールバックを実装。ログレベル解決順・ログディレクトリ解決順を明文化。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。権限不足や未対応環境での安全な警告処理を実装。
  - パッケージメタ情報:
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースにつき該当なし）

Fixed
- なし（初回リリースにつき該当なし）

Security
- なし

Notes / 実装上の注記
- run_monitoring は監視用途の DB 接続に settings.sqlite_path（production 想定）を使用する設計。run_execution は KABUSYS_ENV に応じて paper_sqlite_path を使用しペーパートレード時に本番 DB と分離する。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途など）。
- ロギング設定は既存ハンドラを一旦 flush/close してから再設定するため、複数回呼び出しても重複出力を防止する。
- process_priority と CPU affinity の設定は権限やプラットフォーム依存で失敗する可能性があるため、安全に警告を出してフォールバックする実装。
- portfolio/position_sizing の aggregate cap スケーリングは、端数を単元株単位で再配分するアルゴリズムを備え、利用可能現金を超えないように調整する。

将来の改善案（未実装/検討中）
- portfolio/position_sizing の銘柄別 lot_size サポート（現在は全銘柄共通単元）。
- price が欠損した場合のフォールバック（前日終値や取得原価の利用）を検討中（risk_adjustment の TODO）。
- research/factor_research の完全実装（ファイル末尾に実装途中の箇所あり）。
- 監視・実行の単体テスト追加、及び CI での自動検証。

-----  
（注）本 CHANGELOG はリポジトリ内のソースコードを参照して推測・整理した初回リリース記録です。実際のリリース手順や追加のドキュメントは別途参照してください。