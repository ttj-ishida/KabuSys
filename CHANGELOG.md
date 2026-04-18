CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版リリースを行う際はリリース日を更新してください。

Unreleased
----------

- 進行中 / 予定
  - research.calc_momentum の実装が途中（ソースに断片あり）。完全実装・追加のファクター計算とテストを予定。
  - 既知の改善候補:
    - position_sizing の lot_size を銘柄別に扱う拡張（stocks マスタ参照）。
    - apply_sector_cap の price フォールバック（前日終値や取得原価）導入。
    - ロギング・モニタリングのさらなるメトリクス拡張とアラート連携。

[0.1.0] - 2026-04-18
--------------------

初回公開リリース（ベース機能を実装）。主な追加点は以下。

Added
- 基本アーキテクチャ / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用。
    - BrokerClientFactory を使用したブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による安全停止処理を実装。
    - 起動時にプロセス優先度を設定（high）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ（data/stop_requested.flag）検出でループを終了。
    - 起動時にプロセス優先度を設定（high）。

- 設定管理・ウィザード・検証
  - config.py: 環境変数ラッパー Settings を実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み制御。
    - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - 多数のプロパティ（DB パス、KABUSYS_ENV, PAPER_FILL_MODE 等）を提供し、妥当性チェックやデフォルトを定義。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。
    - 各設定項目の説明、既存値の再利用、秘密値マスク表示、最終確認と .env 書き込み機能を提供。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML 任意）を検証。
    - --strict を指定すると警告も失敗として扱う。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギングセットアップ関数を追加。
    - stdout StreamHandler と 日次ローテートファイルハンドラ（TimedRotatingFileHandler、30 日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR 環境変数や引数優先で設定可能。ディレクトリ作成失敗時はファイル出力をスキップ。
  - utils/process_priority.py: プロセス優先度および CPU affinity のユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（"high" / "normal" / "low"）。
    - set_cpu_affinity(N) により最初の N コアへピン留め可能。権限不足時には警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づく新規候補の除外ロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出を実装。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング、残差処理ロジックを実装。

- 解析 / ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）と Pass/Fail 判定。
  - research/factor_research.py:
    - ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity 設計）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する方針。calc_momentum の実装が途中（注意）。

- パッケージ情報
  - __init__.py: パッケージバージョンを 0.1.0 に設定。

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

注意事項（ドキュメント的補足）
- 環境変数の自動ロード順:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - 自動ロード時は既存 OS 環境変数を保護（上書き不可）
- run_monitoring は環境（KABUSYS_ENV）にかかわらず監視用 SQLite（settings.sqlite_path）を使用します。run_execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離します。
- .env パーサは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント（クォート無しで # の前が空白の場合にコメント扱い）などに対応します。
- validate_config の YAML 検証は PyYAML がインストールされている環境でのみ有効になります。未インストール時は該当チェックを警告でスキップします。
- process_priority / set_cpu_affinity は管理者権限やプラットフォームの制約により機能しない場合があり、その際は警告を出して継続します。

貢献・フィードバック
- バグ報告や改善提案があれば issue を作成してください。将来的にテストと CI の追加、欠落実装（research.calc_momentum 等）の完了を予定しています。