Keep a Changelog フォーマットに準拠した CHANGELOG.md（日本語）を作成しました。リリースはパッケージ内の __version__ (0.1.0) に合わせて初回リリースとして記載しています。必要なら日付や細部を調整できます。

# CHANGELOG

すべての変更は次に従って記載します: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-12
初回リリース。本リポジトリは日本株自動売買システム KabuSys の基礎コンポーネント群を提供します。主な機能は実行エンジン／監視／ポートフォリオ構築／リサーチ／ニュースNLP／ユーティリティ類です。

### Added
- パッケージメタ情報
  - __version__ を 0.1.0 として定義。
- 実行関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と切り離し。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行。
    - プロセス優先度を起動時に設定（utils.process_priority）。
    - duckdb 接続を ExecutionEngine に渡す。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - ポーリングループは例外を捕捉してログ記録し継続、KeyboardInterrupt をハンドルして正常終了。
- 設定/環境読み込み
  - config.py:
    - .env / .env.local の自動ロード機構（プロジェクトルート判定: .git または pyproject.toml）。
    - export KEY=val, 引用符付き値（バックスラッシュエスケープ考慮）やコメントのパース対応。
    - 環境変数の保護（OS 環境変数を上書きしない / .env.local で上書き可能）。
    - Settings クラスを追加し、各種設定値・型変換・妥当性チェックを提供（J-Quants, kabu API, DB パス, Paper モード設定, 監視閾値, PID/KILL ファイルパス等）。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値検証を実装。
- 監視 DB 初期化ユーティリティを用いた監視テーブルの冪等初期化（init_monitoring_db を run_* で呼び出し）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選択（同点時 signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用（既存保有時価を考慮、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知時は警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数の計算、単元株丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差に応じた追加配分ロジックを実装。
  - portfolio/__init__.py で主要関数を外部公開。
- リサーチ（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: ATR20、ATR%（相対）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組合せて PER・ROE を計算（最新財務レコードの選択を実装）。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズン同時クエリ、入力検証）。
    - calc_ic: スピアマンランク相関（IC）を計算（None 値と ties を処理、サンプル数が少ない場合 None を返す）。
    - factor_summary, rank: 基本統計量とランク付けユーティリティを提供。
  - research/__init__.py で主要関数と zscore_normalize を公開。
- ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py:
    - raw_news を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いた JSON モードでセンチメントスコアを計算・ai_scores へ反映するロジックを実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 20 銘柄）・トークン肥大化対策（記事数と文字数の上限）・スコアクリッピング（±1.0）・リトライ（429/ネットワーク/5xx）を実装する設計。
    - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時はエラーを返す。
    - 部分失敗時にも既存スコアを保護するため、更新は対象コードに限定して置換する戦略（DELETE/INSERT）。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定。アクセス権限不足や未対応 OS の場合は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能（検証・例外対応実装）。
  - utils/__init__.py を配置。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定を出力する CLI を追加。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。主要指標の閾値（稼働率99%, 成功率90%, 送信率95%, P95 <= 200ms）を定義。
    - P95 計算、欠損ハンドリング、テーブル不存在時のフォールバックを実装。
- DB 接続
  - run_* とリサーチ機能で duckdb を利用。SQLite は監視・paper trading 用に使用。
- 監視データベース初期化
  - init_monitoring_db が run_execution/run_monitoring 起動時に呼び出され、冪等に監視用テーブルを保証。

### Changed
- （初回リリースのためなし）

### Fixed
- MONITOR_POLL_INTERVAL の不正な値（0 以下や非整数）に対して警告を出しデフォルトにフォールバックする処理を実装（run_monitoring）。
- .env パーサで引用符・エスケープ・コメントの扱いを厳密化し、自動ロード動作が CWD に依存しないようプロジェクトルート探索を導入（config）。

### Security
- OpenAI API キーは明示的に引数か環境変数から取得し、未設定時は明示的にエラーを投げるようにして accidental secret leak を防止（ai/news_nlp）。

### Notes / Implementation details / ユーザ向け備考
- paper_trading モードは本番データベースと完全分離される設計（PAPER_TRADING_SQLITE_PATH を利用可能）。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようと試みる（権限がない場合はログ警告で続行）。
- duckdb を主にリサーチ用途（prices_daily, raw_financials 等）に利用し、SQL を組み合わせて高速集計を行う設計。
- 現在の実装は純粋関数で構成されるポートフォリオ構築ロジックを提供しており、DB 参照は行わない（ユニットテストしやすい設計）。
- ai/news_nlp の詳細な書き込み処理（部分的なトランザクション制御・挿入ロジック）は設計上パーティショニングして既存スコア保護を図る。実行環境では OpenAI の利用制限・レート制限等に注意。

---

今後の提案（任意）
- リリースごとの細かなコミットログから CHANGELOG を自動生成すると追跡しやすくなります（例: git-cliff 等）。
- セキュリティおよびシークレット管理については .env の取り扱いに関するドキュメント（.env.example の整備、KABUSYS_DISABLE_AUTO_ENV_LOAD の利用例）を補完すると良いです。
- ai/news_nlp のエラーハンドリングや部分更新処理のテストケースを追加することを推奨します。

必要であれば日付変更や "Unreleased" セクションへの追記、さらに詳細な修正履歴（各ファイルごとの変更点）を自動推定して追記できます。どの形式に整えるか指示ください。