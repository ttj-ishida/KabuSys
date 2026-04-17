CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。

0.1.0 — 2026-04-17
------------------

Added
- 基本アーキテクチャと主要コンポーネントを実装。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用 DB (data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可) に記録する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで制御。
- 設定管理
  - config.py: .env（及び .env.local）自動読み込み機能、環境変数ラッパー Settings クラスを実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py: 対話式 .env 作成ウィザードを実装（保存・上書き可能、シークレット項目マスク表示）。
  - validate_config.py: 起動前チェック CLI を実装。必須環境変数/パス/設定ファイルの存在や KABUSYS_ENV 等を検証。--strict フラグで警告も失敗扱いに。
- 環境変数のパース改善
  - .env パーサは export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、行内コメント処理などに対応。
  - .env の読み込み順は OS 環境 > .env.local（上書き）> .env（未設定キーのみ）。
- DB / 分析基盤
  - DuckDB 統合（Settings.duckdb_path で指定）。各モジュールで DuckDB 接続を受け取る設計。
  - 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）による冪等なテーブル作成を呼び出し。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: シグナル選別 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。未知レジーム時の警告とフォールバック動作を定義。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を実装。risk_based / equal / score の配分方式をサポート、単元株丸め（lot_size）、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料・スリッページ見積り）を反映。価格欠損時のスキップやログ出力あり。
- 実行ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを実装。Windows / POSIX を考慮し、権限不足や未対応環境では警告してスキップする安全策を採用。
- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB の prices_daily 等を参照してモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR 等）を計算する関数を実装。欠損データ時は None を返す設計、スキャン範囲は安全マージン付き。
- ツール
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成 CLI を実装。期間フィルタ (--from / --to)、DB 指定 (--db) に対応。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値に基づく PASS/FAIL 判定を実施。P95 計算、各種テーブル欠如時の安全なデグレードをサポート。
- その他
  - 監視・実行の停止制御をファイルベースで実装（data/stop_requested.flag、data/execution.pid 等）。
  - ロギングは各スクリプトで基本的な設定を行い、重要イベントでの情報/警告/例外ログ出力を追加。

Changed
- 初回リリースにつき変更履歴は該当なし。

Fixed
- 初回リリースにつき修正履歴は該当なし。ただし実用上の堅牢化（例: .env パーサの改良、DB テーブル欠如時のフォールバック処理、プロセス優先度設定失敗時の警告）を実装。

Security
- セキュリティ関連:
  - .env を生成する際に README 等へコミットしない旨の注意コメントを .env に記載。
  - シークレット項目（トークンやパスワード）は config_setup の対話でマスク表示するが、保存時は .env に平文で書き込むため .gitignore 等でコミット防止が必要（注記あり）。

Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。設定されていない場合は起動時にエラーを送出。
- 環境選択:
  - KABUSYS_ENV は development / paper_trading / live のいずれか。paper_trading は本番 DB と分離される（PAPER_TRADING_SQLITE_PATH）。
- 監視ループ:
  - MONITOR_POLL_INTERVAL で間隔を秒単位で制御。無効値や 0 以下はデフォルト 60 秒へフォールバックし、警告を出力。
- 実行権限:
  - プロセス優先度や CPU affinity の設定は権限や OS に依存するため、実行時に失敗しても警告のみで続行する。
- 設定検証:
  - python -m kabusys.validate_config で事前検証を推奨。--strict を付けると警告も失敗扱い。

開発者向けメモ（内部）
- monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用の monitoring.db）を参照する実装に注意。paper_trading 用の監視データ分離が必要な場合は影響範囲の確認を推奨。
- portfolio/position_sizing の aggregate スケールロジックは lot_size 単位での丸めや residual 配分を行うため、目標株数が少ないケースで期待通りの配分にならないことがある。運用時は lot_size と cost_buffer のチューニングを推奨。

Acknowledgements
- 初版リリース。今後の改良点としては E2E テスト、YAML 構成検証の強化（PyYAML の依存明確化）、監視とペーパートレードの DB 分離ポリシー見直し、銘柄別単元対応などを検討。