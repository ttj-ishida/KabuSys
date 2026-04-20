Keep a Changelog
=================

すべての重要な変更をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-20
--------------------

Added
- 初回リリース (バージョン 0.1.0)。
- 基本アーキテクチャ・起動スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の検出でループを終了。
    - 監視処理は KABUSYS_ENV に依らず本番用の sqlite_path を使用して監視テーブルを初期化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 SQLite (data/paper_trading.db) に記録し、本番 DB と分離。
    - 起動前に停止フラグをチェックし、実行中に停止フラグ検知でエンジンを停止する仕組みを実装。
    - PID ファイル管理（data/execution.pid）に対応。
- 設定関連:
  - config.py
    - 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出 (.git または pyproject.toml を基準)。
    - .env/.env.local の自動読み込み (OS 環境変数優先)。
    - .env パースの堅牢化（export プレフィックス、クォート文字列、インラインコメント処理、コメント判定ルール等）。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、閾値など）。
    - KABUSYS_ENV や LOG_LEVEL の妥当性チェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成/更新を支援。
    - シークレットのマスク表示、選択肢／デフォルト、確認プロンプトを提供。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML のパース検査（PyYAML がインストールされている場合）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティ:
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) に対応。設定失敗時は警告を出してスキップ。
    - CPU アフィニティ固定用の set_cpu_affinity を提供（利用可能コア数を超える場合のフォールバック等を考慮）。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）:
  - portfolio/portfolio_builder.py
    - 候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の際は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック apply_sector_cap を実装（売却予定銘柄を除外可能、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based, equal, score）に基づく株数計算を実装。
    - 単元株 (lot_size) 丸め、1 銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer による保守的見積りなどを実装。
    - 単元ごとの端数配分アルゴリズム（残余キャッシュで frac が大きい順に lot_size を追加）を搭載。
- データ分析・リサーチ:
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算を行うモジュールの骨子を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - （モジュール中に定数や calc_momentum の実装開始が含まれる。将来的な拡張の基盤を提供）
- 工具（tools）:
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計して PASS/FAIL を判定する。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。
    - P95 計算、期間フィルタのサポート、欠損テーブル時の安全なフォールバックを実装。
- パッケージ初期化:
  - __init__.py にバージョン 0.1.0 とエクスポートモジュールを定義。

Security
- 本リリースでは特にセキュリティ修正はありません。シークレットは .env に保存されるため、.env を絶対にリポジトリに含めないようドキュメント内でも注意喚起しています。

Notes / 注意事項
- run_monitoring は監視用 DB（デフォルト data/monitoring.db）を使用します。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を用いる設計になっています（運用上の注意）。
- PAPER_FILL_MODE などの環境変数は妥当性チェックを行い、不正値は例外を送出します。
- ログは標準で stdout とファイル出力の両方に出ます。ログディレクトリ作成に失敗した場合はファイル出力が無効化され、標準出力のみとなります。
- process_priority や CPU affinity の設定は権限に依存し、失敗時は警告を出してスキップします。
- research モジュールは設計方針と一部計算の骨子を含みますが、完全なファクター群の実装は段階的に拡張する予定です。

今後の予定（非網羅）
- research モジュールの完全実装（各種ファクターの SQL 実装と正規化）。
- ExecutionEngine / BrokerClient の詳細実装とテストカバレッジ強化。
- ドキュメント追記（運用手順、デプロイ例、モニタリングアラート設定など）。
- 単体テスト、例外ケースの更なる堅牢化。

既知の制限
- 一部 TODO コメント（例: price 欠損時のフォールバック戦略、銘柄別 lot_size マスタ）あり。運用上のデータ品質に依存する箇所があるため、注意して運用してください。

---