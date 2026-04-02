# Changelog

すべての変更は Keep a Changelog の形式に従い記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-02

### Added
- パッケージ初期リリースとして以下の主要サブモジュールを追加。
  - kabusys.config
    - .env ファイルまたは環境変数からの設定読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動で .env/.env.local を読み込む自動ロードを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート）。
    - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート（エスケープ処理対応）、インラインコメントの扱い等をサポート。
    - 環境変数取得用 Settings クラスを提供（J-Quants / kabu API / Slack / DBパス / 監視閾値 / 環境・ログレベル検証などのプロパティ）。
    - 必須環境変数未設定時に明確な例外を送出する `_require` を実装。
  - kabusys.ai
    - news_nlp.score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを計算し ai_scores テーブルへ書き込む機能を実装。
      - JST 時間ウィンドウ（前日15:00〜当日08:30）を正しく UTC に変換して使用。
      - 1銘柄あたりの最大記事数・最大文字数でトリム、バッチ（最大20銘柄）での API 呼び出し。
      - JSON Mode を使用しレスポンスの厳密バリデーションと不正レスポンス・部分失敗時のフォールバック処理を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフによるリトライ実装。
      - DuckDB の executemany の空リスト制約を考慮した安全な DB 書き込み（DELETE→INSERT の置換）を実装。
    - regime_detector.score_regime: ETF (1321) の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込みする機能を実装。
      - 1321 MA200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立値採用）。
      - マクロニュース抽出（キーワードフィルタ）、LLM 呼び出し（gpt-4o-mini + JSON mode）、リトライ・フェイルセーフを実装。
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。失敗時は ROLLBACK を実施。
  - kabusys.research
    - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）を計算。
      - Volatility: 20日 ATR（true range の NULL 取り扱いを含む）、相対 ATR、20日平均売買代金、出来高比率を計算。
      - Value: raw_financials の最新財務データと当日株価から PER / ROE を計算（EPS が0/欠損のときは None）。
    - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
      - 将来リターン（horizons に応じた LEAD を用いた一括取得、引数検証あり）。
      - IC（Spearman の ρ）計算はランク化して ties の平均ランク処理を考慮。
      - 統計サマリー（count/mean/std/min/max/median）を純粋な標準ライブラリのみで実装。
  - kabusys.data
    - calendar_management: JPX マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ calendar_update_job を実装。
      - market_calendar 未取得時は曜日ベースのフォールバック（土日非営業日扱い）。
      - DB 値優先の一貫したフォールバックロジック、最大探索日数による無限ループ防止、バックフィル・健全性チェックを実装。
      - calendar_update_job は jquants_client を通じて差分取得・保存（バックフィル・lookahead を考慮）。
    - pipeline / etl: ETL パイプラインの基本構造と ETLResult データクラスを実装。
      - 差分更新・バックフィル・品質チェック（quality モジュールと連携）の設計に対応。
      - ETLResult は品質問題の要約やエラー検出フラグを含み、辞書化（監査ログ用）可能。
    - etl モジュールで pipeline.ETLResult を公開再エクスポート。
  - パッケージの __init__ でバージョン情報（__version__ = "0.1.0"）と主要サブパッケージの公開を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を用いる設計とし、キー未設定時は明示的な例外で失敗させることで誤動作の抑止を実装。

### Notes / 設計方針（重要）
- ルックアヘッドバイアス回避: news / regime / research 各モジュールは内部で datetime.today() / date.today() を参照せず、常に引数で与えた target_date を基準に計算する設計。
- フェイルセーフ: OpenAI 等外部 API 失敗時は例外直上げではなく、デフォルトスコア（0.0）で継続するなどのフォールバックを多用してバッチの中断を防止。
- DB 操作の冪等性: market_calendar, ai_scores, market_regime などは上書き/置換のロジックを備え、部分失敗時に既存データが不必要に消えないよう配慮。
- DuckDB 互換性: executemany の空リスト問題や日付型変換を考慮した実装を行っている。
- テスト容易性: OpenAI 呼び出し関数はモジュール間で private 関数を共有せず、単体テスト用にモック差し替え可能な設計（unittest.mock.patch を想定）とした。

### Known issues / 限界
- gpt-4o-mini を利用する想定だが、実行環境により OpenAI SDK のバージョン差で例外型や属性が異なる場合があるため、APIError の status_code 等は getattr で安全に扱う実装にしている。
- 一部モジュール（例: jquants_client, quality モジュールの具体実装、monitoring サブパッケージの中身）はこのリリースのコードスニペットに含まれていないため、外部依存として実装・組み込みが必要。

---

（今後のリリースでは「Changed / Fixed / Removed / Security」セクションを適宜追加してください）