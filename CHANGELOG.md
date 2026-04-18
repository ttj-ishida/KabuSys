CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。

[0.1.0] - 2026-04-18
-------------------

Added
- 初回公開リリース。KabuSys の基盤となる複数のモジュールと CLI を追加。
- 起動スクリプト / デーモン類
  - run_monitoring.py: システム監視（SystemMonitor）用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
    - 監視用 DB は環境にかかわらず本番の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（data/paper_trading.db）と Mock ブローカークライアントを使用して本番 DB と分離。
    - エンジンはバックグラウンドスレッドで実行され、停止フラグで優雅に終了する仕組み。
    - PID ファイル (data/execution.pid) の扱いをサポート。
- 設定管理
  - config.py: Settings クラスを導入し、環境変数の一括取得／検証を提供。
    - プロジェクトルート検出ロジック（.git / pyproject.toml 基準）により .env 自動ロードを安全に実行。
    - .env/.env.local のロード順と既存 OS 環境変数の保護機構を実装。
    - 各種パス・閾値・フラグのプロパティ化（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値 等）。
    - PAPER_FILL_MODE のバリデーション実装。
- 設定補助 CLI
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加。
    - 必須項目のマスク表示、デフォルトや選択肢の提示、保存確認までをサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）をチェック。
    - --strict モードで警告を失敗扱いにできる。
- ロギング／プロセスユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（既定: logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定機能を追加（psutil 利用）。
    - Windows / POSIX（Linux, macOS 等）を吸収し、安全にフォールバック。
    - CPU affinity の設定関数も提供（set_cpu_affinity）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア重み）を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。
    - unknown セクターはセクター上限から除外する挙動。
    - レジーム別乗数は (bull:1.0, neutral:0.7, bear:0.3)、未知レジームは警告の上で 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。
    - allocation_method に応じた計算（"risk_based" / "equal" / "score"）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超えた場合のスケールダウン）を考慮。
    - cost_buffer を使った保守的見積り、端数配分アルゴリズム（remainder に基づく lot 単位での追加配分）を実装。
- リサーチ／解析
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（モメンタム等の指標設計を含む）。
    - Momentum, Value, Volatility, Liquidity 等の計算設計方針と一部実装（モメンタム計算関数の導入）。
    - DuckDB 参照によるデータ取得を想定。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定する閾値を定義。
    - DB 存在チェック、日付フィルタ（YYYY-MM-DD 形式）や --db オプションによる DB 指定をサポート。
- その他
  - package バージョンを __version__ = "0.1.0" として設定。

Changed
- ログ周りのデフォルト動作
  - ログのコンソール出力を stderr ではなく stdout に統一（cron 等でのリダイレクトを想定）。
- .env の自動読み込み
  - プロジェクトルート検出および .env/.env.local の読み込み順を明確化し、OS 環境変数の保護を導入。

Fixed / Improved
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、クォート値内のバックスラッシュエスケープ、インラインコメントの扱い（クォート内を無視）などをサポート。より堅牢な .env 読み込みを実現。
- DB 初期化の冪等性確保
  - init_monitoring_db を起動フローで呼び出し、監視テーブルが存在することを保証（複数起動・環境差を吸収）。

Known issues / Notes
- research/factor_research.py の実装は一部（モメンタム計算の続きなど）で作業途中の箇所があり、今後の拡張／テストが必要です。
- 一部の TODO コメント（例: 価格欠損時のフォールバック実装、銘柄別 lot_size 拡張など）が残っています。実運用前にこれらの検討を推奨します。
- 実行環境が本番（KABUSYS_ENV=live）の場合は設定ミスによる重大な誤発注を避けるため validate_config による事前検証を強く推奨します。

Acknowledgements
- 初期設計は自動売買・ペーパートレード運用を想定した分離設計（本番 DB と paper_trading DB の分離、監視プロセスの独立）を反映しています。今後のリリースではテストカバレッジ、監視メトリクスの追加、リスク管理ルールの拡充を予定しています。