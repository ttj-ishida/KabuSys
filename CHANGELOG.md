# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。互換性のない変更はメジャー番号の更新とともに行います。

現在のバージョン: 0.1.0

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 初回リリース

最初の公開リリース。主要コンポーネントを含む日本株向け自動売買/リサーチ用ライブラリを追加しました。主な内容は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API 候補として data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git or pyproject.toml に基づく）。
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などを考慮した .env パーサ実装。
  - OS 環境変数保護（既存の環境変数は上書きしない、.env.local は上書き可能）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - 必須環境変数取得用の _require ヘルパーと Settings クラスを提供（J-Quants/Slack/kabu API/DB パス/実行環境等のプロパティを持つ）。
  - env 値・log level のバリデーション（許容値チェック）、is_live/is_paper/is_dev ヘルパー。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを構成し、OpenAI（gpt-4o-mini）に対してバッチ（最大20銘柄）で JSON Mode によるセンチメント推定を実行。
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST を UTC で比較）を calc_news_window で提供。
    - 1銘柄あたりの最大記事数/文字数制限、API リトライ（429/ネットワーク/5xx）・指数バックオフ、レスポンス検証（JSON 抽出・results 配列・code/score の検証）を実装。
    - スコアは ±1.0 でクリップ。取得済み銘柄のみを DELETE→INSERT することで部分失敗時に既存データを保護。
    - score_news API を公開（DuckDB 接続・target_date を引数に取り、書き込んだ銘柄数を返す）。テスト時の差し替えポイントを用意（_call_openai_api など）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei連動ETF）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からデータ取得、ma200_ratio 計算、マクロキーワードでのニュース抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得。
    - LLM 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx）を行い、失敗時はフェイルセーフで macro_sentiment=0.0 を利用。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み。score_regime API を公開。
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を参照しない・DB クエリは target_date 未満のデータに限定）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、一貫した探索ロジック（最大探索日数制限で無限ループ防止）。
    - JPX カレンダーの差分取得/保存を行う夜間バッチ calendar_update_job（J-Quants クライアントの fetch/save を呼び出す、バックフィル・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を扱う ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧などを保持、辞書化メソッドあり）。
    - 差分更新・バックフィル方針・品質チェックの扱い方針などを実装方針として反映。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整ロジックなど。
    - etl モジュール経由で ETLResult を再エクスポート（kabusys.data.etl）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - 入力は DuckDB 接続と target_date、結果は (date, code) をキーとする辞書リストで返却。データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman のランク相関）、rank ユーティリティ、統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず純 Python/SQL 実装、欠損や ties の扱いに注意した実装。
  - data.stats の zscore_normalize を re-export（kabusys.research.__init__ 経由）。

### Changed
- （初回公開のため特段の変更履歴はなし）  
  - 実装設計の注記として、ルックアヘッドバイアス回避、フェイルセーフ、テストフック、DuckDB 互換性（executemany の空リスト回避等）を明記。

### Fixed
- （初回公開のためバグ修正履歴なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用する設計。呼び出し失敗時のフォールバックを実装し、例外の直接伝播を抑える箇所あり（ただしキー管理自体は利用者側の責任）。

---

注意事項 / 実装上の重要ポイント
- ルックアヘッドバイアス防止: すべての解析・スコア算出は target_date を明示的に受け取り、内部で現在時刻を参照しない方針です。
- API 呼び出しの堅牢化: OpenAI 呼び出しは JSON Mode を使い、429/ネットワーク/タイムアウト/5xx に対して再試行戦略（指数バックオフ）を採用。致命的なケースでは該当チャンクをスキップして他データの保護を優先します。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当）を意識して実装しています。部分失敗時に既存データを不意に消さない設計です。
- DuckDB 前提の SQL 実装: DuckDB の型や executemany の挙動を考慮した実装となっています。
- テスト容易性: OpenAI 呼び出し等は内部関数をモック可能にしてあり、ユニットテストで差し替えられるようになっています。

---

（補足）本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートやユーザー向けドキュメントはお好みで日付や追加の利用例、互換性注意点を追記してください。