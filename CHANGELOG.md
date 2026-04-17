CHANGELOG
=========

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

フォーマットのポリシー:
- すべての変更はバージョンごとに記載します。
- 可能な限り簡潔に、かつ利用者に影響が分かるように記述します。

Unreleased
----------

- （現在未リリースの変更はここに記載します）

0.1.0 - 2026-04-17
------------------

Added
- 初回公開リリース。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - デフォルトの RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を定義し、broker.get_available_cash() を初期ポートフォリオ値として使用。
    - thread ベースで engine.run_session をデーモン起動し、 data/stop_requested.flag の検知で安全に停止。
    - 起動前に停止フラグが立っている場合は起動をスキップ。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。プロセス優先度を "high" に設定してから起動。
    - 監視用 DB は KABUSYS_ENV に関係なく本番用 sqlite_path を使用（monitoring テーブル初期化を含む）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - data/stop_requested.flag を検知してループ終了。
- 設定管理 / CLI を追加:
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）を実装。  
      読み込み順は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント取り扱いの改善）。
    - Settings クラスを実装し、各種環境変数を型付きで提供（パスは Path に変換）。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE の検証を実装。
  - config_setup.py
    - 対話式の .env 設定ウィザードを提供。既存 .env の読み込み、シークレット入力のマスク、選択肢・デフォルトの提示、保存確認をサポート。
    - .env 書き出しテンプレートを用意（重要な注意書き: .env を Git にコミットしないよう明記）。
  - validate_config.py
    - 起動前の設定検証ツールを追加。必須 / 任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLite のパス確認、config/*.yaml の存在と YAML パース（PyYAML がインストールされていればパースチェック）を行う。
    - --strict モードで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリを追加 (kabusys.portfolio):
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を計算。スコアが全て 0 の場合は警告と等金額フォールバック。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮したセクター集中制限ロジック。unknown セクターは上限の対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームはログ警告の上 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。  
      - risk_based: 損切り率・許容リスクから個別目標株数を算出。  
      - equal/score: 重みから配分額を計算。  
      - lot_size（例: 100）で丸め、単銘柄上限（max_position_pct）および aggregate cap（available_cash）を考慮。cost_buffer により保守的なコスト推定を行い、スケーリング＆残差処理（fractional の大きい順に lot 単位で追加配分）を実装。
- リサーチ / ファクター計算:
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（ATR の NULL 伝播を厳密に扱う実装）。
    - 大きなウィンドウ・スキャン期間（例: MA200 用のバッファ）やデータ不足時の None 処理を考慮。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成ツールを追加。SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。CLI で期間指定（--from/--to）と DB パス指定（--db）を可能に。
    - デフォルトの合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義。
- ユーティリティ:
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority(level) を実装（Windows の優先度クラス、POSIX の nice 値に対応）。権限不足や未対応 OS では警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count) を追加し、最初の N コアにプロセスをピン留めする機能を実装。引数チェックと例外処理を追加。

Changed
- パッケージのトップレベルに __version__ = "0.1.0" を追加。

Fixed
- .env パーサーのコメント・クォート処理を改善し、エスケープシーケンスや export プレフィックスに対応。これにより .env の柔軟な記述が可能に。
- monitoring / execution 起動時の DB 初期化（init_monitoring_db）の呼び出しを導入して監視用テーブルの存在を保証（冪等性あり）。

Notes / Considerations
- config.Settings は起動時に環境変数の妥当性チェックを行うため、必須環境変数未設定時は ValueError を発生させます。validate_config.py を事前実行して設定を確認することを推奨します。
- run_monitoring は監視 DB に対して「本番 sqlite_path を常に使用する」挙動であり、KABUSYS_ENV に依存しません。Paper Trading と監視 DB を完全分離したい場合は設定（SQLITE_PATH 等）に注意してください。
- position_sizing の lot_size は現在グローバル単位（全銘柄共通）で扱っており、将来的な拡張で銘柄別 lot_map の導入が想定されています（コード内に TODO コメントあり）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML）の存在に依存します。環境によってはインストールが必要です。

Acknowledgements
- 本リリースは初期実装の集約であり、今後のマイナーバージョンで追加の検証、テスト、ドキュメント強化、エラーハンドリング改善を行う予定です。