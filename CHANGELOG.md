# CHANGELOG

すべての重要な変更点を Keep a Changelog 形式で記載します。  
このファイルはリポジトリ内の現在のコードベースから推測して作成した初回リリース相当の変更履歴です。

All notable changes
-------------------

0.1.0 - 2026-04-18
-----------------

Added
- 初期リリース: KabuSys 自動売買基盤の基本ユーティリティ・実行/監視モジュールを追加。
- 環境設定／読み込み
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env パーサーは export 形式・クォート文字列・エスケープ・インラインコメントに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを追加し、環境変数を型付きプロパティ経由で取得（各種デフォルト値とバリデーションを含む）。
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を必須として検証。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの値チェックを実装。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）、DuckDB/SQLite パス、PID/kill フラグパスなどの設定プロパティを提供。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用 DB を利用し、MockBroker を想定して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル管理・スレッドベースの実行ループをサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知で安全にループ終了、例外発生時はログを残して次ポーリングへ継続。
- 監視 DB 初期化
  - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等性）。
- ロギング
  - setup_logging: 統一的なログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリーンアップ、ファイル出力失敗時のフォールバック対応。
- プロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity を提供。
    - Windows と POSIX の差分吸収（psutil 使用）。許可エラー等は警告でフォールバック。
- 設定検証 CLI
  - validate_config: .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 任意依存）、本番向けガードチェックを実装。
    - --strict オプションで警告を FAIL として扱う。
- 環境設定ウィザード
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。
    - 各設定項目の説明、既存値の再利用、シークレットマスク表示、保存確認を備える。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。Paper Trading の SQLite DB から各種指標（稼働率・注文成功率・送信率・レイテンシ等）を集計し PASS/FAIL レポートを生成。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間指定可能 (--from / --to)。
    - P95 計算、N/A 表示などを実装。閾値はファイル内定数で管理。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア加重配分（calc_equal_weights / calc_score_weights）。
    - スコア全 0 の場合のフォールバック警告を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
    - セクター未登録銘柄は "unknown" 扱いで上限適用除外。
    - レジームごとの乗数マップ（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-position / aggregate cap、コストバッファによる保守的見積り、スケーリングと端数配分ロジックを実装。
    - 価格欠損時のスキップ、十分な安全弁を確保。
- research.factor_research（ファクター計算）
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等のファクターを計算する設計（calc_momentum 等の骨組みを追加）。（ファイルの末端が途中までの実装を含む）

Changed
- なし（初回リリース想定のため）。

Fixed
- なし（初回リリース想定のため）。

Notes / 注意事項
- Paper Trading と Live は DB を分離して扱う設計:
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用。これにより本番データと完全分離可能。
  - 監視(run_monitoring)は環境にかかわらず Settings.sqlite_path（監視用 DB）を利用する点に注意。
- 環境変数の必須項目が不足している場合、Settings プロパティの呼び出しで ValueError を送出します。起動前に validate_config によるチェックを推奨します。
- process_priority / cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出して継続します。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで動作します。
- research.factor_research は DuckDB を前提とした実装で、prices_daily / raw_financials のスキーマ依存があります。実運用前にデータ準備と検証が必要です。

開発者向けヒント
- .env の生成には python -m kabusys.config_setup を使用し、生成後に python -m kabusys.validate_config で検証してください。
- モニタリングのポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を設定してください（正の整数。無効値は 60 秒にフォールバック）。
- Paper Trading レポートは python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD で実行できます。

---

この CHANGELOG はコードベースの内容から推測して作成しています。追加の変更点や正確なリリース日を反映したい場合は差分情報（コミットログ / Git タグ等）を提供してください。