Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

注: 日付はソースコードのスナップショットに基づき推測して記載しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース (version 0.1.0)
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db を専用 DB として利用することで本番 DB と完全分離する挙動を実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境 (KABUSYS_ENV) に関係なく本番 sqlite_path を使用する挙動を明示。
    - 停止フラグの検出でループ終了、KeyboardInterrupt 対応あり。
- 設定関連
  - config.py
    - Settings クラスを導入し、環境変数から設定値を一元管理。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env のパース・クォート/エスケープ処理、コメント取り扱い、保護された OS 環境変数の扱いなどを実装。
    - 各種デフォルトとバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット入力や選択肢、既存値の再利用をサポート。
  - validate_config.py
    - 起動前検証用 CLI を追加。必須環境変数や DB パス、config/*.yaml の存在とパースチェック、KABUSYS_ENV=live 時の追加ガードなどを検証。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数や引数で挙動を制御。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows / POSIX の差分吸収）を提供。
    - CPU affinity 設定ユーティリティも実装。権限不足や未サポート環境は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。score が全て 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック (calc_position_sizes) を実装。risk_based / equal / score の割当方法、lot_size（単元）、コストバッファ、aggregate cap のスケーリングと端数処理をサポート。
  - portfolio/__init__.py にて上記関数を外部公開。
- データ分析 / リサーチ
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う骨格を追加（prices_daily / raw_financials を参照する設計）。（ファイルはスナップショットで途中まで実装）
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出し PASS/FAIL 判定を行う。
    - デフォルトの閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を設定。
    - PAPER_TRADING_SQLITE_PATH で DB を切替可能、期間フィルタ（--from/--to）対応。
- DB / ストレージ関連
  - duckdb を分析用 DB として統合（duckdb_path）。
  - 監視用テーブルの初期化処理 init_monitoring_db を呼び出して冪等に監視テーブルを保証。

Changed
- ログ出力の標準出力先を stderr ではなく stdout に統一（cron/スケジューラ対策）。
- .env 読み込みの挙動を強化:
  - export KEY=val 形式やクォート内のバックスラッシュエスケープ、行内コメントの扱いに対応。
  - 自動読み込みはプロジェクトルートが見つからない場合はスキップ。
- run_monitoring のポーリング挙動: 不正な MONITOR_POLL_INTERVAL に対して警告を出してデフォルトにフォールバック。

Fixed
- .env パーサーの脆弱なケースについて改善（クォート/エスケープ/コメントの扱いを明確化）。
- ログハンドラの二重設定を防止するため、setup_logging で既存ハンドラを一度クリアするようにした。

Security
- 秘密情報を扱う設定（J-Quants トークン、kabu API パスワード、LINE トークン）は config_setup の対話でシークレット扱い（マスク表示）に。

Notes / Migration
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず sqlite_path（本番 DB）を使用します。ペーパートレードのログや検証は run_execution（paper_trading モード）や paper_verification_report 用の paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を利用してください。
- 自動 .env 読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ出力先やレベルは LOG_DIR / LOG_LEVEL 環境変数で制御できます。

Acknowledgments
- この CHANGELOG は提供されたソースコードの内容から変更点・特徴を推測して作成しています。実際の変更履歴と差異がある可能性があります。必要であれば実際のコミット履歴やリリースノートに基づく正確な更新履歴を作成します。