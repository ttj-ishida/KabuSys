# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

最新リリース
------------

### [0.1.0] - 2026-04-24

Added
- 初回リリース。KabuSys 自動売買基盤のコア機能群を追加。
- 実行スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV による動作分岐を実装（paper_trading 時は専用 SQLite に記録し MockBrokerClient を使用）。
    - 実行プロセスの優先度を設定（高優先度）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - PID ファイル管理（data/execution.pid）。
  - run_monitoring.py を追加。SystemMonitor ポーリングループの起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境に関わらず本番用の sqlite_path を使用する設計。
    - 停止フラグファイルを検知してループを終了。
- 設定関連
  - config.py: 環境変数 / .env 読み込みと Settings クラスを追加。
    - プロジェクトルート探索（.git / pyproject.toml 基準）により .env 自動ロードを行う（無効化フラグあり）。
    - .env パースはコメント、クォート、export 形式、エスケープを考慮した堅牢な実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 / ログ等）。
    - Paper Trading 向け設定: PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、is_paper/is_live/is_dev 判定。
    - 監視・Kill Switch 関連設定（kill_flag_path, kill_flag_clear_on_start など）。
  - config_setup.py: 対話式ウィザードを追加して .env の初期作成・更新を支援。
    - 必須項目のマスク表示、既存値の再利用、選択肢の検証、.env 出力テンプレートを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性チェック、DB パスや config/*.yaml の存在・パース確認、live 環境向けの追加警告など。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、タイブレークは signal_rank）と候補選定。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター上限を適用する apply_sector_cap（既存保有・売却予定銘柄を考慮）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based, equal, score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、コストバッファ処理、端数処理の再配分ロジックなど。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの一元設定ユーティリティを追加。
    - stdout への StreamHandler と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ作成失敗時は file ハンドラをスキップしてフォールバック。
    - LOG_LEVEL / LOG_DIR の解決順序を実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定および CPU affinity 設定を提供。
    - psutil を用い、権限不足時は警告出力して安全にスキップ。
- 監視・計測関連
  - monitoring 側 DB 初期化（init_monitoring_db を別モジュールで提供）を呼び出す形で実行スクリプトから保証。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
- research/factor_research.py（ファクター計算モジュール）
  - DuckDB を使ったファクター計算基盤を追加（Momentum / Value / Volatility / Liquidity の仕様記載、calc_momentum の実装開始）。

Changed
- パッケージバージョンを設定: kabusys.__version__ = "0.1.0"。
- ロギング挙動: コンソール出力は stdout を使用する方針に統一（cron/タスク起動時のリダイレクト対応）。
- 実行環境分離: paper_trading 実行時は本番 SQLite と分離して PAPER_TRADING_SQLITE_PATH を使用するよう明確化。

Fixed
- .env 読み込みの堅牢化: export 構文・クォート内のエスケープ・インラインコメント処理などを改善。既存 OS 環境変数の保護（protected 引数）に対応。

Security
- config_setup.py 生成の .env に対して明示的に「.env は絶対に Git にコミットしないこと」を注記。
- API トークン / パスワードは対話でマスク入力を想定（生成ファイルでは値を空にして手動設定を推奨）。

Notes / Implementation details
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で制御可能。0 以下や非整数はデフォルト（60 秒）にフォールバックして警告。
- run_monitoring は監視 DB として Settings.sqlite_path を使用（監視は本番 DB を参照する設計）。
- run_execution はエンジンを別スレッドで動かし、停止フラグ検知時に ExecutionEngine.stop() を呼んで安全終了を試みる。
- position_sizing の aggregate scale-down は lot_size 単位で再配分を行い、残余キャッシュで fractional 残差が大きい順にロットを追加する安定したアルゴリズムを実装。
- risk_adjustment の apply_sector_cap はセクター不明（"unknown"）の銘柄を上限適用対象外にする仕様。

未解決 / TODO（今後の改善候補）
- position_sizing: 銘柄毎の lot_size を stocks マスタから取得する対応（現状は全銘柄固定）。
- risk_adjustment: price が欠損した場合のフォールバック（前日終値や取得原価の利用）。
- research/factor_research: calc_momentum の実装が途中（ファイル末尾が切れているため追加実装が必要）。
- config_setup の入力でシークレット入力を端末で隠す等の改善（getpass 利用など）。
- DuckDB / SQLite のコネクション周りのリソース管理や接続エラーハンドリングの強化。

Acknowledgements
- 本リリースは初期実装のため多くのモジュールが純粋関数・CLI ベースで構築されています。今後ドキュメント・ユニットテスト・例外処理の拡充を予定しています。

--- 

今後のリリースでは、上記 TODO の対応、テストカバレッジの向上、ドキュメント整備（API リファレンス・設計ドキュメントの同梱）を優先して行う予定です。