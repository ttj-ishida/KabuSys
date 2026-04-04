# Changelog

すべての注目する変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。<br>
<https://keepachangelog.com/ja/1.0.0/>

## [0.1.0] - 2026-04-04

### Added
- パッケージ基盤
  - 初期バージョンとして kabusys パッケージを追加。パッケージバージョンは `0.1.0`。
  - パッケージ公開 API（`__all__`）に data, strategy, execution, monitoring を設定。

- 環境設定 / 管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` の行パーサーは `export KEY=val` 形式、シングル/ダブルクォートのエスケープ、行内コメントの扱い等に対応。
    - `.env` 読み込み時に OS 環境変数を保護するための protected キーセットをサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能:
    - J-Quants / kabu API / LINE Messaging / DB パス（DuckDB/SQLite）/ 監視 PID・フラグファイルパス・閾値 / 環境 (development/paper_trading/live) / ログレベル 等をサポート。
    - 必須環境変数未設定時は明示的な例外（ValueError）を発生させる `_require` を使用。
    - `env` / `log_level` は許容値を検証して不正値で例外を発する。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価を行い `ai_scores` テーブルへ書き込む `score_news` 関数を追加。
    - 処理特徴:
      - JST 基準のニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を `calc_news_window` で提供。
      - 1銘柄あたり最大記事数 / 最大文字数でトリムしてトークン肥大化を緩和。
      - 最大 20 銘柄をバッチ処理（_BATCH_SIZE）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
      - レスポンスは厳格にバリデート（JSON 抽出、"results" 配列、code と score の型検査、未知コードは無視、数値クリップ）。
      - DB への書き込みは冪等性確保のため、スコアを取得した銘柄コードのみ `DELETE` → `INSERT`（トランザクション）で置換。部分失敗時に他コードの既存スコアを保護。
      - テスト容易性のため OpenAI 呼び出し箇所は `_call_openai_api` を通しモック差し替え可能。
      - API キー未設定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を追加。
    - 処理特徴:
      - prices_daily から 1321 の終値を取得して MA200 乖離を算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
      - raw_news をマクロキーワードでフィルタしてタイトルを抽出、OpenAI でマクロセンチメントを評価（記事なし時は LLM 呼び出しをスキップして 0.0）。
      - API 呼び出しはリトライ/バックオフ対応、5xx はリトライ対象、その他はフェイルセーフで macro_sentiment=0.0 にフォールバック。
      - レジームスコアはクリップした上でしきい値に基づきラベル付けし、`market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みエラーを伝播。
      - OpenAI 呼び出し実装は news_nlp と独立させてモジュール結合を低減、テストで差し替え可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）に対する営業日判定・前後営業日取得・期間内営業日列挙などのユーティリティを追加:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - market_calendar が存在しない場合は曜日ベース（土日除外）のフォールバックを採用。
      - DB に NULL が混入した場合に警告を出し、フォールバックを行う堅牢性。
      - 夜間バッチ処理 calendar_update_job を実装（J-Quants API から差分取得 → 保存 / バックフィル / 健全性チェック）。
      - 最大探索範囲 (_MAX_SEARCH_DAYS) やバックフィル日数、先読み日数等の定数を適切に定義。
    - jquants_client との連携を想定（fetch/save を呼び出す）。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表すデータクラス `ETLResult` を実装し、外部へ公開（kabusys.data.etl で再エクスポート）。
      - ETL 実行のメタ情報（取得数・保存数・品質チェック結果・エラー等）を格納、辞書変換ユーティリティを提供。
      - 品質チェック（quality モジュール）で検出された重大度の判定ロジックを保持。
    - パイプライン設計方針として差分更新・バックフィル・idempotent 保存（ON CONFLICT）・品質チェックの継続処理を定義。
    - 内部ユーティリティでテーブル存在チェック・最大日付取得などを準備（実装の一部を含む）。

- リサーチ / ファクター解析 (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - Momentum / Volatility / Value などの定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）、データ不足時は None を返す。
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - calc_value: raw_financials から直近の EPS/ROE を取得して PER/ROE を算出（EPS が 0/欠損時は None）。PBR や配当利回りは未実装。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に集計。ルックアヘッドバイアス防止の方針に準拠。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（指定ホライズンの将来終値から fwd_xd を算出、存在しない場合は None）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の順位相関を実装、データ不足時は None）。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算する関数を実装。
    - 実装は外部依存を最小化（標準ライブラリ中心）し、DuckDB のみ参照する設計。

### Changed
- （初リリースのため該当なし）

### Deprecated
- （初リリースのため該当なし）

### Removed
- （初リリースのため該当なし）

### Fixed
- （初リリースのため該当なし）

### Security
- （初リリースのため該当なし）

---

注記:
- 多くの API 呼び出し箇所（OpenAI / J-Quants）で堅牢性のためのリトライ・フェイルセーフが組み込まれており、テスト容易性のために _call_openai_api 等をモック差し替え可能にしています。
- 時刻関連の実装は「ルックアヘッドバイアス防止」のため global な datetime.today()/date.today() の直接参照を避け、関数引数で基準日を受け取る設計になっています。
- DB 書き込みは冪等性を意識した設計（DELETE→INSERT、ON CONFLICT 想定、トランザクション）です。