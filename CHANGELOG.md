CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
------------

なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本機能を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db をデフォルト）を使用する分離設計。  
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。  
    - ストップフラグ（data/stop_requested.flag）検知で安全に停止。起動時に execution.pid を利用。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境に依存せず本番 sqlite_path を使用して監視テーブルを管理。停止フラグ検知でループ終了。
- 設定管理 / ユーティリティ
  - config.py: 環境変数/ .env 自動読み込み機構を実装。  
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。  
    - .env/.env.local の読み込み順序および OS 環境変数保護（override / protected）に対応。  
    - 複数の設定プロパティを提供（DB パス、ログ設定、Paper Trading 設定、監視閾値など）。  
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証を行う。
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - シークレット値のマスク表示、選択肢・デフォルト対応、.env 保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。  
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ自動作成、ファイルハンドラ作成失敗時はコンソールのみで継続。  
    - ログレベル/ログディレクトリの解決順を仕様化。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。  
    - Windows（psutil の優先度クラス）と POSIX（nice 値）双方に対応。AccessDenied 等の例外を安全に無視して警告を出す。set_cpu_affinity によりプロセスを最初の N コアに固定可能。
- ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py  
    - select_candidates: スコア降順で上位 N を選択（signal_rank を tiebreaker に使用）。  
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重重みを計算（スコア全0 の場合は等金額にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py  
    - apply_sector_cap: セクター別上限超過時に新規候補を除外するロジック（unknown セクターは除外対象外）。  
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数を返す。未知のレジームはフォールバックで 1.0。
  - portfolio/position_sizing.py  
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。  
      - 単元株丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積り、残差処理により追加配分を行う実装を含む。
  - portfolio/__init__.py で上記関数群を公開。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を SQLite から集計し PASS/FAIL 判定（閾値はソース内定義）を出力。  
    - CLI 引数 --from/--to/--db をサポート。P95 計算や各種 SQL 集計ロジックを実装。
- パッケージ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- research/factor_research.py はモジュールの骨組みと定数、calc_momentum の docstring まで実装されているが、ファイル末尾が途中で切れており実装が未完（Work-in-progress）。今後のリリースでファクター計算の完成を予定。
- config._load_env_file は .env 読み込み時に OS 環境変数を保護する設計になっているため、意図的に既存の環境変数を上書きしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 等の運用上の調整を検討してください。
- position_sizing.calc_position_sizes は現状単元（lot_size）をグローバル共通として扱う設計。将来的に銘柄別単元対応を想定した拡張がコメントで示唆されています。

参考
- 実行スクリプトは stop flag / pid file / logging / process priority の取り扱いにより運用監視を重視した設計になっています。ペーパートレードと本番 DB の分離や監視用テーブル初期化（init_monitoring_db）の冪等処理など、安全性に配慮した実装方針が反映されています。