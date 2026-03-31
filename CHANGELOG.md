# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルにはプロジェクトの重要な変更点・機能追加を記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下は主な追加点・設計上の要点です。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開モジュールを定義（kabusys.__init__、バージョン: 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に一部記載）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォート内は無視、非クォートは '#' の前が空白/タブの場合にコメント扱い）。
  - .env.local は .env を上書きする挙動（ただし OS 環境変数は保護）。
  - Settings クラスを提供し、必須値取得用の _require と各種プロパティを実装:
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証など。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント評価を実行する機能を実装。
  - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window で提供。
  - バッチ処理 (_BATCH_SIZE=20)、記事・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、JSON バリデーション、スコアクリップ（±1.0）を実装。
  - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
  - API 呼び出し部の差し替えフック（unittest.mock.patch で _call_openai_api をモック可能）を用意。
  - 成功したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗時に既存スコアを保護）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
  - prices_daily と raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - LLM 呼び出し時のリトライ/バックオフ、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
  - OpenAI クライアントは環境変数または引数で解決。内部でのテスト差し替えを考慮した実装。

- データ処理（kabusys.data）
  - ETL パイプラインインターフェース（ETLResult の公開）。
  - pipeline モジュールに ETLResult データクラスを実装。ETL の取得数・保存数・品質問題・エラー情報を保持し、辞書化メソッドを提供。
  - calendar_management モジュール:
    - JPX マーケットカレンダー管理、営業日判定ユーティリティ（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - calendar_update_job により J-Quants API から差分取得 → 市場カレンダーへ冪等保存。バックフィル・健全性チェックを実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）を提供。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールに以下を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）算出。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS 不在/0 の扱いは None）。
  - feature_exploration モジュールに以下を実装:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（有効レコード数が不足すれば None を返す）。
    - rank: 同順位を平均ランクで扱うランク変換ユーティリティ（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー算出。
  - research パッケージは必要なユーティリティを再エクスポートして使いやすく整理。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY で解決。キー未設定時は明確な ValueError を送出して誤動作を防止。
- .env ロード時に OS 環境変数を保護する仕組みを実装（protected set により既存値を上書きしない）。

### Notes / Implementation details
- ルックアヘッドバイアス対策:
  - AI モジュール（news_nlp, regime_detector）は datetime.today() / date.today() を直接参照しない設計。target_date を明示的に受け取り、クエリでは date < target_date / date = ? といった排他条件を使用。
- DuckDB を主要な分析 DB として採用。SQL と Python を組み合わせて高効率に集計処理を行う設計。
- API 呼び出し周りはリトライ（指数バックオフ）・エラーハンドリングを重視。LLM レスポンスのパース失敗や API エラー時はスキップまたはフォールバック値により処理を継続することで堅牢性を確保。
- DB 書き込みは可能な限り冪等性を担保（DELETE → INSERT、ON CONFLICT を想定）し、部分失敗が他データを消さない工夫を実施。
- テスト容易性: OpenAI 呼び出しの差し替えポイントや環境ロード無効化フラグなど、ユニットテスト向けのフックを用意。

---

その他、各モジュール内に詳細なドキュメント文字列（docstring）と設計意図を含めています。必要であれば各関数・API の使用例や注釈（引数の期待型、戻り値、例外条件など）を別途まとめたドキュメントを作成できます。