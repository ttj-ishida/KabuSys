CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。  
日付はリポジトリ内コードから推測して付与しています。

[Unreleased]: https://example.org/unreleased
[0.1.0]: https://example.org/v0.1.0

フォーマット
------------
- 主要な変更カテゴリ: Added / Changed / Fixed / Deprecated / Removed / Security
- 各項目はコードベース（src/kabusys 以下）から推測した機能・振る舞いに基づき記載しています。

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション初期実装を追加
  - パッケージバージョン: __version__ = 0.1.0
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag による外部停止フラグ検出、停止時は engine.stop() を呼んで安全に終了。
    - 実行中の PID を data/execution.pid に管理（pid_file を ExecutionEngine に渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用するよう明示。
    - data/stop_requested.flag による停止、チェック中の例外はログ出力してループ継続。
- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装（無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env のパースは export 形式、クォート、エスケープ、インラインコメント（クォートなしの場合は直前スペースで判定）に対応。
    - Settings クラスを提供し、環境変数をプロパティ経由で取得（各種パス、閾値、環境判定、Paper Trading 設定等）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の値検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援する CLI を追加。
    - シークレット項目は入力時にマスク表示、最終確認後に .env を書き込み（.env を Git にコミットしないよう注意書き）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の整合性チェック、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML 利用。未インストール時は警告）、本番環境向けの追加ガードなどを実装。
    - --strict オプションにより警告も失敗として扱える。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout へ StreamHandler 出力、さらに日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
    - ログレベル解決順やログディレクトリ解決順を仕様化。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ。
    - set_process_priority("high"|"normal"|"low") を提供（起動スクリプトで "high" を指定して使用）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留めする機能（存在しない OS や権限不足時には警告してスキップ）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0.0 の場合に等金額へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が上限を超えている場合に当該セクターの新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" のマッピング、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - position sizing を実装（risk_based / equal / score の配分方式、単元株丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮）。
    - スケールダウン時は残差（fractional remainder）に基づき lot 単位で追加配分するロジックを実装。
- リサーチ / 分析
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、流動性、バリュー系の計算方針記載）。
    - DuckDB を用いた prices_daily / raw_financials 参照で計算する方針を実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite データベース（PAPER_TRADING_SQLITE_PATH）を解析し、稼働率（uptime）、注文成功率、送信率、レイテンシ（avg/max/P95）等のレポートを生成する CLI を追加。
    - デフォルト閾値を定義し（稼働率 >= 99%、注文成功率 >= 90% 等）、PASS/FAIL 判定を出力。
- DB / 分析基盤
  - run_* スクリプト・execution 側で duckdb を分析用 DB（settings.duckdb_path）として利用。
  - monitoring 側・execution 側ともに init_monitoring_db(sqlite_conn) を呼び、監視用テーブルが存在することを冪等に保証。

Changed
- ログ出力は標準エラーではなく標準出力へ出すよう方針を統一（utils/logging_setup.py）。
- .env のパース挙動を厳密化（クォート内のエスケープ処理、コメント解釈のルール等）して、より実運用に耐える実装に。

Fixed
- run_monitoring.py と run_execution.py での停止フラグ検出ロジックを明示：
  - 起動前・ループ中に data/stop_requested.flag を確認し、安全に起動中断・停止できる実装に修正。

Security
- config_setup.py で生成される .env に関する注意書きを強調（.env を絶対に Git にコミットしないことを明記）。
- Settings._require() により必須環境変数が未設定の場合に早期に ValueError を発生させ、秘密情報が欠落している状態での誤動作を防止。

Known issues / Work in progress
- research/factor_research.py はモジュールの骨組みと多くの定数／説明を含むが、一部関数実装が未完（ファイル末尾で切れている/未完了の箇所あり）。ファクター計算の完全実装は今後の作業対象。
- 一部の Execution / Monitoring 内部実装（ExecutionEngine、BrokerClient の具体実装、monitoring.system_monitor の詳細）は本差分に含まれていない（別モジュールに依存）。実動作はそれらの実装に依存する。
- position_sizing の price が欠損（0.0）の場合、現在は logger.debug でスキップする挙動。将来的に前日終値などのフォールバック価格を導入することを TODO として記載。
- ログファイル作成やプロセス優先度設定・CPU affinity の適用は権限や環境依存のため失敗する可能性がある（例: 権限不足、未対応 OS）。現状は失敗時に警告を出してスキップする方針。

アップグレード手順（初回導入メモ）
- 必要環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を .env に設定（config_setup.py を利用して初期作成可能）。
- 必要な外部ライブラリ（psutil, duckdb, PyYAML が一部の機能で必要）をインストール。
- logs ディレクトリ作成権限を確認。ディレクトリ作成に失敗した場合はコンソールログのみで起動する。
- Paper Trading と本番 DB は分離するため、paper_trading 実行時は KABUSYS_ENV=paper_trading を設定して専用 DB を使用すること。

脚注
- 本 CHANGELOG は提供されたソースコード内容からの推測に基づいて作成しています。実装の追加モジュールや外部依存の差分により挙動が異なる場合があります。必要であれば、実際のコミット履歴やリリースタグ情報を元により正確な CHANGELOG を作成できます。