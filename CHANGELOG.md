KEEP A CHANGELOG 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。必要なら日付やバージョンを調整してください。

---
# Change Log

すべての主要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを想定しています。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用（src/kabusys/run_monitoring.py）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 専用 DB（data/paper_trading.db）へ記録する。停止フラグ／PID ファイルの扱いを実装（src/kabusys/run_execution.py）。

- 設定・環境変数管理の強化
  - .env 自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml）を追加。読み込み順は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（src/kabusys/config.py）。
  - .env パーサーを強化し、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応（src/kabusys/config.py）。
  - Settings クラスを定義し、各種設定（DB パス、API トークン、PID/kill フラグ、監視閾値、環境判定等）をプロパティ化。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL のバリデーションを追加（src/kabusys/config.py）。

- モニタリング DB 初期化ユーティリティの呼び出し
  - run_* スクリプトで init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。

- プロセス運用ユーティリティ
  - set_process_priority(level) を導入して起動直後にプロセス優先度を設定（Windows / POSIX を吸収）。CPU affinity 設定関数 set_cpu_affinity を追加（src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。スコア総和が 0 の場合は等配分にフォールバック）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier。未知レジームは警告を出して 1.0 でフォールバック）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージの __init__ にて上記を公開（src/kabusys/portfolio/__init__.py）。

- 研究・リサーチモジュールを追加
  - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 上の prices_daily / raw_financials を参照して実装。MA200、ATR20、各種リターンなど（src/kabusys/research/factor_research.py）。
  - feature_exploration: 将来リターン (forward returns)、IC（Spearman の ρ）計算、ファクター統計要約（factor_summary）、ランク関数（rank）を実装。外部ライブラリに依存しない純 Python 実装（src/kabusys/research/feature_exploration.py）。
  - research パッケージのエクスポート設定を追加（src/kabusys/research/__init__.py）。

- 検証ツール追加
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を計算し PASS/FAIL を判定。コマンドライン引数 --from / --to / --db をサポート（src/kabusys/tools/paper_verification_report.py）。

- ニュース NLP（AI）スコアリング基盤
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込むための設計と実装（バッチ処理、トリミング、リトライ、レスポンス検証、スコアクリッピング等）。タイムウィンドウ計算ユーティリティ calc_news_window を実装（src/kabusys/ai/news_nlp.py）。
    - 注意: ファイルは途中で切れているため、一部実装（記事フェッチ等）が未完了の状態であることを CHANGELOG に明記。

### Changed
- run_monitoring の振る舞い
  - 監視プロセスは KABUSYS_ENV にかかわらず本番の sqlite_path を使用するように設計。ポーリングループで停止フラグ（data/stop_requested.flag）を参照して安全に終了する（src/kabusys/run_monitoring.py）。

- run_execution の DB 分離
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、本番 DB と完全分離する設計に変更（src/kabusys/run_execution.py）。Monitoring テーブルの存在確認は冪等に行う。

- ログ・例外ハンドリング強化
  - ポーリング中の monitor.check_once() に例外キャッチを追加し、例外発生時もループを継続するフェイルセーフを実装（src/kabusys/run_monitoring.py）。
  - .env 読み込み失敗時は warnings.warn を用いてユーザに通知するよう改善（src/kabusys/config.py）。
  - process_priority の失敗時（権限不足、未サポート OS 等）に警告を出して処理をスキップするよう変更（src/kabusys/utils/process_priority.py）。

- 設定バリデーション
  - Settings にて KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL の入力チェックを追加。無効な値は ValueError を送出し早期検出を促す（src/kabusys/config.py）。

### Fixed
- 環境変数 MONITOR_POLL_INTERVAL の不正値対応
  - 0 以下や整数以外の指定で ValueError を避け、デフォルト 60 秒にフォールバックして警告を出す（src/kabusys/run_monitoring.py）。

- calc_score_weights の全スコア 0 のケース
  - スコア合計が 0 の場合に等金額配分へフォールバックし警告を出す（src/kabusys/portfolio/portfolio_builder.py）。

- position_sizing のスケーリング処理の端数配分
  - aggregate cap 超過時にスケールダウンし、lot_size 単位で残余キャッシュを有効活用するロジックを実装（src/kabusys/portfolio/position_sizing.py）。

- research / feature_exploration の堅牢性向上
  - horizons の検証（正の整数かつ <=252）、重複除去、返り値列名の整備等を追加。rank() は同順位の平均ランク処理と丸めによる ties 対策を実装（src/kabusys/research/feature_exploration.py）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

## [0.1.0] - 初回リリース（推定）
- 基本的なトレード実行基盤、監視、ポートフォリオ構築、研究ツール、Paper Trading 検証ツール、AI ニューススコアリングの基礎を追加。
- 詳細は Unreleased の項目を参照。

---

注記:
- ai/news_nlp.py は設計が詳細に記載されており多くの機能（バッチ処理、リトライ、レスポンス検証など）が実装予定ですが、提示されたコードは途中で切れており（_fetch_articles 呼び出し直後に中断）完全実装ではないため、本 CHANGELOG では「基盤実装を追加、ただし一部未完了」として扱っています。実運用前に残りの実装・テスト（記事取得、OpenAI 呼び出しループ、DB 書込処理の完成）を推奨します。
- 日付やバージョン番号は実際のリリースポリシーに合わせて更新してください。