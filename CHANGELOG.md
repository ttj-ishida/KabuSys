# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog 準拠で、慣習的なセクション（Added / Changed / Fixed / Security）を用いています。

※以下の履歴はコードベースの内容から推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを導入（kabusys v0.1.0）。
  - パッケージバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 実行用エントリースクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を行う。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
    - DuckDB/SQLite の接続を確保し、finally でクローズ。

- 監視用エントリースクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視コンポーネントは環境にかかわらず本番 sqlite_path を使用する設計（注意点として明記）。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定 / ローダー
  - config.py:
    - プロジェクトルート探索（.git または pyproject.toml を基準）により .env 自動ロードを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env と .env.local の読み込み順序（OS 環境変数を保護する protected 機能）を実装。
    - export KEY=val 形式やシングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理に対応するパーサを実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / システム環境判定など）。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - env（KABUSYS_ENV）バリデーション（development / paper_trading / live）を実装。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）: スコア降順、signal_rank によるタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。スコア全てが 0 の場合は等金額配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクターエクスポージャー計算と新規候補からの除外ロジック。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた乗数を返し、未知レジームでは警告のうえフォールバック。
  - portfolio/position_sizing.py:
    - 発注株数計算（calc_position_sizes）:
      - allocation_method = "risk_based" / "equal" / "score" に対応。
      - 損切り率・risk_pct に基づく risk_based 計算。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）での縮小、cost_buffer を考慮した保守的なコスト見積りを実装。
      - aggregate 縮小時に残差処理（lot 単位で再配分）を実装。

- 研究（Research）モジュール
  - research/factor_research.py:
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB を利用し prices_daily, raw_financials テーブルを参照）。
    - 各ファクターはメモリ内結合で date, code をキーとする辞書リストを返す。
  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対応し入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を自前実装（ties は平均ランク）。
    - ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）。
  - research/__init__.py で主要関数をエクスポート。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）計算ユーティリティを提供。
    - バッチサイズ・トークン肥大化対策（最大記事数・最大文字数／銘柄）を実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライと最大リトライ回数の実装。
    - レスポンスバリデーション（JSON 構造・既知銘柄コード・スコアの数値型）とスコアの ±1.0 クリッピング。
    - OpenAI API キー未設定時に ValueError を送出。

- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差分を吸収してプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）に対応し、未対応 OS ではスキップ。権限不足時は警告ログを出力してフォールバック。
  - utils/__init__.py の準備。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加（コマンドラインから実行可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg / max / P95）など。
    - P95 計算ユーティリティ、日付フィルタ、SQLite 存在チェック、出力整形を実装。
    - デフォルト DB は data/paper_trading.db。--db オプションおよび PAPER_TRADING_SQLITE_PATH 環境変数により上書き可能。

- DB・分析基盤
  - DuckDB の利用を前提とした設計（duckdb 接続を受ける関数が多数）。
  - 監視・実行での SQLite 初期化ユーティリティ（monitoring_db.init_monitoring_db）の呼び出しを追加し、監視テーブルの存在を保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY により解決。未設定時は明示的にエラーとなるため、秘密情報の管理に注意。

---

補足（設計上の注意点・運用メモ、コードからの推測）
- run_monitoring は「監視用 DB を本番 DB（sqlite_path）で参照する」仕様であり、環境（KABUSYS_ENV）にかかわらず本番 DB を見に行く点に注意。意図的な設計の可能性が高いが、テスト環境で監視を動かす際は sqlite_path を切り替える必要がある。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用することで発注データを本番 DB と分離している（安全対策）。
- .env 自動ロードはプロジェクトルート検出に基づくため、配布後や仮想環境での実行でも CWD に依存せず動作する想定。ただし自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意しているためテストでの制御が容易。
- 多くの計算関数（ポートフォリオ・研究）は純粋関数設計で DB 参照を最小化しており、ユニットテストが容易な設計になっていることがコードから読み取れる。

もし特定ファイルごとの変更点や詳細なリリースノート（例えば各関数の挙動差分や既知の制限）をより詳しく出力したい場合は、対象のファイル名を指定してください。