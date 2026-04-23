CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。重要な変更点、追加機能、既知の制約などをコードベースから推測してまとめました。

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 自動売買システムのコアユーティリティとランナーを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db を想定）を使用するように実装。停止フラグ（data/stop_requested.flag）検出で安全停止。実行中は PID ファイルを data/execution.pid に記録。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視では本番用 sqlite_path を環境にかかわらず使用する設計。
- 設定管理・ウィザード・検証
  - config.py: 環境変数ラッパー Settings を提供。自動でプロジェクトルートの .env / .env.local を読み込む仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。多くの設定（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading の設定等）をプロパティで提供。
  - config_setup.py: 対話式 .env 作成ウィザードを実装（.env の読み取り・上書き、マスク表示、選択肢サポート）。
  - validate_config.py: 起動前チェック CLI。必須環境変数や設定ファイル（config/*.yaml）の存在・パースチェック、KABUSYS_ENV に応じたガード（本番時の注意喚起）を行う。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定・等比重／スコア加重重み計算を実装。
  - portfolio.position_sizing: position sizing（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウンロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた資金乗数 calc_regime_multiplier を実装。
  - portfolio パッケージのエクスポートを整備。
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定。stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL を尊重し、ファイル出力に失敗した場合はコンソール出力にフォールバック。
  - utils/process_priority.py: psutil を使ったクロスプラットフォームのプロセス優先度設定および CPU affinity 設定ユーティリティ。Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装で、権限不足などはワーニングでフォールバック。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite のログから稼働率、注文成功率、送信率、API レイテンシ（P95 等）を集計して検証レポートを出力する CLI を追加。基準値（稼働率 99%、成功率 90% 等）を定義し PASS/FAIL を判定。
- DuckDB 統合
  - 実行系およびモニタリングで DuckDB 接続を受け取り、分析用途のデータベース（data/kabusys.duckdb 想定）へ接続する仕組みを導入。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを冪等に保証。

Changed
- .env 自動読み込みの振る舞いを明示
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として .env(.local) からの上書きを防止。
  - export KEY=val 形式やクォートされた値、インラインコメントの取り扱いに対応する堅牢なパーサを実装。
- ログのデフォルトと振る舞い
  - ログレベル解決順（引数 > 環境変数 > デフォルト）とログ出力先（stdout + 日次ローテートファイル）を統一。

Fixed
- 環境変数パーサの強化
  - クォート内のバックスラッシュエスケープ処理、クォートなし値のインラインコメント判定など、.env の多様な記述に耐える実装に改良。
- ExecutionEngine 起動時の DB 分離
  - paper_trading モード時に本番 DB と完全に分離された専用 SQLite を使うように明確化（デフォルト data/paper_trading.db）。

Security
- .env の注意喚起
  - config_setup で .env を生成する際に「.env を Git にコミットしないこと」を明示。

Known issues / Notes
- monitoring の sqlite_path の取り扱いに注意
  - run_monitoring.py は Monitoring を「環境にかかわらず本番 sqlite_path を使用する」と記載・実装しており、development / paper_trading と完全に分離されない点は設計上の留意点です（意図的な実装か確認推奨）。
- factor_research モジュールの未完成箇所
  - src/kabusys/research/factor_research.py の calc_momentum 関数定義内で実装が途中（ファイル末尾付近に "start_da" 等の断片）が見られます。ファクター計算の完成（DuckDB SQL 組み立て／エッジケース処理等）は今後の実装タスクです。
- apply_sector_cap の価格欠損処理
  - price_map に価格が欠損（0.0）した場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討する必要あり。
- position_sizing の lot_size 将来拡張
  - 現状は全銘柄共通の lot_size（デフォルト 100）で丸め処理。将来的に銘柄別 lot_map を受け取る拡張を想定するコメントあり。

Migration notes / Breaking changes
- 既存の運用スクリプトや監視設定を導入する際は以下を確認してください:
  - KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかである必要があります。無効値は ValueError を発生させます。
  - run_monitoring の挙動（監視 DB の使用先）は期待と異なる可能性があるため、環境ごとのデータ分離が必要な場合はコードを調整してください。
  - .env 自動読み込みはデフォルトで有効。テストや CI で自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - ログディレクトリ作成に失敗した場合はファイル出力が無効になり stdout のみとなります。LOG_DIR の書き込み権限を確認してください。

Acknowledgements / 次の作業候補
- factor_research の完成（DuckDB クエリ実装・テスト）
- apply_sector_cap の price フォールバック実装
- 銘柄ごとの lot_size サポート
- 監視（monitoring）と実行（execution）の DB 分離方針の確認／ドキュメント化
- ユニットテストと CI の整備（特に .env パーサや position_sizing の集約スケールロジック）

以上。必要であれば、各ファイルごとの変更点をより詳細に分割したバージョン履歴（例: 小さなパッチごとに分けたエントリ）も作成できます。どの粒度で記載したいか教えてください。