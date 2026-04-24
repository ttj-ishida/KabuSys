CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース (0.1.0)
- 基本アプリケーションパッケージとエントリポイントを追加
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（PAPER_TRADING_SQLITE_PATH で上書き可能）。  
    - BrokerClientFactory によるブローカークライアント生成。Engine をバックグラウンドスレッドで起動し、data/stop_requested.flag による停止制御、PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視用 DB の初期化（監視は環境に関係なく本番 sqlite_path を使用する設計）。
- 設定・環境管理
  - config.py: 環境変数/ .env ファイル自動読み込みと Settings クラスを導入。  
    - プロジェクトルート探索（.git または pyproject.toml 基準）による .env 自動読み込み。  
    - .env のパース強化（export プレフィックス対応、クォート内エスケープ対応、コメント処理など）。  
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、env/log_level バリデーション、paper_trading 関連設定）を提供。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加。  
    - J-Quants / kabu API 等の必須項目、DB パス、ログレベル、Kill Switch 設定などを対話式に入力・保存。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パース（PyYAML があれば）を検証。  
    - --strict オプションで警告も失敗扱いにできる。ライブ環境向けのガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START 設定など）を実装。
- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み算出（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数計算、リスク制限、単元丸め、aggregate cap のスケーリング（calc_position_sizes）。
  - portfolio/__init__.py で関連関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリは引数/LOG_DIR/デフォルトで解決。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加。  
    - Windows/Linux/macOS を考慮し、権限不足や未対応 OS は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成する CLI を追加。  
    - 稼働率、注文成功率、送信率、レジテンシ（P95 など）、リスク却下数を集計し PASS/FAIL を判定。しきい値はソース内で定義（例: 稼働率 99%、P95 レイテンシ 200 ms）。
- 研究/ファクター計算の基盤
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum・Value・Volatility 等の計算ロジックを想定）。（実装方針・定数・calc_momentum などの関数群を追加。）
- DB 初期化/監視テーブル
  - monitoring/monitoring_db.py（参照される）：監視テーブル初期化用関数 init_monitoring_db を呼び出す箇所を実装済み（監視・実行の両ランナーで冪等に初期化）。

Changed
- ログ出力先の選択と振る舞いを明確化
  - ログは stdout に出力するようデフォルト化（cron/スケジューラでの扱いを考慮）。
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
- .env 読み込みの優先度と保護機能
  - OS 環境変数を保護するため、.env の上書き制御（override/protected）をサポート。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- run_execution/run_monitoring におけるプロセス優先度設定
  - 起動直後に set_process_priority("high") を呼び出すように変更（重要処理の優先度向上）。

Fixed
- 不正な MONITOR_POLL_INTERVAL 値に対する耐性強化
  - 0 以下や非整数の値の場合に警告を出し、デフォルト 60 秒にフォールバックするよう実装。
- .env パーサのクォート/エスケープ/コメント処理を改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、クォートなし行でのインラインコメント判定などに対応。
- process_priority の失敗時の例外ハンドリング
  - psutil による権限不足や未実装例外をキャッチしてログ警告で安全にスキップ。

Security
- config_setup における .env ファイル出力で「.env を絶対に Git にコミットしないこと」という注意文を挿入。

Notes / Breaking Changes
- 監視（SystemMonitor）は設計上「環境に関係なく本番 sqlite_path を使用する」ため、KABUSYS_ENV 設定と監視 DB パスの扱いに注意が必要です（意図的な設計）。
- run_execution は paper_trading モードで専用 DB を使用することで本番データと完全に分離する設計。

開発者向け補足
- 必須ライブラリ: psutil, duckdb（実行時に必要）。PyYAML が無い場合は config/*.yaml の内容検証はスキップされる。
- 主要 CLI:
  - python -m kabusys.config_setup    (.env 作成ウィザード)
  - python -m kabusys.validate_config (設定検証)
  - python -m kabusys.tools.paper_verification_report (ペーパートレード検証レポート)
  - スクリプト実行: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py

今後の改善候補（コード内の TODO/注釈より）
- position_sizing: 銘柄毎の lot_size 対応（stocks マスタを利用した拡張）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）による精度向上。
- research/factor_research: ファクター計算の完全実装と単体テスト整備。