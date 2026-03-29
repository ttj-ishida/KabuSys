# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
各リリースはセマンティックバージョニングに従います。

※ 本リリースノートはソースコードから機能・設計意図を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。本バージョンでは日本株自動売買システム「KabuSys」のコアライブラリ群を実装しました。以下の機能セットを提供します。

### Added
- 基本パッケージメタ情報
  - パッケージ基本情報を定義（kabusys.__init__ にて version=0.1.0、公開サブパッケージの __all__ を定義）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサを実装（export 句対応、シングル/ダブルクォートとエスケープ処理、行末コメント処理）。
  - 環境変数必須チェック用 _require と Settings クラスを提供。J-Quants / kabu / Slack / DB パスなどの設定項目をプロパティで取得。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値の集合を定義）。
  - デフォルト DuckDB/SQLite パスや kabu API の base URL のデフォルトを設定。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（日本時間基準で前日15:00〜当日08:30）を提供（calc_news_window）。
    - バッチサイズ、記事数上限、文字数上限、レスポンス検証ロジックを実装。
    - レート制限・ネットワーク断・5xx に対する指数バックオフによるリトライ機構。
    - JSON Mode の出力を厳密に検証し、未知コードや不正レスポンスを安全に無視するバリデーション処理。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で実施。部分失敗時に既存スコアを保護する実装。
    - OpenAI API キーの注入（引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照してスコアを計算し、market_regime テーブルへ冪等書き込みを行う（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しのリトライとエラー時フェイルセーフ（macro_sentiment を 0.0 にフォールバック）。
    - OpenAI 呼び出しは内部で OpenAI クライアントを生成して行う（テスト時差し替え可能な _call_openai_api を定義）。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用する設計。

- データプラットフォーム（kabusys.data）
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無に応じた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先、未登録日は曜日ベースのフォールバックを採用（DB がまばらな場合でも一貫性を保つ）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェックを実装）。
    - DuckDB 日付型変換ユーティリティやテーブル存在チェックなどのユーティリティ関数。
    - 最大探索日数など安全性を考慮した定数を導入。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスによる ETL 実行結果の表現（品質問題・エラーの収集、辞書化メソッドを提供）。
    - データ差分取得、保存、品質チェックの設計方針に沿ったユーティリティ（jquants_client と quality モジュール連携を想定）。
    - テーブル最大日付取得やテーブル存在確認のヘルパーを実装。
    - 市場カレンダー先読み・バックフィル・最小データ開始日等の定数管理。

  - データ ETL 公開インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター分析（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 または欠損の場合は None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQL ベースの集約処理で、prices_daily / raw_financials のみを参照。
    - 不足データ時の None 扱い・ログ出力を実装。

  - 特徴量探索 / 統計（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応、ホライズン妥当性チェック。
    - IC（情報係数）計算（calc_ic）：Spearman ランク相関の実装（同順位の平均ランク処理を含む）。有効レコード 3 未満は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位処理と丸めによる ties 対策。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算（None 値除外）。
    - pandas などに依存しない、標準ライブラリのみの実装方針。

- パッケージ構成の公開 API
  - research パッケージは主要関数（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）を __all__ で公開。
  - ai パッケージは score_news を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI / J-Quants / kabu / Slack 関連のシークレットは環境変数で管理することを想定。
  - 必須の環境変数が未設定の場合、Settings のプロパティや関数内で ValueError を投げる設計。
- .env 自動読み込み時に既存 OS 環境変数は保護され、.env.local は明示的に上書き可能（ただし protected に含まれるキーは上書き不可）。

---

既知の注意点 / 今後の改善候補（実装方針に基づく推測）
- OpenAI API コールは gpt-4o-mini を前提に JSON Mode で扱うが、将来モデル変更時の互換性対応が必要。
- news_nlp のレスポンスバリデーションはかなり保守的に実装されているため、LLM の出力形式が変わるとスコア取得失敗が発生する可能性あり。
- DuckDB executemany の空引数制約（バージョン依存）を考慮した実装になっているが、DB バージョンの違いでの追加テストが必要。
- strategy / execution / monitoring パッケージは __all__ に列挙されているが本差分ではソースは含まれていないため、運用・実行周り（発注・監視）の実装は別途追加が必要。

---

（補足）本 CHANGELOG は公開済みソースコードをベースに機能と設計方針を推測して記載しています。実際の変更履歴やコミット履歴が利用可能な場合は、そちらに基づく正確な差分を将来的に反映してください。