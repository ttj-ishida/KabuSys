CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).
変更は重大なものから順に記載しています。

Unreleased
----------

- 進行中:
  - research/factor_research.py 内のモメンタム計算関数が途中で切れており（実装未完）、追加実装および検証が必要です。
  - position_sizing や risk_adjustment 内に将来的な拡張（銘柄ごとの lot_size 管理、価格フォールバック等）の TODO が残っています。

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション構成と初回リリース機能を追加。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。エンジンはスレッドで実行され、停止フラグ（data/stop_requested.flag）を検出して安全に停止。
    - 実行用 PID ファイル（data/execution.pid）を管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視データは常に本番 DB に格納）。
    - 停止フラグ（data/stop_requested.flag）検出、例外キャッチ、KeyboardInterrupt 対応、DB 接続のクローズを実装。

- 設定管理
  - config.py: 環境変数/.env の読み込みと Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - export KEY=val 形式のサポート、クォート値（シングル/ダブル）とバックスラッシュエスケープ対応、インラインコメント処理の改善。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスによるプロパティアクセス（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、各種監視閾値、PID/kill flag パスなど）。
    - env 値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）とエラーメッセージ。

- 設定ヘルパー CLI
  - config_setup.py: 対話式 `.env` 作成・更新ウィザードを追加。
    - 質問形式で主要設定を入力、既存 .env の読み込み・再利用、秘密値のマスク表示、保存確認の実装。
    - .env 書き込みテンプレートを提供（.env を絶対にコミットしない旨の注意を含む）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス存在チェック（親ディレクトリ）、config/*.yaml の存在とパース検証（PyYAML があれば中身を検査）、本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア正規化配分（スコア全て 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーが上限を超える場合に新規候補を除外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（未知レジームは 1.0 でフォールバック、警告ログ）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく発注株数計算。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash） を考慮。
      - cost_buffer による保守的コスト見積りと、スケールダウン後の残差を使ったロット追加配分ロジックを実装。
      - price が不正な場合のスキップ、現在ポジションを考慮した追加数計算等。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通のログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）、ログディレクトリ作成時のフォールバック（作成失敗時はファイル出力をスキップしてコンソールのみ）。
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity: 指定コアにプロセスをピンニングするユーティリティ。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 監視用 DB 初期化
  - monitoring/monitoring_db (import 経路を run_* スクリプトで使用): 監視テーブルの初期化処理を起動時に冪等に実行するよう追加（存在しない場合は作成）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite を読んで検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計。
    - 判定基準（稼働率>=99%、fill_rate>=90%、send_rate>=95%、P95<=200ms）を実装し、PASS/FAIL を出力。
    - 日付範囲フィルタ（--from, --to）と DB パス指定（--db / 環境変数）に対応。

Changed
- 初期アーキテクチャとして、実行系（ExecutionEngine）と監視系（SystemMonitor）を分離して起動スクリプトを用意。プロセス優先度を起動直後に High に試行設定する設計を採用。
- 環境変数読み込みの優先順位を明示 (.env.local が .env を上書き可能)。OS 環境変数は保護されるため、.env の値で上書きされない。

Fixed
- 環境変数パースの堅牢化:
  - export プレフィックスのサポート、クォート内でのバックスラッシュエスケープ、クォート外のコメント判定の改善により .env の取りこぼしや誤解析を軽減。
- ログディレクトリ作成やファイルハンドラ作成の失敗時にプロセスが落ちないようにフォールバック実装を追加（コンソール出力のみで継続）。

Security
- .env 作成ウィザードで秘密値はマスク表示。README 等で .env を Git に含めない旨を明示するテンプレートを出力。

Known issues / Notes
- research/factor_research.py の一部が未完（関数途中切れ）。因果的にファクター計算ロジックの完全実装・テストが必要です。
- position_sizing の将来タスク:
  - 銘柄別 lot_size をサポートする拡張（現在は全銘柄共通で lot_size=100 を想定）。
  - 価格欠損時のフォールバック（前日終値や取得原価等）の実装（現状は price が 0.0 の場合に保守的にスキップ）。
- run_monitoring は監視用 DB 接続に sqlite3 を、分析用に duckdb を開く設計。DB パスやファイル権限に注意してください。
- set_process_priority / set_cpu_affinity は権限不足の環境（コンテナや制限されたホスト）では効果がない場合があります。警告をログ出力しますが、動作を保証するものではありません。

その他
- テスト・CI については本リリース時点での言及なし（今後追加予定）。
- ドキュメントや README、運用手順（起動・停止フラグの扱い、ログローテーション、.env の管理）を整備することを推奨します。

----- 
（注）この CHANGELOG は現在のコードベースから推測して作成したもので、実際の変更履歴／コミット履歴をそのまま反映したものではありません。必要に応じて実際の Git コミットメッセージ等に基づいて調整してください。