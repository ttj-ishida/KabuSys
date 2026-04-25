# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に従っています。  

すべてのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-25

Added
- 実稼働向けの初期モジュール群を追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
      - Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する仕様。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）に記録する（本番 DB と分離）。
      - 起動時にプロセス優先度を "high" に設定し、停止フラグでエンジン停止を行う。
      - 実行中の PID を data/execution.pid に書き込む運用を想定。
  - 設定関連
    - config.py
      - .env 自動読み込み実装（.env / .env.local、OS 環境変数を保護）。
      - .env パースロジックを強化（export 形式、クォート・エスケープ、インラインコメント対応）。
      - Settings クラスを導入し、各種環境変数を型付きプロパティで提供（DB パス、J-Quants / kabu API トークン、紙取引モード等）。
      - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。
      - `paper_sqlite_path` を明示的に分離してペーパートレード用 DB をサポート。
  - 設定ツール / 検証
    - config_setup.py
      - 対話式ウィザードで .env を生成・更新する CLI を追加。
      - デフォルト値、隠蔽入力（シークレット）、選択肢サポート、既存 .env 読み込みを実装。
    - validate_config.py
      - 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在チェック、config/*.yaml の存在とパース検証（PyYAML があれば））。
      - `--strict` オプションで警告も失敗扱いにできる。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - 稼働率、注文成立率（Fill Rate）、送信率（Send Rate）、レイテンシ（avg / max / P95）等を算出して PASS/FAIL 判定を出力。
      - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
  - ポートフォリオ構成（純関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
      - スコアが全て 0 の場合、等金額配分にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中管理（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
      - レジームごとの投下資金乗数（bull/neutral/bear）を定義し、不明なレジームはフォールバック。
    - portfolio/position_sizing.py
      - position size（発注株数）計算を実装（risk_based / equal / score の各方式）。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap のスケールダウン、手数料・スリッページ考慮の cost_buffer をサポート。
  - ユーティリティ
    - utils/logging_setup.py
      - 共通ログ設定ユーティリティを追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
      - ログディレクトリ自動作成のフォールバック、ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
    - utils/process_priority.py
      - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows / POSIX 対応）。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
  - パッケージ情報
    - __init__.py にてバージョンを "0.1.0" として設定。
    - portfolio パッケージで主要関数を __all__ にてエクスポート。

Changed
- 仕様・設計に関する注記をソース内に追加（TODO / 設計意図のコメントを多数追加）。
  - 例: price 欠損時のフォールバック検討、単元株の将来的拡張案、Bear レジーム時の設計上の説明等。

Fixed
- N/A（初回公開のため既知のバグ修正履歴なし）。

Notes / Known limitations
- research/factor_research.py は途中まで実装されており（ファイル末尾が切れている）、完全実装は今後の作業。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。環境により機能制限（例: ログディレクトリ作成失敗時はファイル出力が無効）があります。
- run_monitoring は Monitoring 用 DB 接続に production の sqlite_path を用いる設計のため、テストや開発時は注意が必要。
- PAPER_FILL_MODE の不正値や MONITOR_POLL_INTERVAL の不正値はランタイムで警告・例外となるため、.env の初期設定と validate_config による検証を推奨します。

参考: 主なコマンド
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証:    python -m kabusys.validate_config [--strict]
- 監視起動:      python -m kabusys.run_monitoring
- エンジン起動:  python -m kabusys.run_execution
- ペーパートレード検証レポート生成:
                 python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]