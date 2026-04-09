# CHANGELOG

このプロジェクトは Keep a Changelog のガイドラインに従って変更履歴を管理します。
全ての重要な変更はこのファイルに記載します。

フォーマット:
- すべての変更はカテゴリ（Added, Changed, Fixed, Removed, Deprecated, Security）に分類します。
- 日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買・リサーチプラットフォームのコア機能を実装しました。

### Added
- 基本パッケージ定義
  - kabusys パッケージのエントリポイントとバージョン定義を追加（__version__ = 0.1.0）。
  - パッケージの公開モジュール一覧を __all__ で定義。

- 環境設定 / .env ロード機能（kabusys.config）
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local で上書き）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化できるオプションを追加。
  - .env パーサ実装：コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
  - Settings クラスを追加し、アプリケーション設定を型付きプロパティで提供：
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite） / Paper Trading 設定 / 監視設定 / システム設定（env, log_level 等）。
  - Paper Trading の PAPER_FILL_MODE の入力検証（instant|partial|never|reject）。
  - 環境変数が必須な場合に明確なエラーメッセージを出す _require ユーティリティを実装。

- AI 関連機能（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信して銘柄単位のセンチメントを算出。
    - チャンクサイズ、記事数・文字数上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフとリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、スコア数値検証、未登録コードの無視）。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）で部分失敗時の被害を最小化。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを追加（ルックアヘッドバイアス回避）。
    - 外部に OpenAI API キーを注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースからのマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - DuckDB からのデータ取得、OpenAI 呼び出し（リトライ・フォールバック）、スコア合成、market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 で安全に継続（フェイルセーフ）。
    - OpenAI 呼び出しはモジュール内プライベートとして実装しテスト置換を想定（patch 可能）。

- Research（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出。データ不足時の扱いを明示。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を算出。NULL/データ不足取り扱い。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS が 0 または欠損時の挙動明記）。
    - DuckDB を前提とした SQL + Python の実装、外部 API へ依存しない設計。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを算出。horizons パラメータ検証。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。レコード不足時の None 返却。
    - rank: 同順位を平均ランクで扱うランク関数（丸めによる ties 問題に対処）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算するユーティリティ。
  - 研究用に zscore 正規化ユーティリティを data.stats から再公開（kabusys.research パッケージで export）。

- Data プラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブルの利用、曜日ベースのフォールバック）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の実装。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して冪等に保存する夜間バッチジョブ。バックフィル・健全性チェック実装。
  - ETL / pipeline
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約して to_dict によるシリアライズを提供。
    - pipeline モジュールの ETLResult を etl パッケージから再エクスポート（kabusys.data.etl）。
    - ETL 設計に関するポリシー（差分更新、バックフィル、品質チェックの扱い等）を明文化。

- 依存性／外部 API に対する設計方針を明記
  - 全ての AI / ETL / リサーチ処理でルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない設計。
  - DuckDB のバージョン互換性（executemany の空リスト制約など）に配慮した実装。
  - OpenAI 呼び出しについては APIError の status_code を安全に扱い 5xx のみリトライ対象にする等の堅牢化。
  - ロギングとフォールバック（警告・情報ログ）を充実させ、部分失敗が全体を止めない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用する設計。必須チェックを行い未設定時は明確なエラーを発生させます。

---

注意事項 / 既知の制約
- OpenAI（gpt-4o-mini）を利用する箇所はネットワーク・API レート制限等の影響を受けます。ライブラリ側で再試行やフォールバックを実装していますが、API キーと利用制限の管理は利用者の責任です。
- DuckDB をデータストアとして想定しています。SQL や executemany の振る舞いは DuckDB のバージョン差による影響を受けるため、実運用前に利用バージョンでの確認を推奨します。
- news_nlp/regime_detector の OpenAI 呼び出し部はテスト用にモック置換できるよう設計されています（unittest.mock.patch を想定）。

（このファイルはコードベースの現在の状態から推定して作成しています。実際の変更履歴があればそちらを優先して反映してください。）