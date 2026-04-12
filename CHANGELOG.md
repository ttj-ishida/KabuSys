# Changelog

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

テンプレートの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [0.1.0] - 2026-04-12

### Added
- 初期リリース — KabuSys 基本コンポーネントを実装。
- 実行（Execution）関連
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度を起動時に "high" に設定。
    - 環境に応じて Paper Trading 用の専用 SQLite DB を使用（KABUSYS_ENV=paper_trading 時に PAPER_TRADING_SQLITE_PATH を利用）。
    - DuckDB 接続を利用したデータ処理をサポート。
    - BrokerClientFactory によるブローカークライアント生成（実運用 / モックを環境で切替）。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立ててセッションを実行。
    - RiskConfig によるデフォルトパラメータ（max_position_pct, max_utilization 等）を設定。
- 監視（Monitoring）関連
  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB は本番データを参照する仕様）。
    - 監視ループ内で check_once() の例外を捕捉して継続するフェイルセーフ挙動。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - 各種環境変数のアクセス用プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等）。
    - 入力値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェック）。
- ポートフォリオ構築（純関数群）
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（銘柄スコア順・等配分・スコア加重）。
  - position_sizing: calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer 対応）。
  - risk_adjustment: apply_sector_cap（セクターごとの既存エクスポージャーに基づく候補除外）、calc_regime_multiplier（market regime に応じた乗数）。
- リサーチ／特徴量関連
  - research.factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算。prices_daily / raw_financials を参照）。
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（将来リターン、IC（Spearman rank）計算、統計要約）。
  - 全体方針として pandas 等外部データフレーム依存を避け、DuckDB + 標準ライブラリのみで実装。
- AI ニュース NLP
  - ai.news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコア算出機能（score_news）。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン過剰対策（記事数・文字数トリム）、リトライ（指数バックオフ）、レスポンス検証、±1.0でのクリップ、部分失敗時に既存スコア保護（対象コードに限定して差し替え）などの堅牢化処理を実装。
    - calc_news_window により JST ベースのニュース収集ウィンドウを UTC に変換して使用。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定（psutil ベース）。Windows / POSIX(Linux, Darwin, FreeBSD) に対応し、権限不足や未対応環境では警告を出して安全にスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト（system_status / trade_logs / risk_logs を集計して稼働率、成功率、送信率、P95 レイテンシ等を報告、閾値に基づく PASS/FAIL 判定）。

### Changed
- パッケージメタデータ
  - バージョンを __version__ = "0.1.0" として公開。

### Fixed
- 例外・欠損データ耐性の強化
  - 各種集計・計算関数はデータ不足時に None を返す等、安全に動作するように実装（sqlite3.OperationalError を想定したフォールバックも含む）。
  - run_monitoring のメインループは check_once() の例外をキャッチしてログ出力のうえ次回ポーリングへ継続する。

### Notes / Known issues / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過小見積りされてしまい意図せぬブロックが外れる可能性あり（ソース内で TODO コメントあり）。前日終値や原価等のフォールバック導入が検討課題。
- position_sizing の lot_size は現状全銘柄共通（100）を想定。将来的には銘柄別 lot_map を導入する予定（TODO コメントあり）。
- DuckDB の実装差異により executemany に空パラメータが渡せない制約を考慮した実装上の注意がある（ai.news_nlp の設計メモ）。
- news_nlp の実装は OpenAI API キー必須（環境変数 OPENAI_API_KEY または引数）。API 呼び出しの失敗（429/ネットワーク/5xx）はリトライを試行するが、最終的に失敗した場合は該当チャンクをスキップして続行する設計。
- run_monitoring は「監視用 DB を本番 sqlite_path に固定して使用する」挙動に注意（監視は本番 DB を参照する方針）。

### Security
- OpenAI API キー等の機密値は Settings 経由で環境変数から取得することを想定。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能。

---

（本 CHANGELOG は提供されたソースコードの内容・コメントから推測して作成しました。実際の変更履歴やバージョン運用方針に合わせて適宜修正してください。）