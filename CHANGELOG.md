# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。日付はリポジトリの現在の状態（コードベースから推測）に基づいています。

## [Unreleased]
- 今後のリリース向けの変更点はここに記載します。

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買・データ基盤・リサーチ・AI 支援スコアリングを含む基盤機能を実装。

### 追加 (Added)
- パッケージのエントリポイントとバージョン
  - kabusys パッケージを追加。バージョンを "0.1.0" として公開。
  - __all__ に data / strategy / execution / monitoring を公開。

- 設定管理 (.env / 環境変数)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト時に便利）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理。
  - 環境変数保護機能（読み込み時に既存 OS 環境変数を protected として上書きを防止）。
  - Settings クラスを実装し、J-Quants / kabuAPI / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供。
    - 必須キー取得時に未設定なら ValueError を送出する _require を実装。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/...）。

- AI モジュール（OpenAI を利用したニュースセンチメント・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信してセンチメントスコアを取得。
    - バッチサイズ、文字数上限、記事数上限などの肥大化対策:
      - _BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000。
    - JSON Mode (response_format={"type": "json_object"}) を想定した応答パースとバリデーションを実装。
    - リトライポリシー（429, ネットワーク断, タイムアウト, 5xx）をエクスポネンシャルバックオフで実装（最大リトライ回数＝3）。
    - スコアを ±1.0 にクリップ。
    - 書き込みは冪等性を考慮（DELETE → INSERT のトランザクション）し、DuckDB 0.10 の executemany の空リスト制約を回避するガードを実装。
    - target_date に対するニュースウィンドウ計算 calc_news_window(target_date) を実装（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - API キーを api_key 引数で注入可。テストのため _call_openai_api をモック可能に設計。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321（日経225 連動型）の直近 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定・保存。
    - マクロ記事の抽出はニュース NLP の calc_news_window とマクロキーワードを利用。
    - LLM 呼び出しは専用の _call_openai_api を使用（news_nlp とは実装を分離）。
    - フェイルセーフ: API 失敗やパース失敗時は macro_sentiment=0.0 を使用。
    - レジームスコアの閾値: bull if >= 0.2, bear if <= -0.2。DB への書き込みは冪等に実行（BEGIN/DELETE/INSERT/COMMIT）。

- Data / ETL / カレンダー管理
  - data.pipeline.ETLResult データクラスを追加（ETL の取得数・保存数・品質問題・エラーを管理）。
  - calendar_management モジュールを追加:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といったマーケットカレンダー関連ユーティリティを実装。
    - market_calendar が未取得の際は曜日ベース（平日）でフォールバックする設計。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants からカレンダーを差分取得して保存（バックフィル、健全性チェックあり）。
    - 最大探索日数やバックフィル日数などの定数で安全策を導入。
  - data.pipeline 内部ユーティリティ:
    - テーブル存在チェック、最大日付取得、取得範囲調整等のヘルパー関数を実装。
    - デフォルトの初回ロード開始日 (_MIN_DATA_DATE) や backfill の既定値を定義。

- Research（ファクター・特徴量探索）
  - research パッケージを追加し、以下を提供:
    - factor_research: calc_momentum, calc_value, calc_volatility を実装。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（200 行未満なら None）。
      - Volatility: 20 日 ATR（true_range の NULL 伝播に配慮）、相対 ATR、20 日平均売買代金、出来高比率。
      - Value: raw_financials から最新の EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損なら None）。
    - feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - zscore_normalize は data.stats から再エクスポート。
    - 設計上、DuckDB 接続を受け取り外部 API にアクセスしない点を明確化（研究用に安全）。

- その他ユーティリティ
  - data.etl で pipeline.ETLResult を再エクスポート（公開インターフェース）。

### 変更 (Changed)
- API 呼び出しに関する設計上の方針を明記
  - datetime.today() / date.today() をスコアリング処理内部で直接参照しない設計（ルックアヘッドバイアス防止）。すべて target_date を明示的に受け取る。
  - OpenAI クライアントは関数引数（api_key）で上書き可能にし、テスト容易性を確保。
  - news_nlp と regime_detector で OpenAI の呼び出し実装を分離し、モジュール間の結合を避ける設計に変更。

- DB 書き込みの冪等性と DuckDB の互換性対応
  - ai_scores / market_regime / market_calendar 等への書き込みは、既存行の DELETE → INSERT のパターンで冪等に実行。
  - DuckDB 0.10 の executemany が空リストを受け付けない点を考慮し、空パラメータ時には実行をスキップするガードを追加。

### 修正 (Fixed)
- OpenAI レスポンスパースの堅牢化
  - JSON Mode でも前後余計なテキストが混入する場合を想定して最外の {} を抽出して復元するロジックを追加。
  - レスポンスの validation を強化し、不正な要素（未知コード・非数値スコア・無限値）を無視するように修正。

- エラー時のフォールバック強化
  - LLM / API 呼び出しの失敗時に処理全体をクラッシュさせず、フェイルセーフ（macro_sentiment=0.0、スコアスキップ等）で継続するように改善。

### セキュリティ (Security)
- 環境変数の必須チェック（API キー等）で未設定時は ValueError を投げるため、秘密情報の存在確認が明示化。
- .env の自動読み込み時に OS 環境変数を保護する protected 機構を実装（意図しない上書きを防止）。

### 既知の制約 / 注意事項 (Known issues / Notes)
- DuckDB のバージョン依存の挙動（executemany の空リスト受け入れ可否など）に対する互換性対応を導入しているが、動作は使用する DuckDB バージョンに依存する可能性がある。
- OpenAI API の呼び出しは外部サービスに依存するため、API キーの提供とネットワーク環境が必要。
- 一部関数（例: _adjust_to_trading_day の続きを含む処理）はファイルスニペットの範囲で実装が継続していることが想定される（将来的な追加・改善予定）。

---

文書化はコードから推測して作成しています。実際のリリースノート作成時にはコミット履歴やリリース差分、実運用での変更点を参照のうえ、日付・項目の調整を行ってください。