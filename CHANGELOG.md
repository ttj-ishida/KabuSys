# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠します。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買支援ライブラリ「KabuSys」の基本機能を実装しました。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージの公開 API を設定（data, strategy, execution, monitoring を公開）。
  - バージョン: __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動読み込みの優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート（テスト用）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWDに依存しない）。
  - .env パーサー強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォートのエスケープ解釈対応
    - インラインコメント処理（先頭にスペース／タブがある場合の '#' をコメントとして扱う等）
  - Settings クラスを提供し、アプリで使用する主要設定をプロパティで取得可能:
    - J-Quants / kabuステーション / Slack / DB パス等の設定取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証。
    - duckdb/sqlite のデフォルトパス設定。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive）。
    - バッチ処理: 最大 20 銘柄/API コール（_BATCH_SIZE=20）。
    - 1銘柄あたりのリミッタ: 最大記事数、最大文字数（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode を利用して厳密な JSON 応答を期待。応答の復元（前後の余計なテキストが混入する場合に {} を抽出）やバリデーションを実装。
    - スコアは ±1.0 にクリップ。
    - リトライ / バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数 _MAX_RETRIES=3）。
    - エラーハンドリング: API 呼び出しが失敗した銘柄はスキップし、部分失敗時に既存スコアを保護するために DELETE→INSERT をコード単位で実行。
    - test で差し替え可能な内部 _call_openai_api によりユニットテストを容易化。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - LLM モデル: gpt-4o-mini を使用。
    - マクロキーワードリストを定義し raw_news のタイトルをフィルタ（最大 _MAX_MACRO_ARTICLES=20）。
    - マクロスコア取得時のリトライ/エラーハンドリング（RateLimit/接続エラー/タイムアウト/5xx を考慮、最大リトライ _MAX_RETRIES=3、指数バックオフ）。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフに処理継続。
    - レジーム合成時にスコアをクリップし閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理用ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS=60）や先読み・バックフィル・健全性チェックを実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して market_calendar を更新、バックフィル _BACKFILL_DAYS=7、lookahead デフォルト 90 日）。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETL の公開インターフェース ETLResult を実装（kabusys.data.etl で再エクスポート）。
    - 差分更新、保存（jquants_client 経由、idempotent 保存）、品質チェックフローに沿った設計。
    - ETLResult dataclass により取得件数・保存件数・品質問題・エラー一覧を集約、has_errors / has_quality_errors / to_dict を提供。
    - デフォルトバックフィル日数（_DEFAULT_BACKFILL_DAYS=3）や最小データ開始日 _MIN_DATA_DATE の定義。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。

- Research（研究）モジュール (kabusys.research)
  - factor_research
    - モメンタム (1M/3M/6M)、200日移動平均乖離（ma200_dev）、ATR・流動性指標（20日 ATR、平均売買代金、出来高比率）等を DuckDB の SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 設計上、外部 API 呼び出しは行わず prices_daily / raw_financials のみ参照。
    - データ不足時の None 返却や結果を (date, code) キーの dict リストで返す。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）のリターンを LEAD() を使って一括取得。
    - IC（Information Coefficient）計算 (calc_ic): スピアマンのランク相関を実装（同順位は平均ランク）。
    - ランク関数 (rank) とファクター統計サマリー (factor_summary) を実装（count/mean/std/min/max/median）。
    - pandas 等に依存せず、標準ライブラリ + DuckDB SQL で実装。

### 変更 (Changed)
- 設計方針や安全対策の明文化（各モジュールともにルックアヘッドバイアス回避のため date.today()/datetime.today() を参照しない設計や、DB 書き込み時の冪等性・部分失敗保護など）。
- OpenAI API 呼び出しは JSON mode を積極利用し、レスポンスパースの堅牢化を行った（余計な前後テキスト復元ロジックなど）。

### 修正 (Fixed)
- （初回リリースにつき過去のバグ修正履歴は無し。各所にログ記録・例外処理・ROLLBACK 保護を追加して安定性を高めていることを明記。）

### 注意事項 / 設計上のポイント
- OpenAI API キーは関数引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する。
- DuckDB を主要な分析 DB として利用。DuckDB の executemany の制約（空リスト不可）を考慮した実装を行っている。
- API 呼び出し失敗時は可能な限りフェイルセーフ（スキップ・デフォルト値採用）で継続する設計。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後動作環境では環境変数での設定を推奨。
- 一部内部関数（例: _call_openai_api）はテスト用に差し替え可能（unittest.mock.patch）な設計。

---

以上が初回リリース（0.1.0）の主要な変更点と機能概要です。今後のリリースでは API の追加・改善、モデル・プロンプト調整、監視／実行部分（execution, monitoring）や戦略（strategy）の具体実装強化を予定しています。