CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。  
フォーマットやカテゴリは可能な限りソースコードから推測して作成しています。

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-04-19
-----------------

Added
- 基本構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは専用のペーパートレーディング用 SQLite を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用できる設計。
    - 起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウンする仕組みを実装。
    - 実行時の PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を参照する設計（監視データを本番 DB に集約）。
    - 停止フラグ検出によるループ終了、KeyboardInterrupt ハンドリング、例外時のログ出力を備える。
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせて設定。
    - LOG_DIR / app_name / LOG_LEVEL の優先解決、ログディレクトリ自動作成（失敗時はファイル出力をスキップ）に対応。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) を透過的に扱い、"high" / "normal" / "low" を指定可能。失敗時は警告を出してスキップ。
    - set_cpu_affinity で最初の N コアに固定する機能を追加（未指定時は何もしない）。
  - config.py: 環境変数・設定管理クラスを追加。
    - .env 自動読み込み（.env, .env.local）機能（プロジェクトルート自動検出、OS 環境変数優先、保護機構あり）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視閾値 / 環境種別等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
    - 対話形式で主要設定を入力・既存値の再利用が可能。生成される .env は書式化されて出力。
    - .env を誤ってコミットしないようファイルヘッダに注意書き。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml の存在と YAML パース検証（PyYAML があれば実施）を提供。
    - --strict オプションで警告も失敗扱いにできる。
  - portfolio モジュール: ポートフォリオ構築用の純関数群を追加。
    - portfolio_builder: select_candidates（上位 N の選定）、calc_equal_weights、calc_score_weights（スコアが 0 の場合は等配分にフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中排除、"unknown" セクターは除外しない設計）、calc_regime_multiplier（bull/neutral/bear マップ、未知レジームは警告のうえ 1.0 フォールバック）。
    - position_sizing: calc_position_sizes（allocation_method="risk_based"／"equal"／"score" に対応）。
      - lot_size 単位で丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
      - aggregate cap を考慮したスケーリング（cost_buffer を利用した保守的コスト見積り、残差を用いた追加配分ロジック）。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ(P95) などを集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定を出力。
    - コマンドラインオプションで期間指定（--from, --to）および DB パス指定（--db）に対応。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（設計と一部実装）。
    - Momentum / Value / Volatility / Liquidity 系のファクター計算方針と定数定義を含む（prices_daily / raw_financials テーブル参照を想定）。
  - パッケージ基礎
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- なし（初回リリース想定のため新規追加が中心）

Fixed
- なし（初回リリース想定）

Security
- 環境変数扱いの注意や .env の取り扱い（自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD、.env をコミットしない注記）を用意して機密情報の誤置換リスクを軽減。

Notes / 実装上の注意点（コードから推測）
- run_monitoring は監視 DB に本番 sqlite_path を常に使用するため、monitoring データは環境に依存せず本番 DB に集約される点に注意。
- run_execution は paper_trading 環境時に本番 DB と分離した専用 SQLite を使用する（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされ、テスト環境などでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に例外を投げず警告を出して継続する設計。
- position_sizing のスケーリングや price の欠損時の挙動（price が 0 のときはスキップ、将来的なフォールバック未実装）など、運用時に注意が必要。
- config_setup による .env ファイル生成はデフォルト値を埋めるが、J-Quants / kabu API パスワード等は必須のためユーザが正しい値を設定する必要がある。
- tools/paper_verification_report はテーブルが存在しない場合に sqlite3.OperationalError をハンドリングして不足データとして扱うようになっている。

参考
- コードベースは duckdb を分析用 DB、sqlite をトランザクション/監視用 DB として使い分ける設計になっています。ログや監視、実行エンジン、ポートフォリオ構築、リサーチ、設定管理の主要機能が含まれます。

もし特定のモジュールや変更点についてより詳しい説明（例: 関数仕様・引数・戻り値のドキュメント化、既知の制約やテストケース提案など）が必要であれば教えてください。