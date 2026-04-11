# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-11
初期リリース。自動日本株売買システム「KabuSys」のコアモジュール群を収録しています。  
主要な機能、設計方針、注意点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを公開。モジュールは監視、実行、ポートフォリオ構築、リサーチ、AI 補助、ユーティリティ等を含む。
  - DuckDB / SQLite を組み合わせたデータアクセス設計（DuckDB は分析用、SQLite はモニタリング・注文レポジトリ等）を採用。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を用いて本番 DB と分離して実行可能。
    - 実行時にプロセス優先度を高く設定（utils.process_priority.set_process_priority）。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）。
    - デフォルトのリスク設定（RiskConfig）を組み込み、broker.get_available_cash() を初期ポートフォリオ値として使用。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する点に注意。
    - 起動時にプロセス優先度を高く設定。

- 設定管理
  - src/kabusys/config.py:
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env ファイルのパース実装（export 形式、シングル/ダブルクォート、エスケープ、コメント処理に対応）。
    - Settings クラスを提供し、環境変数をラップ。必須値チェック（_require）・値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH など）と監視閾値（CPU/MEM/DISK）をプロパティで提供。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分を実装（スコア全てが 0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告後 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。lot_size（単元）丸め、per-stock 上限、aggregate cap、コストバッファ、スケールダウンロジック、端数処理（fractional remainder）を実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算（必要行数が不足する場合は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（欠損データの扱いに注意）。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算。
    - DuckDB の SQL ウィンドウ関数を活用した効率的実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得（horizons 検証あり）。
    - calc_ic: スピアマン順位相関に基づく IC 計算（レコード数が少ない場合は None）。
    - rank / factor_summary: ランク計算（同順位は平均ランク）と基本統計量サマリーを実装。
  - research パッケージは外部依存を極力避け、DuckDB 接続を受けて動作。

- AI 補助機能
  - src/kabusys/ai/news_nlp.py:
    - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄単位のセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウを JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - バッチ処理（最大 20 銘柄 / リクエスト）、記事数/文字数トリム、JSON Mode レスポンス想定、レスポンスバリデーション、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx）、書き込みは部分成功耐性（対象コードに限定して DELETE → INSERT）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - 実装はルックアヘッドバイアスを防止する設計（date.today 等を参照しない）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロキーワードによる raw_news フィルタ、ma200 比率の計算（target_date 未満のデータのみを使用）、合成スコアのクリップ、エラー時は macro_sentiment=0.0 で継続。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは専用実装（news_nlp と直接結合しない）。

- ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。
    - アクセス権限不足や未対応 OS の場合は警告ログを出してスキップ。

### Changed
- （初期リリースのため履歴は無し）

### Fixed
- （初期リリースのため履歴は無し）

### Security
- OpenAI API キーは明示的に引数または環境変数から取得する仕様（.env を自動で読み込むが OS 環境変数を保護する仕組みあり）。

### Notes / 注意事項
- 環境読み込み
  - .env の自動読み込みはプロジェクトルート検出が成功した場合にのみ行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
  - .env.local は .env を上書きするため、テスト環境やローカル設定の上書きに利用できます。既存の OS 環境変数は保護されます。

- Paper trading
  - paper_trading 環境では SQLite を分離して使用するため、本番 DB とデータが混在しません（安全設計）。

- ルックアヘッドバイアス対策
  - research / ai モジュールは date.today() / datetime.today() を直接参照しない設計で、target_date を明示的に与えることで将来情報の参照を防止しています。

- フォールバック動作
  - ファクター計算やレジーム判定はデータ不足や API エラー時に安全側のフォールバック（例: 中立値 1.0、macro_sentiment=0.0、等金額配分へのフォールバック）を行います。

- ロギング / フェイルセーフ
  - 多くの箇所で警告ログや例外ハンドリング（リトライ、スキップ、部分書き込み保持）が組み込まれており、外部 API の失敗や一部データ欠損時でも処理継続を重視しています。

### Breaking Changes
- （初版のため無し。ただし Settings のプロパティは環境変数の値検証を行うため、不正な環境変数値は ValueError を発生させます。環境設定時は .env.example を参照してください。）

---

今後の予定（メモ）
- 銘柄別 lot_size の個別化、取引手数料・スリッページのより現実的な見積もり反映、AI モデルの逐次評価・キャッシュ化、より細かな監視メトリクス保存等を検討中。