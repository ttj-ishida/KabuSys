# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]

### 追加予定 / 注意点（推測）
- .env 読み込みの拡張（現在はプロジェクトルートの .env / .env.local を自動で読み込み）。テスト用に自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD が用意済み。
- 単体テスト向けに OpenAI 呼び出し部分をモックできるよう関数分離済み（news_nlp._call_openai_api / regime_detector._call_openai_api）。今後はテストケース追加が想定される。
- 将来的な拡張点として銘柄ごとの lot_size を持つ設計（stocks マスタへの lot_size 追加）や価格フォールバックロジックの実装が考慮されている（TODO コメントあり）。

---

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンとして `__version__ = "0.1.0"` を定義。
  - パッケージ公開エクスポート: data, strategy, execution, monitoring などのトップレベル定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル（および .env.local）または環境変数から設定を読み込む自動ロード実装。プロジェクトルートは .git または pyproject.toml を探索して決定。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応）。
  - 環境変数の既存値保護（protected set）と .env.local による上書き挙動をサポート。
  - 設定アクセスラッパー Settings を提供（プロパティ経由で各種設定にアクセス）。
    - J-Quants / kabu API / LINE API / DB パス（DuckDB/SQLite） / Paper Trading 用の設定 / 監視用ファイルパス / リソース閾値 / 環境（development/paper_trading/live） / ログレベル 等。
  - 必須環境変数未設定時には _require() が ValueError を投げる仕組みを用意。
  - 入力検証: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の許容値チェック。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定: select_candidates — score 降順、同点は signal_rank 昇順でタイブレーク。
  - 重み計算:
    - calc_equal_weights — 等金額配分（1/N）。
    - calc_score_weights — スコア比率で正規化。全銘柄スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - リスク調整:
    - apply_sector_cap — セクター別既存保有比率を計算し、指定の最大セクター比率を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。当日売却予定銘柄を除外してエクスポージャーを計算可能。
    - calc_regime_multiplier — 市場レジーム（bull/neutral/bear）に応じた投下資金倍率（1.0 / 0.7 / 0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - ポジションサイズ計算:
    - calc_position_sizes — risk_based / equal / score の allocation_method をサポート。単元株（lot_size）丸め、per-stock 上限、aggregate 上限（available_cash）に対するスケールダウン、cost_buffer による保守的見積り、端数配分のための remainder ソートロジックなどを実装。
    - risk_based モード: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく計算。
    - aggregate cap 超過時のスケールダウンと lot_size 単位での追加配分の実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - calc_momentum — 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を DuckDB の prices_daily テーブルから計算。ウィンドウ内データ不足時の None ハンドリング。
  - calc_volatility — 20日 ATR（true range 定義に基づく）・相対 ATR（atr_pct）・20日平均売買代金・出来高比（volume_ratio）を計算。NULL の伝播を制御して正しいカウントを行う実装。
  - calc_value — raw_financials から target_date 以前の最新財務データを取得し PER（EPS が 0/NULL の場合は None）および ROE を計算。
  - calc_forward_returns — 複数ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括 SQL で取得。horizons の妥当性チェックあり。
  - calc_ic / rank / factor_summary — Spearman（ランク相関）による IC 計算（同順位は平均ランク）、rank 関数（同順位は平均ランク、丸めにより ties 検出の安定化）、および基本統計量（count/mean/std/min/max/median）を提供。
  - DuckDB を直接利用する SQL + Python 実装により外部ライブラリへの依存を最小化。

- AI（OpenAI）連携（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols からタイムウィンドウ（前日15:00 JST〜当日08:30 JST に対応する UTC 範囲）を集め、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄/API 呼び出し）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の存在、score の数値化、スコアのクリップ）を行い、ai_scores テーブルへ置換的に書き込み（DELETE → INSERT）。部分失敗時に他銘柄の既存スコアを保護する設計。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - テスト向けに API 呼び出しを差し替え可能（_call_openai_api をモック）。
  - レジーム判定（regime_detector.py）
    - ETF 1321 の ma200 乖離（70% 重み）とマクロニュース LLM センチメント（30% 重み）を合成して日次で regime_score を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュースはタイトルにマクロキーワードを含むものを抽出（最大件数あり）。API 失敗時は macro_sentiment=0.0 をフォールバックし処理継続。
    - レジーム判定閾値により 'bull' / 'neutral' / 'bear' を決定。
    - OpenAI 呼び出し部は news_nlp とは別実装で分離（モジュール結合回避）。
    - API キー解決/未設定時の ValueError を実装。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた MonitoringDB 初期化機能を提供（冪等なテーブル作成）。
  - system_status / trade_logs / positions / risk_logs などのテーブルと必要なインデックスを作成。

- パッケージ初期エクスポート
  - kabusys.portfolio、kabusys.research、kabusys.ai など主要 API を __all__ で公開。

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

### Security
- OpenAI API キーは明示的に引数または環境変数から取得し、未設定時に明確なエラーを返すことで誤ったデフォルト挙動を防止。

### Performance
- DuckDB を活用してファクター計算／リサーチ処理を SQL で効率化。
- ファクター等の計算は窓幅に基づいてスキャン範囲を限定（パフォーマンスチューニングのためのカレンダーバッファを使用）。

### Documentation / Design notes
- ルックアヘッドバイアス回避のため、datetime.today()/date.today() を参照しない設計（関数は target_date を受け取る）。
- OpenAI 呼び出しのリトライ戦略、JSON mode の利用、レスポンス検証、部分失敗時の DB 書込み保護などフェイルセーフ設計を採用。
- 単体テストの容易さを考慮して OpenAI 呼び出しを差し替え可能にしている点を明記。

### Known issues / TODO（コード内コメントより推測）
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされ、想定よりセクターブロックが緩くなる可能性あり。将来的に前日終値や取得原価でフォールバックする検討が必要。
- position_sizing: lot_size を全銘柄共通で扱っているため、銘柄ごとの単元対応を行う場合は拡張が必要（TODO コメントあり）。
- DuckDB executemany の空リストバインドの制約対応（news_nlp で考慮済み）。
- Unknown regime / 未定義値はフォールバックするが、監視・アラート等で通知する仕組みが将来必要。

---

メジャー/マイナー/パッチの規則に従い、今後の変更はこの形式で追記してください。