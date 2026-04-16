# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベース（src/ 以下）の現状から実装内容を推測して作成した初期の変更履歴です。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）に整理しています。
- 日付はリポジトリ内の実装（コメントや例）を参考に設定しています。
- 一部実装の未完（TODO）や注意点は "Unreleased" に記載しています。

## [Unreleased]

### Added
- 監視・実行系の運用補助
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書き可能（run_monitoring）。
  - 実行エンジンのプロセス PID 管理／停止フラグ対応（run_execution/run_monitoring）。
  - 実行エンジンは KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite を使用（data/paper_trading.db 想定）。

### Changed
- Settings の .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う仕様に明確化。  
  - .env → .env.local の順で読み込み、OS 環境変数は保護される（上書き禁止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

### Fixed / Notes
- 複数箇所に残る TODO / 注意点を列挙（優先対応推奨）:
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題（フォールバック価格の導入が必要）。
  - ai/news_nlp モジュールの実装が途中（ファイル末尾が切れており _fetch_articles 呼び出し以降が未実装）ため、ニューススコアリング処理は現状で動作しない可能性あり。
  - DuckDB へ executemany で空パラメータを渡すと失敗する点への注意（コメントで対処済みの記述あり）。

### Deprecated
- なし

### Removed
- なし

---

## [0.1.0] - 2026-04-16

初回リリース（コードベースの主要機能群を実装）。

### Added
- コアパッケージ情報
  - kabusys パッケージ初期版（__version__ = 0.1.0）。

- 設定管理
  - Settings クラスを実装（環境変数経由で設定取得、検証付き）。
  - J-Quants / kabu API / LINE / DB パス / 監視・しきい値など主要設定をプロパティとして用意。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject を許容）。

- 実行・監視インフラ
  - run_execution.py:
    - ExecutionEngine 起動スクリプト（スレッドで実行、停止フラグ検知で安全停止）。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading モードで Mock を利用）。
    - RiskManager の初期設定（デフォルト値: max_position_pct=0.20 など）。
    - OrderRepository / OrderManager / Reconciler 等の組み立てと Engine の起動処理。
  - run_monitoring.py:
    - SystemMonitor の単純ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）。
    - 停止フラグ検知でループ終了、例外時はログ出力して次ポーリングへ継続。

- データベース連携
  - sqlite3（監視用）および DuckDB の接続初期化を実装（init_monitoring_db 呼び出し）。
  - paper_trading DB と本番 DB の分離（Settings に paper_sqlite_path を追加）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順、タイブレークルールあり）。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限のフィルタリング）。
    - calc_regime_multiplier（market regime による投下資金乗数）。
  - portfolio/position_sizing.py:
    - calc_position_sizes（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、aggregate cap によるスケールダウン、残余キャッシュを用いた再配分ロジックを実装。
    - cost_buffer による手数料・スリッページの保守的見積り対応。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority（Windows / POSIX の差分吸収）。
    - set_cpu_affinity（プロセスの CPU affinity 固定、引数検証あり）。
    - psutil の権限不足や未対応 OS では安全にスキップして警告ログを出力。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - calc_volatility（ATR20、相対 ATR、出来高指標）。
    - calc_value（最新財務データと株価から PER / ROE 計算）。
    - DuckDB による SQL 実装で大量データの計算を想定。
  - research/feature_exploration.py:
    - calc_forward_returns（複数ホライズンの将来リターン）。
    - calc_ic（スピアマンランク相関による IC 計算）。
    - factor_summary / rank（統計サマリー、ランク計算）。
  - research/__init__.py に主要関数をエクスポート。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - CLI オプションで期間指定（--from / --to）および DB パス指定（--db）に対応。

- AI（ニュース NLP、実装途中まで）
  - ai/news_nlp.py（ニュース記事の OpenAI を用いたセンチメントスコアリング設計を実装）
    - ニュース窓（前日15:00 JST ～ 当日08:30 JST）の計算ユーティリティ calc_news_window。
    - OpenAI API を使ったバッチスコアリングの設計（モデル gpt-4o-mini、JSON Mode 想定）。
    - バックオフ・リトライ、レスポンスバリデーション、スコアクリッピング（±1.0）、書き込み戦略（部分置換）などを設計。
    - 実装は大半完了しているが、ファイル末尾で処理が切れており完全実装には追加作業が必要。

### Changed
- 環境変数パーサの強化（configモジュール）
  - export KEY=val 形式に対応。
  - クォート文字列（'"/）やバックスラッシュエスケープの解析に対応。
  - 行末コメントの扱いを精密化（クォート内は無視、クォート外は '#' の前が空白の場合をコメントと判断）。
  - .env の読み込みは既存 OS 環境変数を保護する設計（protected set）。

### Fixed
- 複数の SQL クエリで NULL / データ不足時の保護ロジックを追加（例: factor_research, paper_verification_report の各クエリでの NULL チェック・フォールバック）。

### Security
- OpenAI API キー未設定時は明示的に ValueError を発生させる（ai/news_nlp.score_news）。

### Documentation / Comments
- 各モジュールに設計方針・注意事項・参照ドキュメント（PortfolioConstruction.md 等）をコメントで明記。

### Known limitations / Notes
- ai/news_nlp モジュールはファイル末尾が切れており、_fetch_articles 以降の処理が未実装のため本番稼働には追加実装が必要。
- portfolio/risk_adjustment.apply_sector_cap の price 欠損時のフォールバック未実装（TODO コメントあり）。
- process_priority/set_cpu_affinity は権限不足で失敗する可能性があるため警告ログでスキップする設計。
- DuckDB の executemany の挙動に注意（空パラメータ集合の扱い） — ツール内で対策の注記あり。

---

（注）この CHANGELOG はソースコードの実装内容から推測してまとめたものであり、実際のコミット履歴やリリース方針に基づくものではありません。必要に応じて日付・カテゴリ・詳細を公式のコミット履歴に合わせて修正してください。