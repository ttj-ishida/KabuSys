# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: 以下の履歴はソースコードの内容から推測して作成しています。実際のコミット履歴やリリース日とは異なる可能性があります。

## [Unreleased]

### Added
- 環境変数の自動ロードを改善
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の行パーサに `export KEY=val`、クォート文字内のバックスラッシュエスケープ、インラインコメント処理を追加。
- 設定管理クラス Settings を追加し、アプリケーション全体で環境変数を統一的に取得・検証できるようにした（J-Quants / kabuAPI / LINE / DB / 監視 / システム関連のプロパティを提供）。
- モニタリングおよび実行の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。例外発生時はログ出力して次回ポーリングへフォールバック。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動。paper_trading 環境では MockBrokerClient / 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番DBと完全分離。
- プロセス優先度・CPU affinity ユーティリティを追加（utils/process_priority.py）
  - Windows / POSIX の差分を吸収してカレントプロセスの nice / priority / cpu_affinity を設定可能。権限不足や非対応 OS は警告でスキップ。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - 候補選定（select_candidates）、等重 / スコア重み計算（calc_equal_weights / calc_score_weights）。
  - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - 発注株数計算（calc_position_sizes）：risk_based / equal / score の配分方式、単元株丸め、aggregate cap（available_cash）に基づくスケールダウン、手数料・スリッページ用 cost_buffer。
- リサーチ機能を追加（kabusys.research）
  - ファクター計算（momentum / volatility / value）：DuckDB の prices_daily / raw_financials を利用して各種ファクターを計算。
  - 特徴量探索（forward returns / IC / factor summary / rank）：将来リターン計算、スピアマンrank相関（IC）、ファクター統計サマリ等。外部ライブラリ非依存で標準ライブラリのみで実装。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols から記事を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
  - タイムウィンドウ計算、記事数／文字数上限、チャンクバッチ（最大 20 銘柄）、429/ネットワーク/5xx の指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の書き込み保護などを実装。
- Paper Trading 向け検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - CLI オプション（--from / --to / --db）対応。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 99% など）。

### Changed
- DB 周りの扱いを明確化
  - monitoring 初期化は冪等に行い、run_execution/run_monitoring ともに sqlite（SQLite3）と DuckDB 接続を作成して最後に確実にクローズするようにした。
  - run_execution では KABUSYS_ENV=paper_trading の際に paper_sqlite_path を使って本番 DB と分離。
- エラーハンドリング / ロギングを強化
  - モニタリングループ内の予期せぬ例外をキャッチしてスタックトレースを出力し、ループを継続するようにした。
  - 環境変数の不正値に対するフォールバック（MONITOR_POLL_INTERVAL が不正な場合はデフォルト 60 秒を使用）や警告メッセージを追加。
- 設定値検証を追加
  - PAPER_FILL_MODE の有効値チェック（instant|partial|never|reject）を追加。
  - KABUSYS_ENV / LOG_LEVEL の検証とエラー報告を追加。

### Fixed
- 空データに対する堅牢化
  - factor / latency / order 統計の集計クエリや P95 計算でデータが無い場合に None を返す等、Null 安全を考慮。
  - calc_score_weights: 全スコアが 0 の場合に等重配分へフォールバックして警告を出す。
  - calc_position_sizes: 価格欠損や price <= 0 を検出してスキップする処理を追加。
- process_priority の権限エラーや未対応 OS を警告でスキップするように変更（アプリの起動を妨げない）。

### Security
- OpenAI API キー未設定時は明確に ValueError を送出して処理側で取り扱えるようにした（news_nlp）。

---

## [0.1.0] - 初回リリース

### Added
- 初期実装として以下の主要機能を提供
  - 基本パッケージ情報（kabusys.__version__ = "0.1.0"）。
  - 環境変数・.env ロードと Settings クラスによる統一設定管理。
  - 実行系/監視系スクリプト（run_execution, run_monitoring）。
  - ExecutionEngine 周りの組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）と起動フロー。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db の利用）。
  - DuckDB を用いたリサーチ / ファクター計算モジュール（momentum, volatility, value）。
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数）。
  - ニュース NLP スコアリング（OpenAI 連携の基盤）および ai_scores 書き込み設計。
  - Paper Trading 用ログ・DB 分離（data/paper_trading.db）と検証レポートツール（paper_verification_report）。
  - ユーティリティ群（process priority / CPU affinity 設定、research の統計ユーティリティ等）。
- ドキュメント的な注釈や設計コメントを各モジュールに記載（PortfolioConstruction.md / StrategyModel.md 参照など、実装方針を明記）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

---

備考
- 本 CHANGELOG はソースコードから推測して作成しています。実際のバージョン管理（git）のコミットメッセージやタグ付けと差異がある場合があります。リリース日や詳細な修正履歴は実際の履歴に基づいて更新してください。