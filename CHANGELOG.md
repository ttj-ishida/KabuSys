CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリースノートはコードベース（src/ 以下）の現在の実装内容から推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys パッケージ v0.1.0 を追加。
- 実行用スクリプト:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時には paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境に関わらず本番 sqlite_path を使用する実装（監視 DB 初期化処理を呼び出す）。
- 設定・環境管理:
  - config.py — Settings クラスを追加。環境変数と .env 自動読み込み機能を提供。  
    - .env/.env.local の自動ロード（OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
    - .env 行パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメントへの対応）。  
    - 各種設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE, PID/KILL フラグのパス、閾値等）を提供。
  - config_setup.py — 対話式 .env 作成ウィザードを追加。  
    - シークレットのマスク表示、既存値読み込み、保存テンプレートの生成、Git に .env をコミットしない旨の注記を出力。
  - validate_config.py — 設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在チェックを実装。--strict オプションで警告を FAIL 扱いにできる。
- ユーティリティ:
  - utils/logging_setup.py — 統一ログ設定ユーティリティを追加。  
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、既存ハンドラの二重設定を防止。LOG_DIR/LOG_LEVEL による上書き、ログディレクトリ作成失敗時のフォールバックをサポート。
  - utils/process_priority.py — クロスプラットフォームなプロセス優先度設定ユーティリティを追加。  
    - Windows と POSIX（Linux/macOS 等）で適切に nice / priority を設定し、未対応 OS や権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築 / リスク調整 / 発注数算出:
  - portfolio/portfolio_builder.py — 銘柄選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py — セクター集中上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py — position sizing の本格実装（calc_position_sizes）。  
    - allocation_method に "risk_based" / "equal" / "score" をサポート。  
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いた保守的コスト見積り、残余を考慮した lot 単位での再配分ロジックを実装。
- モニタリング / 検証ツール:
  - tools/paper_verification_report.py — Paper Trading 用検証レポート生成ツールを追加。  
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、閾値に基づき PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH または --db で DB 指定可能。
- research/factor_research.py — ファクター計算モジュールの骨子を追加（DuckDB 経由で momentum/value/volatility/liquidity 等を計算する設計）。calc_momentum の実装用の定数や設計方針が含まれる（DuckDB 接続を受ける想定）。

Changed
- パッケージメタ情報:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- ログ出力のデフォルト挙動を統一:
  - setup_logging により全起動スクリプトから同じフォーマット・ローテーション方式を利用する設計に変更。
- 監視/実行プロセス起動時の優先度設定:
  - run_monitoring/run_execution の起動シーケンスで最初に set_process_priority("high") を呼ぶようにして、起動直後に優先度を上げる仕様。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメントの扱い（クォート有無での差別化）を実装し、既存の簡易実装での誤解析を回避。
- process_priority, logging_setup の例外耐性強化:
  - 権限不足や未サポート環境（psutil が提供しない定数やハンドラ作成失敗）に対して警告ログを出し、処理全体を停止させないよう修正。

Security
- config_setup.py の .env 出力で「.env は絶対に Git にコミットしないこと」と明記。
- 対話式ウィザードではシークレット項目をマスクして表示。

Notes
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合にデフォルト（60 秒）へフォールバックして警告を出す実装になっています。
- validate_config は PyYAML が未インストールの場合、config/*.yaml の中身検証をスキップして警告を出す設計です。
- portfolio モジュールは純粋関数群として実装され、DB 参照なしでメモリ内計算を行うよう設計されています。
- research/factor_research.py は設計方針と定数・関数の骨子を含み、DuckDB を使ったファクター計算の実装が進められています（ファイル末尾が途中になっているため、calc_momentum 等の完全実装は今後の作業を想定）。

Acknowledgements
- 本 CHANGELOG は現行ソースコードからの推測に基づき作成しています。実際のリリースノートと差異がある場合があります。必要であれば、特定のコミット単位や差分に基づく詳細な CHANGELOG を改めて生成します。