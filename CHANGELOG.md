# Changelog

すべての変更は Keep a Changelog のガイドラインに従い、逆順（新しいものが上）で記載します。  
日付・内容はソースコードから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。主要機能を実装しました（環境設定、ポートフォリオ構築、リサーチ、AI ベースのニュース/レジーム判定、監視用 DB ユーティリティ等）。

### Added
- 基本パッケージメタデータ
  - パッケージ初期バージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（配布後の動作を意識）。
    - .env パーサは export 形式、クォートやエスケープ、インラインコメント等に対応。
    - OS 起源の環境変数を保護するため protected set を用いた上書き制御。
  - 必須値取得のヘルパー `_require`（設定未存在時は ValueError）。
  - 各種設定プロパティを実装（J-Quants / kabuステーション / LINE / DBパス / Paper Trading / 監視閾値 / システム環境等）。
    - Paper Trading の fill モード検証（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL（DEBUG/INFO/...）の検証。
    - デフォルトパス（DuckDB/SQLite 等）とフル展開（expanduser）をサポート。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄選定・重み計算（純粋関数群）
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分 (1/N) を計算。
    - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - リスク調整・セクター上限
    - apply_sector_cap: 現在ポジションからセクターごとのエクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。売却予定の銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対応する投入資金乗数を返す（未知レジームは 1.0 にフォールバック、警告ログ）。
  - 株数決定・リスク管理・単元丸め
    - calc_position_sizes:
      - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
      - risk_based: 許容リスク率と損切り幅から目標株数を算出し単元（lot_size）で丸め。
      - equal/score: ポートフォリオ配分から per-position 上限や aggregate cap を適用。
      - 単元丸め、価格欠損時のスキップ、max_position_pct 制約、cost_buffer（スリッページ/手数料見積り）を考慮した保守的な集計。
      - aggregate cap 超過時はスケールダウンを行い、残差を lot_size 単位で公平に配分するアルゴリズムを実装。

- リサーチ / 特徴量 (src/kabusys/research/*)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の window 関数を利用）。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。必要行数に満たない場合は None を返す。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損時は None）と ROE を算出。最新の財務レコード取得に ROW_NUMBER を使用。
    - いずれも DuckDB 接続を受け取り、外部 API に依存しない純粋な計算を行う設計。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターン（LEAD を使ってまとめて取得）。horizons のバリデーション（正の整数、<=252）。
    - calc_ic: ファクターと将来リターンを code で結合し、スピアマンのランク相関（ρ）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを割り当てるランク関数（浮動小数丸めで ties 判定を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。標準ライブラリのみで実装。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング機能。
    - calc_news_window: target_date に対するニュース検索ウィンドウ（JST→UTC 変換）を計算。
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、最大バッチ _BATCH_SIZE (=20) で LLM に投げてスコアを計算、ai_scores テーブルへ書き込み（DELETE→INSERT の冪等的置換）。
    - 設計上の注意点:
      - トークン肥大化対策（1 銘柄あたり max 記事数 / max 文字数でトリム）。
      - API レスポンスのバリデーション（JSON 抽出、results キー、型検査、未知コードの無視、数値チェック）。
      - スコアは ±1.0 にクリップ。
      - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ、それ以外は失敗をログ出力してスキップ（フェイルセーフ）。
      - OpenAI API キーの解決は引数優先、なければ環境変数 OPENAI_API_KEY。未設定時は ValueError。
      - DuckDB executemany の制約（空リスト不可）を回避する実装。

- AI / レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - _calc_ma200_ratio: look-ahead を避けるため target_date 未満のデータのみを使用。データ不足時は中立 (1.0) にフォールバック。
    - _fetch_macro_news: タイトルベースでマクロキーワードに一致する記事を抽出（最大件数制限）。
    - _score_macro: LLM 呼び出しはリトライ制御とエラー時のフォールバック (0.0) を実装。
    - score_regime: レジームスコアの合成ロジック、閾値によるラベリング、market_regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは news_nlp と別実装にしてモジュール依存を低減。

- AI パッケージ初期公開 API
  - src/kabusys/ai/__init__.py で score_news を公開。

- 監視用 DB 初期化ユーティリティ (src/kabusys/monitoring/monitoring_db.py)
  - SQLite での監視ログ永続化層の初期化関数 init_monitoring_db を追加。
  - system_status / trade_logs / positions / risk_logs 等のテーブル作成スクリプト（冪等）を実装。
  - インデックス作成を含む SQL スクリプト。

### Changed
- （該当なし — 初回リリースのため変更履歴はありません）

### Fixed
- （該当なし）

### Security
- .env 読み込みで OS 環境変数の上書きを防ぐ protected set を導入（設定のセーフガード）。
- OpenAI API キーは引数優先で受け取り、環境変数未設定時は明示的にエラーを出すことでキー漏れ・誤実行を防止。

### Notes / Implementation details
- DuckDB を利用する計算系関数は外部 API に依存せず、prices_daily/raw_financials/raw_news 等のテーブルのみ参照して動作する設計となっています（リサーチ機能の安全性と再現性を重視）。
- 時刻処理はルックアヘッドバイアスを避ける実装思想（関数に target_date を渡し、datetime.today()/date.today() を参照しない）を採用。
- OpenAI とのやり取りは JSON Mode を利用し厳密な構造を期待するが、実際の応答での前後付加テキストに備えたパースロジックも備えています。
- ロギングを随所に配置し、データ不足や異常系は警告/情報ログで検出できるようにしています。

---

今後のリリースでは、例えば以下のような改善が想定されます（未実装だがコード中に TODO/拡張意図あり）:
- 銘柄ごとの単元情報（lot_size）を stocks マスタから読み込む拡張。
- price 欠損時のフォールバック価格（前日終値や取得原価）の導入。
- AI モジュールのテスト容易化のための抽象化やインターフェース整理。
- 追加のファクター実装（PBR・配当利回りなど）。

変更履歴に関して補足や修正希望があればお知らせください。コードから推測したため、実際のコミットメッセージ・日付と差異がある可能性があります。