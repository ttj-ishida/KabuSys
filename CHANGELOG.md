CHANGELOG
=========

すべての注目すべき変更を記録します。形式は「Keep a Changelog」に準拠しています。

注: 本ログはリポジトリ内のコードから推測して作成しています。実際のコミット履歴とは一致しない可能性があります。

Unreleased
----------

変更予定 / 既知の TODO / 改善点（今後のリリースで対応予定）

- 研究モジュール (kabusys.research.factor_research) の実装完了
  - ファクター計算の一部が途中で切れているため、残りの SQL/計算ロジックを実装予定。
- position_sizing の単元株（lot_size）管理を銘柄別に拡張する予定（現在は全銘柄共通の lot_size を想定している）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価）の実装検討。
- ロギング周りのファイルハンドラ作成失敗時の挙動改善とリトライ処理（現状は警告ログを出してコンソール出力にフォールバック）。

[0.1.0] - 2026-04-23
--------------------

Added
- 基本アプリケーション情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（Paper 時は MockBrokerClient が想定）。
    - エンジンはデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）の検出で安全に停止。
    - 実行中の PID を data/execution.pid に書き出す仕組みを用意（pid_file を Engine に渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を上げる（set_process_priority("high")）。

- 設定管理 / CLI
  - config.py
    - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env のパースは引用符・エスケープ・インラインコメントに対応する堅牢な実装。
    - Settings クラスを追加し、環境変数をラップして型変換やバリデーションを提供。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の妥当性チェックを実装。
    - SQLite / DuckDB / Paper 用 DB パスや PID / Kill flag 関連設定をプロパティとして定義。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を追加。
    - 秘匿設定はマスク表示、選択肢・デフォルトを提示して簡単に初期化可能。
  - validate_config.py
    - 起動前に設定（.env / config/*.yaml）を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコア全0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - セクター上限判定や unknown セクターの扱いについての仕様を明記。
  - portfolio/position_sizing.py
    - position size 計算ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・全体利用上限（max_utilization）、コストバッファ（cost_buffer）を考慮したスケーリング（aggregate cap）を実装。
    - スケーリング時の再配分アルゴリズム（fractional remainder に基づく lot 単位での追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログレベルおよびログディレクトリ解決ルールを実装。ログディレクトリ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux / macOS / FreeBSD）差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定を行うユーティリティを追加。
    - psutil の権限エラー等を適切にハンドリングして安全にフォールバック。

- 監視・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプション対応。

- データ基盤
  - DuckDB 接続の利用を各所で明示（research モジュールや実行スクリプトで duckdb.connect を使用）。
  - 監視用 DB 初期化関数 init_monitoring_db が複数起動スクリプトで呼ばれる（冪等にテーブル存在を保証）。

Changed
- なし（本リリースは初期リリースのため「Added」が中心）。

Fixed
- なし（明示的なバグ修正履歴はコードからは確認できず、主に新規追加）。

Deprecated
- なし。

Removed
- なし。

Security
- なし（セキュリティ関連の明示的変更は無し。ただし機密情報は .env に保存する旨を README 等で注意する実装になっている）。

注記 / 実装上の注意
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール環境でも動作するように __file__ を基準に親ディレクトリを探索する実装になっている。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- run_monitoring は監視 DB に対して「環境にかかわらず本番 sqlite_path を使用する」仕様となっているため、テスト環境で監視 DB を分離したい場合は設定に注意が必要。
- run_execution は paper_trading 用の DB を分離する設計だが、PAPER_TRADING_SQLITE_PATH による上書きが可能。
- 一部モジュール内に TODO コメントが残っている（例えば価格欠損時のフォールバック、銘柄毎 lot_size 管理など）。将来的に改善予定。

--- 

（補足）この CHANGELOG はコード内容から推測して作成しています。実際のコミットメッセージや日付が必要であれば、git 履歴を解析して正確な CHANGELOG を生成できます。必要であればその旨お知らせください。