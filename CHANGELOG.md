# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本リポジトリの初期公開バージョンは 0.1.0 です。

## [0.1.0] - 2026-04-01

### Added
- パッケージ基盤
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
  - パッケージの公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロード順序: OS環境変数 > .env.local（override=True）> .env（override=False）。
    - OS 環境変数を保護するため保護セットを導入（既存の OS 環境変数は上書きしない）。
    - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト向け）。
  - .env パーサ `_parse_env_line` を実装し、以下をサポート:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート値、バックスラッシュによるエスケープ、インラインコメントの扱い（クォートあり/なしで異なるルール）。
  - `Settings` クラスを実装し、プロパティで型変換・バリデーションを提供:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（KABUSYS_ENV）/ログレベルなど。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェックを実装。
    - 必須項目未設定時に明示的なエラーを投げる `_require()` を提供（例: `JQUANTS_REFRESH_TOKEN`、`SLACK_BOT_TOKEN` 等）。
    - デフォルトのデータベースパス: `data/kabusys.duckdb`、監視DB: `data/monitoring.db` など。

- ニュース NLP（AI）モジュール
  - `kabusys.ai.news_nlp` を追加
    - raw_news と news_symbols を集約して、銘柄毎に OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出し `ai_scores` に書き込む処理を実装。
    - 処理の流れ: タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）→ 銘柄ごと記事集約（最大記事数、文字数でトリム）→ バッチ（最大 20 銘柄）で API 呼び出し → レスポンスバリデーション → ±1.0 にクリップ → DuckDB へ置換保存（DELETE → INSERT）。
    - バッチング、文字数トリム、最大記事数、JSON Mode 応答の厳格検証を実装。
    - リトライ/バックオフ: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数）を実装。その他のエラーはスキップして継続（フォールセーフ）。
    - レスポンスバリデーションにより未知コードの無視、数値検証、JSON パース補正（外側の余計なテキストから最外の {} を抽出）を行う。
    - DuckDB の executemany の制約に配慮し、空パラメータ時の呼び出しを回避。

  - `kabusys.ai.regime_detector` を追加
    - 市場レジーム（'bull' / 'neutral' / 'bear'）判定ロジックを実装。
    - 指標: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してスコア化。
      - ma200_ratio のスケーリングとクリップ、しきい値でラベル付け（BULL/BEAR/NEUTRAL）。
    - raw_news からマクロキーワードで記事タイトルを抽出し（最大 20 件）、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API 呼び出しのリトライ・バックオフ・5xx 判定、失敗時は macro_sentiment = 0.0 として継続（フォールセーフ）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止のため内部で datetime.today() を参照せず、必ず明示的な target_date を使用する設計。

  - `kabusys.ai.__init__` で `score_news` を公開。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を追加:
      - `calc_momentum(conn, target_date)` : 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - `calc_volatility(conn, target_date)` : 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
      - `calc_value(conn, target_date)` : PER（EPS 有効時）、ROE（raw_financials から最新財務を取得）。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。
    - 全関数とも prices_daily / raw_financials のみ参照し、発注系 API を呼ばない設計。
  - `kabusys.research.feature_exploration`
    - 特徴量探索ユーティリティを追加:
      - `calc_forward_returns(conn, target_date, horizons)` : 将来リターン（デフォルト [1,5,21]）を計算。horizons のバリデーションあり。
      - `calc_ic(factor_records, forward_records, factor_col, return_col)` : スピアマンのランク相関（IC）計算（有効レコード 3 件未満で None）。
      - `rank(values)` : 同順位を平均ランクで扱うランク付け（丸めで ties の検出精度向上）。
      - `factor_summary(records, columns)` : count/mean/std/min/max/median を算出する統計サマリー。
  - `kabusys.research.__init__` で主要関数と zscore_normalize をエクスポート。

- データ基盤（Data）モジュール
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理 API（J-Quants 連携）の夜間バッチ更新ロジックを実装。
      - カレンダーの差分取得（lookahead/backfill を考慮）→ `market_calendar` へ冪等保存。
      - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。
      - DB 未登録日のフォールバックは曜日ベース（土日非営業）を採用し、DB 登録値を優先。
      - 最大探索範囲・健全性チェック（future date の上限）を導入。
  - `kabusys.data.pipeline`
    - ETL パイプライン用の設計とユーティリティを実装。
    - `ETLResult` dataclass を導入（取得数・保存数・品質チェック結果・エラーの集約）。
    - 差分取得、バックフィル、品質チェックを想定した設計方針をコメントで記載。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

### Security
- OpenAI API キーや各種シークレットは environment から取得する設計。必須設定がない場合は明示的に ValueError を発生させる（安全な失敗）。

### Design / Reliability notes
- ルックアヘッドバイアス防止: AI スコアリング・レジーム判定等の関数は内部で現在時刻を参照せず、必ず外部から与えた target_date の過去データのみを使用する設計。
- フォールセーフ: OpenAI API 失敗時はスコアを中立（0.0）にフォールバックするなど、例外を上位に伝播させず継続可能な挙動を優先。
- DB 書き込みは冪等性を考慮（DELETE→INSERT、ON CONFLICT 想定等）し部分失敗時に既存データの保護を行う。

### Known limitations
- 一部の機能（例: strategy / execution / monitoring 内部実装の詳細）は本リリース段階では未掲載（あるいは未実装）であり、将来追加予定。
- OpenAI 呼び出しは gpt-4o-mini を想定しているが、SDK 互換性やレスポンスフォーマットの変化に注意が必要。
- DuckDB のバージョン依存（executemany の空配列取り扱い等）に配慮した実装を行っているが、運用環境の DuckDB バージョンでの動作確認を推奨。

### Fixed
- 初版のため該当なし。

## Unreleased
- (なし)

---

注意: 本 CHANGELOG はリポジトリ内のソースコードから実装・設計意図を推測して作成しています。実際の変更履歴やリリースノートとして利用する際は、コミット履歴やリリースポリシーに基づく追記・修正を行ってください。