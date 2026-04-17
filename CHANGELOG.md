CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在のリポジトリ状態は 0.1.0 として初回リリース相当の内容です。以後の変更はここに記載します。）

0.1.0 - 2026-04-17
------------------

Added
- 基本バージョン情報を追加
  - パッケージバージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスを追加して環境変数を型付きプロパティ経由で取得可能に（src/kabusys/config.py）。
  - プロジェクトルート自動検出 (.git または pyproject.toml) に基づく .env 自動読み込み機能を実装。環境変数優先・.env.local による上書きをサポート。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーシングを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。

- 環境設定ウィザード CLI
  - 対話式で .env を作成 / 更新する config_setup ウィザードを実装（src/kabusys/config_setup.py）。
  - 入力項目定義、既存 .env 読み取り、確認プロンプト、および .env ファイル書き出し機能を提供。

- 設定検証 CLI
  - 起動前に環境設定や config/*.yaml の基本チェックを行う validate_config CLI を実装（src/kabusys/validate_config.py）。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース検証（PyYAML があれば実行）、本番環境向けのガードチェック等を実施。
  - --strict オプションで警告を FAIL 扱いにするモードを追加。

- 実行エントリポイント
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。Reconciler、OrderManager、RiskManager 等の組み立ておよび Engine 起動・停止の制御を実装。
    - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）をサポート。

  - Monitoring ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - stop flag による優雅な終了、例外時のログ出力、DuckDB 接続を使用した初期化を実装。

- Paper Trading / 検証ツール
  - Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均／最大／P95）を算出してレポート出力。
    - P95 計算、期間指定（--from, --to）、DB パス指定（--db または環境変数）をサポート。
    - 合格基準（しきい値）を定義（稼働率、成功率、送信率、P95 レイテンシなど）。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出力。
  - セクター集中制限やレジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap は既存保有をセクター別に集計し上限超過セクターの新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' に対してそれぞれ 1.0/0.7/0.3 を返す。未知レジームは 1.0 でフォールバックして警告を出力。
  - 株数決定ロジック（calc_position_sizes）を追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）に基づく丸め、max_position_pct による per-stock キャップ、全体の available_cash に対する aggregate スケーリング、cost_buffer を加味した保守的見積りを実装。
    - スケーリング後の端数配分を残差に基づいて再配分するロジックを実装。

- リサーチ / ファクター計算
  - DuckDB 接続を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）、calc_volatility（ATR、平均売買代金、出来高比）等を実装。
    - データ不足時は None を返す仕様とし、DuckDB 上の SQL で効率的に集計を行う。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差異を吸収し、psutil を用いて優先度（high/normal/low）や CPU affinity の設定を試みる。権限不足や未対応 OS では警告を出してスキップ。

Changed
- ドキュメント的な改善
  - 各モジュールに詳細な docstring と使用例を追加。CLI スクリプトの使用方法を明記。

Fixed
- 環境変数・入力検証の堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0 以下、非整数など）を検出してデフォルト（60 秒）にフォールバックする挙動を追加し、警告ログを出力（src/kabusys/run_monitoring.py）。
  - PAPER_FILL_MODE の検証を実装し、有効値以外は ValueError を投げるように（src/kabusys/config.py）。
  - calc_score_weights: 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックして警告を出すよう修正（src/kabusys/portfolio/portfolio_builder.py）。
  - process_priority/set_cpu_affinity: 未対応プラットフォームや権限不足時に例外を抑制し、警告でフォールバックするよう改善（src/kabusys/utils/process_priority.py）。
  - Execution / Monitoring 起動時の DB 初期化（監視テーブルの作成）を冪等に行う処理を追加（init_monitoring_db 呼び出しを明示）。
  - Paper Trading と本番 DB の分離を確実に（settings.paper_sqlite_path を paper モードで使用）。

Notes / Known limitations
- 一部に TODO コメントあり（価格欠損時のフォールバック価格使用など）。将来的に銘柄別 lot_size の対応や価格フォールバックの導入を想定。
- calc_volatility の実装は DuckDB の SQL 集約を用いているため、prices_daily テーブルのスキーマ依存がある。データ不足時は None を返す。
- process_priority の一部定数は OS / psutil のバージョンに依存するため、プラットフォーム差分が残る可能性がある。

Security
- 特に既知のセキュリティ修正はありません。機密情報（API トークン等）の取り扱いについては .env を Git にコミットしないよう注意を促す注記を config_setup に追加。

ライセンス、貢献方法、その他
- 本 CHANGELOG はコード内のコメント・docstring と実装から推測して作成しています。実際の変更履歴やリリースノートとして使用する場合は、リポジトリの履歴（コミットログ）と合わせて確認してください。