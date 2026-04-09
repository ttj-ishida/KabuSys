# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース日付はコミット時点から推測して記載しています。
- 内容は提供されたコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - パッケージの公開エクスポート設定（data, strategy, execution, monitoring 等）。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（__file__ 起点で親ディレクトリを探索）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - OS に既にある環境変数は protected として上書きを保護。
  - .env パーサ実装（export プレフィックス、クォートやエスケープ、行内コメント処理に対応）。
  - 必須値取得用ユーティリティ `_require()` と各種設定プロパティを提供:
    - J-Quants・kabuステーション・LINE API・DBパス・監視閾値・システム環境（KABUSYS_ENV, LOG_LEVEL）等。
    - バリデーション（有効な env 値・log level・PAPER_FILL_MODE の許容値チェック）を実装。
  - 設定の Path 型返却やデフォルト値、真偽値変換（例: KILL_FLAG_CLEAR_ON_START）をサポート。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N 件抽出。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING ログ出力。
  - risk_adjustment
    - apply_sector_cap: セクター毎の既存保有比率が閾値を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を計算。未知レジームはフォールバックで 1.0。
  - position_sizing
    - calc_position_sizes: 各種配分方式（risk_based, equal, score）に対応した発注株数計算を実装。
      - risk_based: 許容リスク率・損切り率から基本株数を算出し単元（lot_size）で丸める。
      - equal/score: ウェイトと金額上限（max_utilization）に基づく算出。
      - per-position 上限（max_position_pct）や aggregate cap（available_cash）を尊重し、available_cash 超過時はスケールダウンして残差を lot 単位で配分。
      - cost_buffer によりスリッページ/手数料を保守的に見積もり。
      - lot_size は現状グローバル定義（デフォルト 100）。将来的に銘柄別 lot_map へ拡張する旨の TODO コメントを追加。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr/close）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う設計。
    - calc_value: raw_financials から直近財務データを結合して PER, ROE を算出（EPS が 0/NULL の場合は PER を None）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials テーブルのみ参照。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ。丸め（round(...,12)）による ties の安定検出。
    - factor_summary: count, mean, std, min, max, median を計算する統計サマリ。
  - research/__init__.py で zscore_normalize（kabusys.data.stats）などをエクスポート。

- AI 機能（src/kabusys/ai/*）
  - news_nlp
    - calc_news_window: ニュース収集ウィンドウ（日次、JSTベース→UTC変換）を提供。ルックアヘッドバイアス対策で datetime.today() を参照しない設計。
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へ最大 20 銘柄ずつバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
      - 入力テキストは銘柄ごとに最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - API の 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ）。
      - OpenAI の JSON Mode を利用し、レスポンスを厳密にバリデートしてスコアを ±1.0 にクリップ。
      - DuckDB への書き込みは冪等（該当 date/code の DELETE → INSERT）で実装。DuckDB executemany の空リスト制約に対応したガードを追加。
      - API キー未指定時は ValueError を送出。
      - テスト容易性のため _call_openai_api を差し替え可能。
  - regime_detector
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込む機能。
      - ma200_ratio の計算では target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立（1.0）でフォールバックし WARNING を出力。
      - マクロニュースはキーワードベースでタイトルを抽出（最大件数制限）。記事が無い場合は macro_sentiment = 0.0 で継続。
      - LLM 呼び出しはリトライ付きで行い、最終的な regime_score を [-1,1] にクリップした上でラベル付け（bull/neutral/bear）。
      - API キー未指定時は ValueError を送出。
      - news_nlp.calc_news_window を再利用して時間窓を計算。
      - LLM 呼び出し実装は news_nlp と独立（内部プライベート関数を共有しない設計）。
  - ai/__init__.py で score_news をエクスポート。

- 監視永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を使った監視ログ永続化層を実装（読み書きのみ、ビジネスロジックなし）。
  - init_monitoring_db により system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等的に作成する SQL スクリプトを実装。

### Fixed
- （初回リリース）なし

### Changed
- （初回リリース）なし

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キー未設定の場合に早期に ValueError を投げることで誤った挙動を防止。

### Notes / Known issues / TODO
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張がコメントで残されている。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、セクターエクスポージャーが過少見積りされうる。将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO コメントあり。
- news_nlp / regime_detector:
  - LLM レスポンスの不定形出力に備えたパーシングを行うが、完全な堅牢性は LLM の応答品質に依存する。
- DuckDB の executemany に関する互換性問題に対して防御実装あり（空リストを渡さないガード）。
- 多くの関数は「純粋関数」設計（副作用無し）を志向。ただし AI モジュールや DB 書き込みは副作用を伴う実装。

## 依存ライブラリ（主要）
- duckdb
- openai

（注）上記はコードからの推測に基づく CHANGELOG です。実際のリリース日やリリースノートはプロジェクト運用の記録に合わせて調整してください。