CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。
リリース日付は本ファイル作成日時です。

0.1.0 - 2026-04-23
-----------------

Added
- 初回公開: KabuSys パッケージの基礎機能を実装。
  - src/kabusys/__init__.py
    - パッケージのバージョン定義 (__version__ = "0.1.0")。
- 実行スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクトルート/data/stop_requested.flag を監視して安全終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する挙動を明示。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用 DB（デフォルト: data/paper_trading.db）で完全に分離して実行。
    - 停止制御: data/stop_requested.flag と data/execution.pid を使用。
    - エンジンは別スレッドで実行し、フラグ検知で安全停止する実装。
- 設定管理 / ユーティリティ
  - src/kabusys/config.py
    - Settings クラスによる環境変数ラッパーを実装（J-Quants / kabuAPI / DB パス /監視閾値など）。
    - .env 自動読込: プロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local をロード（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
    - .env 行パーサは export プレフィックス、クォート文字、エスケープ、インラインコメント等に対応。
    - 各種プロパティは未設定時に明確な例外や検証を行う（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の有効値検査）。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 各種設定項目の説明、デフォルト、シークレットマスク表示、保存前の確認をサポート。
  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数・パス・config/*.yaml の存在/パースを検査。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML が無い場合は YAML 検証をスキップし警告を出す。
- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時は等配にフォールバックして警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) と市場レジーム乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジーム別乗数マップ (bull/neutral/bear) を定義。
  - src/kabusys/portfolio/position_sizing.py
    - 株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリング、端数処理ロジックを実装。
- ログ / プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ログ設定ユーティリティを実装。stdout へ StreamHandler、日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > デフォルト INFO。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装。Windows と POSIX を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。
- Research / Tools
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity を想定、DuckDB を使った prices_daily/raw_financials 参照）。
    - （注）ファイルの末尾は途中までの実装が含まれます（今後の拡張を想定）。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。P95 レイテンシ、稼働率、注文成功率・送信率、リスク却下数を集計し PASS/FAIL 判定（閾値はソース内定義）。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py で主要関数をエクスポートして容易に利用可能に。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Notes / Important details
- DB の扱い
  - 監視 (run_monitoring) は常に Settings.sqlite_path（デフォルト data/monitoring.db）を参照します。KABUSYS_ENV に依存しません。
  - 実行エンジン (run_execution) は paper_trading 環境時に専用 DB (Settings.paper_sqlite_path、デフォルト data/paper_trading.db) を使用して本番 DB と分離します。
- .env 自動読み込み
  - プロジェクトルートが検出できない場合は自動読み込みをスキップします。
  - OS 環境変数は .env の上書き対象外（保護）。
- ログ
  - ログ出力は stdout を使用（stderr ではない）。ファイル出力は logs ディレクトリに日次ローテーションで出力されますが、ディレクトリ作成に失敗した場合はコンソールのみで動作します。
- エラーハンドリング
  - 監視ループでは check_once() の例外をキャッチしてローカルに記録し、次のポーリングへ継続します（安定運用を重視）。
- 環境変数 / 設定検証
  - Settings や validate_config によるチェックで未設定や不正値（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を早期に検出します。
- 開発者向け
  - config_setup のウィザードは .env を作成/更新し、保存ガイドや validate_config での検証を案内します。

今後の予定（短期）
- research/factor_research の完成（各ファクター計算の SQL 実装の追加）。
- Execution 層の broker / order / reconciler 等の追加実装・テスト強化（run_execution はエンジン起動の枠組みを提供）。
- 単体テストと CI 構築、ドキュメントの充実（API 使用例・運用手順）。

-----