# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
現在のリリース履歴は以下のとおりです。

すべての新規・既存の機能追加・設計方針についてはコード内の docstring / コメントを元に推測して記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基礎
  - kabusys パッケージ初期版を追加。バージョン __version__ = "0.1.0" を設定。パッケージ公開用の __all__ を定義（"data", "strategy", "execution", "monitoring"）。
- 設定管理 (kabusys.config)
  - .env ファイル・環境変数を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から解決するため、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用含む）。
  - .env パーサーを実装。以下をサポート/考慮:
    - 空行・コメント（#）の扱い、export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い（クォートあり/なしでの違い）。
    - ファイル読み込み失敗時には警告を発する。
    - override フラグと protected キーセットの導入により OS 環境変数の保護を実現。
  - Settings クラスを提供し、環境変数に依存する設定項目をプロパティで公開。
    - J-Quants、kabuステーション、Slack、DB（DuckDB / SQLite）やシステム設定（KABUSYS_ENV, LOG_LEVEL）についてのデフォルト値・必須判定を実装。
    - KABUSYS_ENV / LOG_LEVEL の許容値検証を実装（不正値で ValueError を送出）。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。
- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルからターゲット時間ウィンドウの記事を集約し、銘柄ごとに OpenAI (gpt-4o-mini) にバッチ送信して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算 calc_news_window を実装（JST 基準、UTC 変換で DB と比較）。
    - スコア取得処理 score_news を実装。主な特長:
      - 1チャンクあたり最大 _BATCH_SIZE（デフォルト 20）銘柄で送信。
      - 1銘柄あたりの記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
      - JSON Mode を利用したレスポンス検証・パース処理を実装。冗長テキスト混入時の補正（最外側の {} 抽出）を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx はエクスポネンシャルバックオフでリトライ、他のエラーはスキップ。
      - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の既存データ保護。DuckDB executemany の空リスト制約に対応。
      - テスト用に OpenAI 呼び出しをモックしやすい設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して（日次）市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロ記事フィルタリング（キーワードベース）・OpenAI 呼び出し・リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試み例外伝播。
    - ルックアヘッドバイアス対策のため、target_date 未満のデータのみを使用し datetime.today()/date.today() を参照しない設計。
- Research（因子計算・特徴探索）モジュール (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも DuckDB の prices_daily / raw_financials のみを参照し、本番 API にはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションを実装。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。サンプル不足や分散ゼロ時のハンドリングを実装。
    - rank: 同順位は平均ランクを採るランク変換を実装（float の丸めで ties の誤差を抑制）。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）を計算。
- Data プラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダー取得・営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベースのフォールバック（平日が営業日）を使用。
      - 最大探索範囲 _MAX_SEARCH_DAYS を定義し無限ループを防止。
    - calendar_update_job: J-Quants クライアントから差分取得して market_calendar テーブルを更新（バックフィルや健全性チェックを実施）。
  - pipeline / etl:
    - ETLResult データクラスを実装し ETL の統計・品質問題・エラーを集約して返却。
    - 差分更新やバックフィル方針、品質チェックの扱いに関する設計方針を実装（詳細は docstring）。
  - etl の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - jquants_client / quality など外部モジュールとの連携前提で設計（実装は別モジュールに委譲）。
- パッケージ公開インターフェース
  - ai と research の __init__.py で主要関数/ユーティリティを再エクスポートして使いやすくした（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去バグ修正履歴なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 環境変数の重要情報（OPENAI_API_KEY など）は Settings 経由で必須チェックを行い、未設定時は明確な例外を送出。自動 .env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini を想定しており、JSON Mode の返却整形に依存するためモデルや SDK の変更があった場合に互換性問題が生じる可能性があります。テスト時は _call_openai_api を patch してモック可能な設計にしています。
- DuckDB の executemany に対する空リストの扱い（バージョン依存）に注意し、空リスト送信を回避する実装を行っています。
- news_nlp と regime_detector のレジーム判定は LLM を用いるため、API の利用料・レイテンシに依存します。API 失敗時はフェイルセーフ（スコア 0.0）で継続する設計です。
- 日付取り扱いは全て date/datetime の naive オブジェクト（UTC 換算等）で統一し、ルックアヘッドバイアス対策として datetime.today() / date.today() を直接参照しない設計方針を採用しています。ただし一部のバッチジョブでは実際の today を使用する箇所があります（calendar_update_job など）。

---

今後のリリース案内や改修要望があれば、どの機能についてどのような改善を望むか教えてください。