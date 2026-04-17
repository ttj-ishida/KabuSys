CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
全ての公開変更は、日付付きのリリースエントリに記録されています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリースを追加。
- 基本設定・起動ツール
  - 環境変数・設定読み込みモジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env, .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export 形式やクォート、インラインコメント等に対応した堅牢な .env パーサーを実装。
    - Settings クラスに各種設定プロパティ（J-Quants, kabu API, DBパス, PID/kill フラグ, 監視閾値, 環境判定など）を提供。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV の有効値チェックを実装。
  - 環境設定ウィザード CLI を追加 (src/kabusys/config_setup.py)。
    - 対話式で .env を新規作成/更新する機能。シークレット入力のマスク、選択肢、デフォルト表示をサポート。
  - 設定検証 CLI を追加 (src/kabusys/validate_config.py)。
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在・YAML パース等を検査。
    - --strict オプションで警告を FAIL 扱いにできる。live 環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプトを追加 (src/kabusys/run_execution.py)。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用専用 SQLite を使用し本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine の起動ループを実装。
    - 停止フラグ (data/stop_requested.flag) と PID 管理をサポート。
    - RiskManager に初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を適用。
  - SystemMonitor ポーリング起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下など不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に上げる処理を実行。

- Portfolio モジュール（純粋関数群、DB 参照なし）
  - 銘柄選定・重み付け (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates、calc_equal_weights、calc_score_weights を追加。スコアが全て 0 の場合のフォールバックと警告を含む。
  - セクター制約・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap：既存ポジションを基にセクター上限チェックを行い候補を除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier：regime に応じた乗数（bull/neutral/bear）を返す。未知レジームは警告のうえ 1.0 にフォールバック。
  - 位置決め・ポジションサイズ計算 (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes：risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファ、aggregate cap のスケーリングロジックを実装。
    - スケーリング時に残差を lot 単位で再配分するアルゴリズムを実装。

- 研究・分析ユーティリティ
  - ファクター計算モジュールを追加 (src/kabusys/research/factor_research.py)。
    - calc_momentum：1M/3M/6M リターン、MA200 乖離を DuckDB 上の prices_daily テーブルから計算。
    - calc_volatility：ATR、相対 ATR、20日平均出来高、出来高比率等を計算する SQL ベースの実装（長期間スキャン用バッファを考慮）。
    - DuckDB 接続を受け取り SQL と Python 組合せで高速に集計する設計。
  - Paper Trading 検証レポート生成スクリプトを追加 (src/kabusys/tools/paper_verification_report.py)。
    - 稼働率、注文成功率（fill）、送信率（send）、リスク却下数、API レイテンシ（P95等）を算出・判定。閾値（稼働率99%、fill 90%、send 95%、P95 <= 200ms）を定義。
    - --from/--to/--db オプションに対応、PAPER_TRADING_SQLITE_PATH 環境変数経由の DB 指定も可能。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加 (src/kabusys/utils/process_priority.py)。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する API（set_process_priority, set_cpu_affinity）。
    - アクセス拒否や実装未対応の場合は警告ログを出して安全にフォールバック。
  - パッケージ初期化とバージョン定義 (src/kabusys/__init__.py) を追加（__version__ = "0.1.0"）。

Changed
- （初回リリース）各モジュールのログ出力や入力検証を強化。環境変数未設定時の早期エラー検出を優先。

Fixed
- （初回リリース）.env パーサーのクォート・エスケープ・コメント処理を改善し、エッジケースでの誤読を回避。

Notes / Implementation details
- DB
  - DuckDB は分析用（duckdb_path）、SQLite は監視・発注履歴用（sqlite_path / paper_trading_sqlite_path）として分離設計。
- Safety
  - ExecutionEngine は起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に停止フラグがある場合は起動を行わない。
  - 本番環境（KABUSYS_ENV=live）向けに validate_config で注意喚起を行う（LINE 設定未設定や kill flag の自動クリア設定など）。
- Defaults
  - MONITOR_POLL_INTERVAL デフォルト 60 秒。
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等は data/ 以下のデフォルトパスを使用。
  - ログレベルのデフォルトは INFO。

Acknowledgements
- 本リリースは初期実装であり、将来以下を改善予定:
  - 銘柄別の lot_size 管理、価格フォールバックロジック（price 欠損時の扱い）、細かな例外ハンドリングの強化。
  - factor_research の追加ファクター実装やテスト充実。

未リリースの変更 / 既知の制限
- factor_research の一部 SQL が大きいため、周辺ユーティリティやテストをさらに整備する予定。
- GUI や Web UI、より詳細なモニタリングダッシュボードは未実装。

配布
- パッケージバージョンは src/kabusys/__init__.py にて 0.1.0 に設定されています。