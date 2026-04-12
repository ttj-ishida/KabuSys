CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）に記載します。
- バージョンは [Unreleased] またはタグ付きで日付を付けます。

[Unreleased]
------------

- 特になし（初回リリースに相当する内容は 0.1.0 に含まれます）。

[0.1.0] - 2026-04-12
-------------------

Added
- 基本的なアプリケーション骨格を追加（初回公開）。
  - パッケージ全体のエクスポート定義を含む kabusys.__init__（__version__ = "0.1.0"）。
- 実行エントリスクリプトを追加。
  - run_execution.py: ExecutionEngine を起動するエントリ。KABUSYS_ENV に応じて paper_trading 用 DB/モックブローカーを使用可能。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
- 設定/環境変数管理モジュールを追加（kabusys.config）。
  - .env 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env / .env.local の読み込み順と上書き制御（OS 環境変数の保護対応）。
  - 行パーサの実装（export プレフィックス、引用符対応、インラインコメントの扱いなど）。
  - Settings クラス：J-Quants / kabuAPI / LINE / DB パス /監視閾値 /実行環境判定 等のプロパティを提供。
  - 環境変数未設定時の _require() による早期エラー報告。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
- モニタリング DB 初期化ユーティリティの呼び出しを run_* スクリプトに組み込み（init_monitoring_db）。
- Execution 関連コンポーネントを追加（骨組み）。
  - BrokerClientFactory に基づくブローカークライアント生成（paper_trading ではモックを選択）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の連携起動例を実装。
  - RiskConfig にデフォルトパラメータを設定（max_position_pct=0.20, max_utilization=0.80, …）。
- portfolio モジュール群を追加（銘柄選定・配分・リスク調整・株数決定）。
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合のフォールバック実装）。
  - risk_adjustment: apply_sector_cap（セクター集中度の除外ロジック）, calc_regime_multiplier（レジーム→倍率マップ）。
  - position_sizing: calc_position_sizes（risk_based / equal / score 向けの株数算出、lot_size で丸め、aggregate スケーリング、cost_buffer を考慮）。
- research モジュール群を追加（DuckDB を使ったファクター計算・解析）。
  - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を利用する SQL ベースの実装）。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank（同順位は平均ランクで処理）。
  - research パッケージのエクスポート（zscore_normalize を含む）。
- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp）。
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む処理を実装。
  - バッチ処理（最大 20 銘柄/回）、トークン肥大対策（記事数・文字数上限）、スコアクリッピング（±1.0）。
  - score_news による API キー解決、ニュースウィンドウ計算（calc_news_window）、部分更新の設計（部分失敗時の影響最小化）。
  - 429/ネットワーク/5xx 等に対する指数バックオフ付きリトライ設計（基本実装方針）。
- tools スクリプトを追加。
  - paper_verification_report.py: Paper Trading の検証レポートを SQLite（デフォルト data/paper_trading.db）から生成。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する CLI ツール。
- utils/process_priority を追加。
  - set_process_priority: Windows / POSIX(nice) を吸収してプロセス優先度設定を実装。未対応 OS や権限不足をログでスキップ。
  - set_cpu_affinity: 指定コア数への固定機能（利用不可時は警告してスキップ）。
- 各モジュールで DuckDB / sqlite3 の接続を利用する実装例を含む（research / ai / tools / run_*）。

Changed
- （初回）パッケージ構成上の初期整理。各サブパッケージの責務を明確化（execution / monitoring / portfolio / research / ai / tools / utils）。

Fixed
- （初回）各種入力チェックとフォールバックを整備。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック（run_monitoring）。
  - PAPER_FILL_MODE の検証と不正値時の ValueError（Settings）。
  - calc_score_weights でスコア合計が 0 の場合の等配フォールバックと警告。
  - 各ファクター計算でデータ不足時に None を返す一貫した挙動。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡せるようにしており、環境変数が未設定の場合は明示的なエラーを出す（score_news）。公開リポジトリにキーを置かない運用を推奨。

Notes / Caveats
- run_monitoring は環境（KABUSYS_ENV）にかかわらず settings.sqlite_path を使って監視テーブルを扱う設計になっています（監視データは本番 DB を参照する意図）。
- run_execution は paper_trading 環境時に paper_sqlite_path（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離する設計。
- 多くの集計／指標関数はデータ不足時に None を返すため、呼び出し側は None を扱う必要があります（tools/paper_verification_report ではその点を考慮している）。
- 一部の処理（例: position_sizing の price が欠損した場合の挙動、apply_sector_cap の price=0 の扱い）は TODO コメントで今後改善余地ありと記載。

今後の予定（例）
- ai.news_nlp: API 呼び出し時の詳細なリトライ/バックオフ実装の強化、JSON レスポンスバリデーションの追加強化。
- portfolio: 銘柄ごとの lot_size をマスタ化して個別制御を追加。
- monitoring/system_monitor の詳細実装（現在は run_monitoring のループ実行と check_once 呼び出しを提供）。

お問い合わせ
- この CHANGELOG に誤りや補足が必要な場合はリポジトリの Issue または PR でご連絡ください。