CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）に記載しています。
- 日付は YYYY-MM-DD 形式です。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
- 実行エントリ/ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離（settings.is_paper）し、BrokerClientFactory 経由でブローカークライアントを取得してセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を利用する設計。
- 設定管理
  - config.py: .env / .env.local の自動読み込み（プロジェクトルート検出ベース）と柔軟なパースロジックを追加。export 形式、クォート、インラインコメント、保護キー（既存 OS 環境変数の保護）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化も実装。
  - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB / 監視 / システム設定等のプロパティ化された取得ロジックを提供（環境変数検証付き）。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力値検証を実装。
- 監視関連
  - monitoring_db の初期化呼び出しを起動スクリプト内で行うことで監視テーブル存在を保証（冪等処理）。
- ツール
  - tools/paper_verification_report.py: paper_trading の検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を出力する CLI を提供。日付フィルタ（--from / --to）と DB パス指定（--db）に対応。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコア全てが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバック（1.0）。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を追加。risk_based / equal / score の配分方式、単元株丸め（lot_size）、aggregate cap によるスケールダウン、手数料・スリッページ用 cost_buffer を考慮。
- 研究・リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算を追加（calc_momentum, calc_volatility, calc_value）。prices_daily / raw_financials を参照し、データ不足時は None を返す堅牢な実装。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティを追加。標準ライブラリのみで実装し外部依存を除外。
  - research/__init__.py: 主要関数群と zscore_normalize の公開。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む機能を追加。前日15:00 JST〜当日08:30 JST の窓で記事を集約し、1 銘柄あたり最大記事数・最大文字数でトリム、最大 20 銘柄単位でバッチ送信、429/ネットワーク/5xx 等は指数バックオフでリトライ、レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分成功時でも既存スコアを保護する置換ロジック（DELETE→INSERT）設計等を実装。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティ（set_process_priority）と CPU アフィニティ設定（set_cpu_affinity）を追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足等は警告を出してスキップするフェイルセーフを実装。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数読み込みと値検証を強化:
  - MONITOR_POLL_INTERVAL が不正（0 以下や数値以外）の場合はデフォルト 60 秒にフォールバックし警告を出力。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の不正値で早期に ValueError を送出してミスコンフィグを検出。
- DB まわり: monitoring 用のテーブル初期化をランナー起動時に呼ぶことで欠如時のエラーを抑制（init_monitoring_db を起動時に実行）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キー未設定時は明示的にエラーを出す設計（ai/news_nlp.score_news）。API キーは引数経由または OPENAI_API_KEY 環境変数で供給する必要あり。

Notes / Known issues / TODO
- apply_sector_cap 内の価格欠損（price_map に値がない場合）については TODO コメントがあり、将来的に前日終値や取得原価などのフォールバック価格導入が想定されている。現状は price が 0.0 の場合エクスポージャーが過少になる可能性がある。
- ai/news_nlp.py は堅牢性（バッチ処理、リトライ、部分更新）の設計が入っているが、ソースの一部が途中で切れているように見える箇所がある（ログ出力の途中で終わっている）。実際の DB 書込（DELETE→INSERT）の詳細実装とエラーハンドリングは本ソースの続きに依存するため、運用前に最終的な実装とテストを推奨。
- DuckDB の executemany に関する注意（コメントあり）: DuckDB のバージョンにより空パラメータでの executemany が問題になるため、パラメータが空でないことを事前確認する実装がある。
- process_priority.set_process_priority / set_cpu_affinity は権限やプラットフォーム差異により動作しない場合があり、その際は警告を出してスキップする。運用環境での権限確認を推奨。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、大規模データセットのパフォーマンス評価は実運用で確認が必要。

References
- 各モジュールの詳細な設計意図やアルゴリズムはソース内の docstring / コメント（PortfolioConstruction.md / StrategyModel.md 参照想定）に記載されています。運用前に該当ドキュメントを確認してください。