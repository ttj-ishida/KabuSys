CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

フォーマットの方針:
- 署名済みのコミットやリリースノートに相当する「目に見える変更」を記載しています。
- ここに記載の内容は、提示されたソースコードの実装から推測して作成したものです。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリースを追加（パッケージバージョン: 0.1.0）。
- 実行用エントリスクリプト:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB と MockBrokerClient を使うことで本番 DB と完全に分離される。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定関連 CLI / ユーティリティ:
  - config_setup.py: .env ファイルを対話式に作成・更新するウィザードを追加。秘密値はマスク表示、選択肢サポート、書き出しテンプレートを提供。
  - validate_config.py: .env および config/*.yaml の起動前検証ツールを追加。--strict フラグで警告をエラー扱いにできる。
  - Settings クラス（config.py）: 環境変数経由の設定取得を集約。多くの設定プロパティ（DB パス、API 関連、監視閾値、環境判定など）を提供。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: 共通ログ設定を追加。コンソール（stdout）出力と日次ローテーションのファイル出力（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを追加（psutil 使用）。Windows/Linux/macOS 等に対応。
- ポートフォリオ構築ライブラリ（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）と重み算出（等分／スコア加重）を実装。
  - portfolio/risk_adjustment.py: セクター集中の上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数決定ロジック、単元株丸め、aggregate cap によるスケーリングなどを実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標計算と基準比較を行う。日付範囲オプションと DB パスの指定をサポート。
- 研究用モジュール（開始）:
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等の計算を意図）。

Changed
- .env 自動読み込みルールを導入（config.py）:
  - プロジェクトルートを .git または pyproject.toml から探索して特定し、.env（優先度低）→ .env.local（優先度高）の順でロード。
  - OS 環境変数は保護され、デフォルトで上書きされない挙動。
- run_monitoring の挙動:
  - Monitoring は KABUSYS_ENV に依らず「本番用の sqlite_path」を使用する旨を明示（運用上の注意点）。
- ログ出力の振る舞い:
  - logging_setup はログディレクトリ作成に失敗した場合でもフォールバックしてコンソール出力のみで継続するよう堅牢化。
  - コンソール出力は stdout を使用（cron 等のリダイレクト運用を想定）。
- run_execution の DB 決定:
  - paper_trading 環境では settings.paper_sqlite_path を使用して専用 DB（既定 data/paper_trading.db）に記録することで本番 DB と分離。

Fixed
- .env パーサー（config.py）を改善:
  - export キーワード、引用符付き値（シングル/ダブルクォート）内のバックスラッシュエスケープ、行内コメントの扱い、クォートなしでのコメント認識を考慮するなど、より柔軟で実運用向けのパース処理を実装。
  - 読み込み失敗時に警告を出す（例外は直接投げず警告に留める）。
- process_priority および set_cpu_affinity の例外ハンドリング強化:
  - パーミッションや未実装機能による失敗を警告で吸収し、起動中断しないようにした。
- 各種 DB 初期化・接続処理での耐障害性:
  - init_monitoring_db が idempotent（冪等）に呼べることを想定して起動時に必ずテーブル存在を保証する処理を呼び出すようにした（run_execution/run_monitoring）。
- paper_verification_report:
  - データ不足やテーブル未存在時に sqlite3.OperationalError を捕捉してレポート生成を続行できるようにした（存在しない場合は N/A を表示）。

Deprecated
- なし（初回リリース）

Removed
- なし

注記 / マイグレーション
- 重要: run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。テスト環境で monitoring を実行する場合は sqlite_path を切り替えるか仮想化してください。
- paper_trading 実行時は run_execution が settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと完全に分離されます。paper_trading 用 DB を消去・再生成することで検証データを管理できます。
- .env 自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます（テスト用途に便利）。

開発者向けメモ（推測）
- 多くのユーティリティはテストを想定した堅牢化が行われており、エラー時は警告ログ出力に留めてプロセスの継続を優先しています。
- ロギング・プロセス優先度・PID/停止フラグなどは運用環境での安定稼働を意識した実装になっています。
- portfolio / position sizing 周りは将来的に銘柄別 lot_size や価格フォールバック（前日終値等）を導入する拡張を想定した TODO コメントが残されています。

--- 
（以上）