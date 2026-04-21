CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-21
-------------------

Added
- 初版リリース。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ経由で実行環境に応じたクライアントを生成。
    - ExecutionEngine をデーモンスレッドで起動し、 data/stop_requested.flag による停止検出、pid ファイル管理、DB（SQLite / DuckDB）接続管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告を出力）。
    - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使用する設計。
    - data/stop_requested.flag による停止処理、KeyboardInterrupt のハンドリング、SQLite / DuckDB 接続のクリーンアップを実装。
- 設定管理
  - config.py: 環境変数読み込み・ラッパーを実装。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロード（必要に応じて自動ロードを無効化可）。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 各種設定プロパティ（DB パス、LINE トークン、KABUSYS_ENV 判定、PAPER_FILL_MODE など）を提供し、値の妥当性チェックを実施。
    - settings インスタンスをグローバルに提供。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL 等）を対話的に入力して .env を生成・更新。
    - シークレット項目は入力時マスク表示、保存前に確認を行う。
  - validate_config.py: 起動前設定検証用 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML がある場合は）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START 設定への警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化関数を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログを logs/<app_name>.log に出力（30 日分保持）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラを一旦閉じてから再設定することで二重出力を防止。
  - utils/process_priority.py: プロセス優先度と CPU affinity のユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収して優先度（high/normal/low）を設定。
    - psutil の権限エラー等を安全にハンドリングしてフォールバック。
    - set_cpu_affinity による最初 N コアへのピン留め機能。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・signal_rank でタイブレークして選定。
    - calc_equal_weights / calc_score_weights: 等比重・スコア加重の重み計算（全スコアが 0 の場合は等比重にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮して新規候補を除外）。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - risk_based: 許容リスク率、損切り幅から各銘柄のベース株数を算出。
      - equal/score: weight に基づく割当て。per-position 上限・lot_size（単元）丸め、price が不正な銘柄はスキップ。
      - aggregate cap: 全銘柄合計コストが available_cash を超える場合はスケールダウンし、lot_size 単位で残差調整を行うロジックを搭載。
      - cost_buffer による手数料・スリッページ見積りを考慮。
- Paper Trading / 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を抽出して検証レポートを生成。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、データ不在時の安全処理を実装。
- 研究向けファクター計算基盤
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム等のファクターを計算する設計を追加（Momentum, MA200 dev, ATR 等。関数インタフェースと設計方針を含む）。
- パッケージ情報
  - __init__.py: バージョンを "0.1.0" に設定し、主要モジュールを __all__ で公開。

Changed
- なし（初版）

Fixed
- なし（初版）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known limitations
- factor_research.py は大枠の実装・設計を含むが、ファイル末尾が未完の可能性があり（スニペット切れ）、実装の継続が必要。
- position_sizing の price 欠損時の補完（前日終値や取得原価など）について TODO コメントあり。将来的に価格フォールバックが必要。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特異なディレクトリ構成では自動検出がスキップされる可能性がある（KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止可能）。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で設定できない場合があり、その場合は警告を出してスキップする。

開発者向けメモ
- ロギングは stdout を使う仕様（cron や Task Scheduler での stdout/stderr 一括リダイレクトを想定）。
- 実行/監視スクリプトは data/stop_requested.flag を監視して安全に停止できるように設計。
- Paper Trading と本番 DB は分離される設計（エンジンは settings.is_paper に応じて paper_sqlite_path を使用）。

--- 
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートにはリリース日・作者・マイナーな修正点などを適宜追記してください。