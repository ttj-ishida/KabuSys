Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリース日付はコードから推定可能な最新の状態（ドキュメント作成時）を使用しています。

注意: 下記の変更履歴は提示されたソースコードの内容から推測して作成したもので、実際のコミット履歴に基づくものではありません。

Unreleased
----------
- 今後の改善予定（コード内の TODO や警告に基づく想定）
  - position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）実装
  - 銘柄ごとの単元株（lot_size）を銘柄マスタに持たせる拡張
  - research/factor_research の実装完了（モメンタム等の計算処理の続き）
  - system_monitor / monitoring_db 周りの追加検証・安定化

[0.1.0] - 2026-04-19
--------------------
Added
- パッケージ初期版を追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動ロジックを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててエンジンをスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイルをサポート。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値をブローカーの get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor ポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっている点を明記。
    - 停止フラグ検知によるループ終了、例外時のロギング・リカバリを実装。
- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を参照可能にした。
    - .env と .env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースと必須チェック（_require）を実装。paper_trading 用 DB パスや PAPER_FILL_MODE などの専用設定を追加。
- 設定支援 CLI
  - config_setup.py
    - .env の対話式ウィザードを実装（初期作成・更新支援）。機密値はマスク表示、Enter で既存値/デフォルトを再利用可能。
    - .env ファイルの読み書きロジックを実装（git にコミットしない旨のヘッダを自動出力）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パースチェック、KABUSYS_ENV=live 時のガードチェックを行う。
    - --strict モードで警告を失敗として扱う機能を追加。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通に使えるログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数や関数引数での上書きをサポート。ログディレクトリの作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで続行。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）と CPU affinity 固定ユーティリティを追加。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収する実装。失敗時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコア全0時のフォールバックロジックを含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやレジーム未定義時のフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 損切り率・リスク率からの risk_based 計算、lot_size（単元）での丸め、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積もりを実装。
    - 価格欠損時のログとスキップ、スケールダウン時の端数配分アルゴリズムを実装。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポートを生成する CLI を実装。system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）に基づく PASS/FAIL 判定を出力。
    - 日付範囲指定（--from/--to）と DB 指定（--db / 環境変数）をサポート。
- research/factor_research.py
  - ファクター計算の設計と初期実装（モメンタム等の定数・インタフェース）を追加（計算ロジックの続きは未完。コメント・設計に基づく実装途中）。
- パッケージ初期化
  - kabusys/__init__.py を追加し、パッケージ名とエクスポート一覧を定義。

Changed
- 初期公開版のため該当なし（初出の機能群）。

Fixed
- 初期公開版のため該当なし（ただし、robust なフォールバック処理が各所で実装済み）
  - ログディレクトリ作成失敗時にファイル出力を無効化してコンソール出力のみで継続するフォールバックを実装。
  - validate_config では PyYAML 未インストール環境を検出して YAML 検証をスキップするよう対応。

Known issues / Notes
- research/factor_research.calc_momentum の実装がファイル末尾で途中となっており、完全なファクター計算は未実装（設計は存在）。
- position_sizing の注記にある通り、価格が欠損（0.0）だった場合にエクスポージャーが過少見積もられる可能性があるため、将来的に前日終値等でのフォールバックを推奨するコメントあり。
- 単元株（lot_size）を全銘柄共通の定数として扱っている。将来的に銘柄別単元をサポートする拡張を予定。
- monitoring 側（SystemMonitor、monitoring_db）の実装は別モジュールに分かれている（参照されているが本差分に含まれていないため、統合時に注意）。

Acknowledgements
- 本 CHANGELOG は提示されたソースコードのコメント・実装内容から推測して作成しています。実際のコミットログと合わせて調整してください。