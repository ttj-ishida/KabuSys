CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

[0.1.0] - 2026-04-21
-------------------

Added
- 初期リリース: KabuSys 自動売買基盤のコア機能を追加。
- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知でクリーンに終了。監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用。
  - run_execution.py を追加。ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient（BrokerClientFactory）を使用し paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）で本番 DB と分離。プロセス優先度設定、PID ファイル管理、停止フラグでの終了制御、スレッド監視を実装。
- 設定管理
  - config.py: .env ファイルの自動読み込み（プロジェクトルート検出）と強化された .env パーサーを実装。export 形式、引用符付き値（バックスラッシュエスケープ対応）、インラインコメントの扱い、読み込み優先度（OS 環境 > .env.local > .env）をサポート。Settings クラスに各種プロパティ（J-Quants / kabu API / DB パス / paper_trading 設定 / 監視しきい値 / ログレベル等）を定義し、値検証を実施。
  - config_setup.py: 対話式ウィザードを追加。.env の初期作成・更新を支援（シークレット項目のマスク表示、デフォルト値、保存確認）。.env を安全に生成するテンプレート書き出し機能を提供。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース検証（PyYAML が存在しない場合はスキップ）、本番向けガード（LINE 通知設定や Kill Switch の設定）などをチェック。--strict オプションで警告を FAIL 扱いに可能。
- ロギング
  - utils/logging_setup.py: setup_logging を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗やファイルハンドラ作成失敗時はコンソール出力へフォールバック。
- プロセス制御
  - utils/process_priority.py: set_process_priority / set_cpu_affinity を追加。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収する実装（psutil 利用）。権限不足や未対応プラットフォーム時には警告を出してスキップする安全策を実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: シグナル選択（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合に等配分へフォールバックする挙動を持つ。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた乗数（calc_regime_multiplier）を追加。既存保有からセクター露出を算出し上限超過セクターの新規候補を除外するロジックを実装。
  - portfolio/position_sizing.py: 株数計算ロジック（risk_based / equal / score に対応）、単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。再配分のための残差処理（fractional remainder に基づく追加配分）も実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成 CLI を追加。期間指定可能（--from / --to）、PAPER_TRADING_SQLITE_PATH または --db で DB 指定可。指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値判定に基づき PASS/FAIL を出力。P95 計算ユーティリティ、日付フィルタ組立て、テーブル存在に伴うフェイルセーフを実装。
- 研究・ファクター計算（スケルトン）
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算する方針を実装（関数シグネチャ、定数、ドキュメント）。（ファイルは部分実装で続きがあることを示唆）
- パッケージメタ情報
  - __init__.py にてバージョン 0.1.0 を設定。

Changed
- ログ出力を stdout に統一（setup_logging の StreamHandler）。cron / Task Scheduler 等でのリダイレクト運用を考慮。
- run_execution の DB 接続は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用することで本番データと分離。さらに init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Fixed / Improved
- .env のパースを強化：引用符付き文字列内部のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなどに対応し、より堅牢なロードを実現。
- ロギングハンドラの二重追加を防ぐため、既存ハンドラをクリアしてから再設定するよう変更。
- process_priority / cpu_affinity の失敗時に例外を放置せず警告ログでスキップするよう安全化。

Known limitations / Notes
- research/factor_research.py はドキュメント・設計に基づく実装の骨組みを提供するが、ファイルの末尾が途中で切れており一部実装が未完（継続実装が必要）。
- 一部の TODO コメント（例: price フォールバック、銘柄別 lot_size のサポート）が残っており将来的な拡張を想定。
- run_monitoring は「監視用 DB を本番パスで固定する」設計を採っているため、テスト環境で監視 DB を分離したい場合は環境変数やコード側の調整が必要。

Acknowledgements
- 本リリースは内部モジュールの整理と CLI /ユーティリティ群の整備に注力しました。今後は factor 計算の実装完了、単体テスト追加、ドキュメント整備（使用手順・運用ガイド）を予定しています。