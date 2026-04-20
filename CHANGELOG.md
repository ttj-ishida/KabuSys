CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- ドキュメント・メタ情報のみ（リリース前）。

[0.1.0] - 2026-04-20
-------------------

初回公開リリース。日本株自動売買システム "KabuSys" の基本コンポーネント群を含みます。

Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定・ロード
  - .env ファイルと環境変数を扱う設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml 基準で探索して自動的に .env/.env.local を読み込む機能。
    - export KEY=val 形式、クォートされた値のエスケープ処理、インラインコメント処理などをサポートする堅牢なパーサを実装。
    - OS 環境変数を保護する protected オプションを用いた上書き制御。
    - 設定取得用 Settings クラスを提供（J-Quants / kabu API / DB パス / paper fill モード /監視しきい値 / 環境判定など）。
    - PAPER_FILL_MODE の妥当性チェック（instant|partial|never|reject）。

- 対話式設定ウィザード
  - .env の初期作成・更新を支援する CLI を追加（src/kabusys/config_setup.py）。
    - J-Quants、kabu、DB パス、ログレベル、Kill Switch 振る舞い等を対話的に設定・保存可能。
    - 秘匿項目はマスク表示。既存 .env の読み込み・利用に対応。
    - .env を生成する際は Git へのコミット禁止を強調するヘッダを付与。

- 設定検証ツール
  - 起動前に環境変数や config/*.yaml の存在・妥当性を検査する CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）等。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - data/execution.pid に PID を記録、data/stop_requested.flag による外部停止検知を実装。
    - スレッドでエンジンを実行し、フラグ検知時に安全に停止要求を送るループ。

  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を設定可能（デフォルト 60 秒、0 以下はデフォルトへフォールバックして警告）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - process priority を最初に high に設定する処理を実行。

- ロギング・ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、既存ハンドラの安全な flush/close と再設定、ログディレクトリ作成失敗時はファイル出力をスキップする堅牢な実装。
    - ファイルハンドラ作成失敗時もコンソール出力は継続する。

- プロセス優先度・CPU 制御ユーティリティ
  - psutil を利用したプロセス優先度設定と CPU affinity 設定を提供（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS に対応（Windows の優先度定数は getattr で安全に取得）。
    - 権限不足や未実装 API に対して警告ログを出し、安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークロジック
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコア合計が 0 の場合は等配分にフォールバック）

  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下倍率（bull:1.0 / neutral:0.7 / bear:0.3）と未知レジームでのフォールバック。

  - 株数決定・リスク制限・単元株丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method="risk_based" / "equal" / "score" に対応。
    - risk_based: risk_pct と stop_loss_pct に基づく株数算出。
    - equal/score: 重みと max_utilization に基づく算出。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮。
    - aggregate cap 超過時はスケールダウンし、端数は lot_size 単位で残差の大きい順に追加配分するロジックを実装。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを出力。
    - デフォルト基準値（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）を設定し PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。

- 研究用ファクター計算（骨格）
  - src/kabusys/research/factor_research.py を追加（momentum, volatility, value, liquidity の設計・定数化と calc_momentum の実装骨格を含む）。
    - DuckDB 経由で prices_daily / raw_financials を参照し、(date, code) 単位でファクターを返す設計方針。

Changed
- NA（初版のため過去リリースとの差分なし）。

Fixed
- NA（初版）。

Security
- .env は絶対に Git にコミットしない旨を config_setup の生成ファイルヘッダに明記。

Notes / Migration
- paper_trading モードでは監視 DB と実行 DB を分離しているため、ペーパートレードデータは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に格納され、本番 DB（SQLITE_PATH）とは混在しません。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすることで無効化できます。CI やテスト環境で利用する際に注意してください。
- ログディレクトリ作成に失敗した場合でも標準出力にはログが出力されます。ファイル出力が必要な場合は LOG_DIR の書き込み権限を確認してください。
- process priority / CPU affinity の設定はプラットフォームや権限に依存します。設定失敗時は警告が出力され、処理は継続します。

Contributing
- バグ修正や機能追加の提案は issue を立て、Pull Request を送ってください。テストとドキュメント付与を推奨します。

License
- プロジェクトルートのライセンスファイルに従ってください（リポジトリに未付属の場合は個別に確認してください）。