# Keep a Changelog
すべての重要な変更点を日付順に記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-09
初回公開リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env および環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索し、自動で .env / .env.local を読み込む。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パースは export 構文・クォート・インラインコメント・エスケープに対応。
    - .env ファイル読み込み時、OS 環境変数は protected として上書きを制御。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目を取得し未設定時は ValueError を送出。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証を実装。
    - DB/ファイルパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）を Path 型で提供。
    - Paper Trading 固有設定（PAPER_FILL_MODE）や監視パラメータ（CPU/MEM/DISK 閾値、KILL_FLAG など）を提供。

- ポートフォリオ構築ロジック (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコアが全てゼロの場合は等配分にフォールバックし警告を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター別集中を抑制するために候補からブロックする機能（既存ポジションの時価を元に判定）。"unknown" セクターはセクター上限の適用対象外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金の乗数を提供。未知レジームは警告を出して 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式をサポートし、単元株（lot) に丸めて発注株数を計算。aggregate cap（available_cash）に基づくスケールダウンと、端数の優先配分ロジックを実装。
    - cost_buffer による手数料・スリッページを保守的に見積もる機能を追加。

- リサーチ機能 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードを参照）。
    - 計算は DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時は None を返す扱い。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算。有効レコードが 3 件未満の場合は None を返す。
    - rank / factor_summary: ランキング（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの __all__ に主要 API をエクスポート。

- AI サブシステム (src/kabusys/ai/)
  - news_nlp.py
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメント（ai_score）を算出・ai_scores テーブルへ書き込み。
    - バッチサイズ、記事/文字数上限、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx）を実装。
    - API レスポンスの堅牢なバリデーション（JSON抽出、results 配列確認、コード・スコア検証）を実装し、異常時は当該チャンクをスキップして続行。
    - DuckDB executemany の制約（空リスト不可）を考慮した安全な DELETE/INSERT ロジックを実装。
  - regime_detector.py
    - ETF 1321（日経連動）MA200 乖離とマクロニュース LLM 評価を重み付けして市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードベース、LLM 評価は再試行/フォールバックを実装。API 失敗時は macro_sentiment = 0.0 として続行。
  - ai パッケージの __all__ に score_news をエクスポート。

- 監視データ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite 接続に対してシステムステータス、トレードログ、ポジション、リスクログ等のテーブルとインデックスを冪等的に作成するスクリプトを実装。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- OpenAI API キーは関数引数で渡すか環境変数 OPENAI_API_KEY を利用すること。未設定時は ValueError を送出して明示的に失敗することで誤動作を防止。

### Notes / Known limitations / TODO
- news_nlp と regime_detector は外部 API（OpenAI）を使用するため、実行には有効な API キーとネットワーク接続が必要。API エラー時はフォールバック/スキップでフェイルセーフ化しているが、精度低下が起こり得る。
- .env 読み込みはプロジェクトルートの検出に依存するため、配布後や特殊なデプロイ環境でルートが見つからない場合は自動読み込みをスキップする（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト時に制御可能）。
- position_sizing.calc_position_sizes:
  - lot_size は現状グローバルで固定（デフォルト 100）。将来は銘柄別 lot_map を受け取る拡張を予定（TODO コメントあり）。
  - price が欠損（0.0）の場合は一部ロジックで過少見積りの懸念がある（TODO コメントあり）。
- DuckDB executemany の空パラメータ制約を考慮している（空リストで実行しない保護）。
- news_nlp の JSON 抽出は堅牢化しているが、LLM の出力形式変化には注意が必要（余計なテキストが混ざる場合は最外の {} を抽出する試みを行う）。
- factor_research / feature_exploration の計算は prices_daily / raw_financials テーブルのデータ品質に依存する。データ不足時は None を返す挙動。

### Backwards incompatible changes
- なし（初回リリース）。

---

開発者向けの README やドキュメント（PortfolioConstruction.md, StrategyModel.md 等）で参照している運用方針・設計ノートに基づく実装が多数含まれます。実運用前に .env 設定、DuckDB/SQLite のスキーマ準備、OpenAI API キーの確認を行ってください。