# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠します。

未リリースの変更は Unreleased に記載します。初回公開バージョンは 0.1.0 です。

## [Unreleased]

（現時点ではなし）

---

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開します。

### Added
- パッケージメタ情報
  - kabusys パッケージのバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - パッケージの主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 環境変数・設定管理
  - 環境変数と .env ファイルの扱いを提供する設定モジュール（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を起点に探索して自動的に .env/.env.local を読み込む仕組みを実装（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は .env の値を上書き（override）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動読み込みを無効化可能（テスト用途）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント扱い等に対応。
    - 設定オブジェクト Settings を提供。主要な設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
      - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
      - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU/MEMORY/DISK 閾値（デフォルト値を設定）
      - KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL（DEBUG|INFO|...）
    - 未設定の必須変数取得時は ValueError を送出する（明確なエラーメッセージ）。

- ポートフォリオ構築ユーティリティ（メモリ演算の純粋関数群）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択（同スコアは signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター別時価を計算し、指定の最大セクター比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし WARNING を出力。
    - 内部コメントで price 欠損時の挙動や将来的な拡張（前日終値等へのフォールバック）を明示。
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method により "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率と損切り幅から目標株数を算出。
    - equal/score: weight に従い allocation を算出、lot_size（単元）で丸め。
    - per-position 上限（max_position_pct）、aggregate cap（available_cash）、cost_buffer（手数料・スリッページ見積り）に対応。
    - aggregate cap 超過時にはスケーリングし、端数は lot_size 単位で再配分するアルゴリズムを実装。
    - 将来的な拡張点（銘柄別 lot_size の導入）を TODO コメントで記載。

- リサーチ（DuckDB ベースのファクター計算）
  - research.factor_research
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER, ROE を算出（EPS が 0/欠損時は None）。
    - SQL ウェア句・ウィンドウ関数を用いて効率的に計算。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位を平均ランクにするランク化ユーティリティ（round(v,12) による丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポート。

- AI 関連機能（OpenAI を用いた NLP / レジーム判定）
  - ai.news_nlp
    - raw_news テーブルのニュースを OpenAI（gpt-4o-mini）へ送りセンチメントを銘柄ごとに算出し ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウは JST 基準で前日 15:00 〜 当日 08:30（UTC に変換して DB 検索）を採用。calc_news_window を提供。
    - 1 銘柄あたり最大記事数・文字数（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）でプロンプト長を制御。
    - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信。JSON Mode（response_format）を利用して厳密な構造を期待。
    - リトライポリシー: 429/ネットワーク/タイムアウト/5xx をエクスポネンシャルバックオフでリトライ（最大回数制限あり）。その他のエラーはリトライしない（フェイルセーフでスキップ）。
    - レスポンスバリデーションを厳密に行い、未知コードや非数値スコアは無視。スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT することで既存スコアを保護。DuckDB executemany に対する空パラメータ問題に対処。
    - OPENAI_API_KEY が未設定の場合、score_news は ValueError を送出。
  - ai.regime_detector
    - ETF 1321 の ma200 乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して market_regime を日次判定する score_regime を実装。
    - マクロニュース抽出はマクロキーワードリストによるフィルタ。タイトルを最大件数まで取得して LLM に投げる。
    - LLM の失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。API キー未設定時は ValueError。
    - レジームスコア合成後、閾値により 'bull' / 'neutral' / 'bear' に分類。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
    - news_nlp と似た API 呼び出し実装だが、モジュール間でプライベート関数を共有しない設計。

- モニタリング DB（SQLite）
  - monitoring_db.init_monitoring_db により監視用テーブル群を作成（冪等）。
    - system_status: システム稼働状況ログ（cpu/memory/disk/process_ok 等）
    - trade_logs: 取引ログ（client_order_id, code, side, qty, price, state 等）
    - positions: 保有銘柄と数量・平均取得単価・最終更新時刻
    - risk_logs（ファイル内で続くスキーマ定義あり）
    - インデックスを含むスキーマを作成するスクリプトを提供。

- パッケージエクスポート
  - ai.score_news をトップレベルでエクスポート（kabusys.ai.score_news）。
  - research.* の主要関数を __all__ で公開。

### Security / Safety
- ルックアヘッドバイアス対策: 各種日付参照処理（news/research/regime）で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計を採用。
- OpenAI 呼び出しに対してはタイムアウト・リトライ・フォールバックを実装し、API 障害がシステム全体に波及しないように設計。
- .env 自動読み込み時に OS 環境変数を保護（protected set）して意図しない上書きを防止。

### Notes / Known limitations / TODO
- position_sizing: lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を受け取る設計へ拡張予定（TODO コメントあり）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積もられてブロックが外れる可能性。将来的に前日終値などのフォールバック価格を使う検討あり（TODO コメント）。
- DuckDB executemany の実装上の制約により、空リストの executemany 呼び出しを避けるためのガードを追加している。
- news_nlp / regime_detector ともに OpenAI SDK の将来の変更に備え、status_code の取得などで堅牢性を考慮しているが、SDK の大幅な変更があった場合は調整が必要。

### Fixed
- （初回リリースのため過去修正はなし。実装上の堅牢化・入力検証・例外処理を多く含む。）

---

開発・運用に関するお問い合わせやバグ報告は issue を作成してください。