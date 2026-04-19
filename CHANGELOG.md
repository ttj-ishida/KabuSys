CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
（この CHANGELOG は提示されたコードベースの内容から推測して作成しています）

[0.1.0] - 2026-04-19
--------------------

Added
- 実行／監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と完全分離。停止フラグファイル（data/stop_requested.flag）や PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を環境にかかわらず使用する仕様。

- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env を初期生成／更新する CLI を追加。デフォルト値、シークレットマスク、選択肢提示等に対応。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告をエラー扱いにできる。

- 設定読み込み・管理の強化
  - config.py: .env の自動読込機能を実装（OS 環境変数優先、.env.local による上書き）。.env パーサーは export KEY=val 形式、クォートやバックスラッシュエスケープ、行内コメントの扱いを考慮した堅牢な実装を提供。Settings クラスで多くの環境変数をプロパティとして提供（パスの Path 変換、各種閾値、paper_trading 用 DB パス等）。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。既存ハンドラの二重設定防止、ログレベル／ログディレクトリの解決ロジックを実装。
  - utils/process_priority.py: Windows / POSIX 差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。アクセス権限不足や未対応 OS の場合は安全にスキップする。CPU affinity を設定する set_cpu_affinity を追加。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py: シグナルから候補選出（スコア降順、同点タイブレーク）と等金額/スコア加重重み計算を実装。スコア全ゼロ時は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap（売却予定銘柄の除外、unknown セクターは除外しない）と市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear を定義、未知レジームは 1.0 でフォールバック）を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数計算を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）の考慮、残差の公平配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite から指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポートを標準出力に出力するスクリプトを追加。各種閾値を定義して PASS/FAIL 判定を行う。P95 計算や日付フィルタ、DB 存在チェック等を実装。

- その他
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

Changed
- ロギングの出力先を stdout に統一（StreamHandler で stdout を使用）。cron やタスクスケジューラ実行時のリダイレクトを考慮。
- run_execution.py / run_monitoring.py など起動スクリプトから共通ユーティリティ（logging_setup, process_priority, monitoring_db 初期化等）を呼び出すように整理。

Fixed
- .env 読み込みの安全性向上: ファイル読み込み失敗時に警告を出して継続する（テスト環境等での堅牢性向上）。
- process_priority のプラットフォーム差分や権限不足で落ちるのを防ぐため例外処理を強化。

Deprecated
- なし（初期リリース想定のため該当なし）。

Removed
- なし。

Security
- 環境設定ウィザードでシークレット入力をマスク表示するなど、秘匿情報の取り扱いに配慮。

Notes / Known issues
- research/factor_research.py の calc_momentum の実装が途中で切れている（ファイル末尾が途中で終端している）。実装途中のファイルが含まれているため、このモジュールは現在完全な動作を保証しない可能性があります。今後、momentum 計算ロジック（DuckDB を用いた時系列集計）の完成が必要です。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバックなど）。将来的な拡張ポイントとして計画されています。

開発者向けメモ
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基に探索するため、配布後でも CWD に依存せず動作します。テストや特殊用途では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- ログディレクトリ作成に失敗してもアプリケーションは継続し、コンソール出力のみで動作します。これにより権限のない環境でも起動が可能です。

Footer
- 以上は提供されたコードベースから推測した変更履歴です。実際のコミット履歴や開発履歴に基づく正式な CHANGELOG 作成時は、各コミットや Pull Request の情報を参照して事実に即した追記・修正を行ってください。