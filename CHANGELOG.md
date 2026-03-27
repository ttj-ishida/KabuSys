CHANGELOG
=========

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（kabusys）から推測される初期リリースの変更履歴を日本語でまとめたものです。

フォーマット:
- Unreleased: 開発中の変更（なし）
- 各リリースは日付付きで記載

Unreleased
----------
（現在のところ未リリースの変更はありません）

0.1.0 - 2026-03-27
-----------------
初回公開リリース。主要機能・モジュールを実装。

Added
- パッケージ基盤
  - パッケージ情報とエクスポートを定義（kabusys.__init__、__version__ = "0.1.0"）。
  - モジュール構成: data, strategy, execution, monitoring を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと環境変数からの設定自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を探索）によりカレントワーキングディレクトリ非依存の自動読み込みを実現。
  - .env パーサーの実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - .env/.env.local の読み込み順と override ロジック、OS 環境変数保護（protected set）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等のプロパティを定義。必須環境変数の検査（_require）を実装。
  - KABUSYS_ENV, LOG_LEVEL の検証（有効値チェック）とユーティリティプロパティ（is_live, is_paper, is_dev）を追加。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）と営業日ロジックを実装。
    - is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。検索範囲上限と健全性チェック（最大探索日数/_SANITY_MAX_FUTURE_DAYS）を実装。
    - calendar_update_job により J-Quants からの差分取得、バックフィル（直近数日の再取得）、冪等保存を実現。
  - etl / pipeline:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの収集）。
    - ETL パイプライン基盤のユーティリティ（最終取得日の検出、テーブル存在チェック、差分取得方針、バックフィル設定）を実装。
    - jquants_client と quality モジュールとの連携を想定した設計。

- AI / ニュース・NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメント（ai_score）を算出して ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの記事トリム（最大記事数・最大文字数）によりトークン肥大化対策を実装。
    - OpenAI 呼び出しは JSON mode を利用。429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフ再試行を実装。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ、部分成功時に既存スコアを保護するための部分置換（DELETE → INSERT）を実装。
    - テスト容易化のため _call_openai_api を patch 可能にしている。
  - regime_detector:
    - ETF 1321（日経225連動型）の直近200日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI へ JSON モードで投げて macro_sentiment を取得。API 失敗時はフェイルセーフで 0.0 にフォールバック。
    - レジーム算出後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、エラー時は ROLLBACK を試行。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）ファクターを実装。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。データ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（Spearman のρ）、rank（同順位は平均順位の扱い）、factor_summary（基本統計量）を実装。
    - pandas 等外部依存なしで標準ライブラリと DuckDB を利用する設計。
  - Research パッケージ __init__ で主要 API を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Security
- 環境変数の読み込みに関する保護（OS 環境変数の上書きを防ぐ protected set）を導入。
- OpenAI API キーを明示的に渡す設計（api_key 引数 or OPENAI_API_KEY 環境変数）。未設定時は ValueError を発生させ誤使用を抑止。

Notes / 実装上のポイント（利用者向け）
- ルックアヘッドバイアス対策: 全ての AI / リサーチ処理は内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計。
- DuckDB を主要なローカル分析 DB として使用。テーブルスキーマ（prices_daily, raw_news, market_calendar, raw_financials, news_symbols, ai_scores, market_regime 等）を前提としている。
- OpenAI 呼び出しは JSON 形式での厳密パースを期待しているが、実運用時の余分な前後テキストにも耐えるように復元ロジックを実装。
- テスト容易性: 環境変数自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）や、OpenAI 呼び出しの差し替え（モジュール内のプライベート関数を patch）を考慮。

Breaking Changes
- 初回リリースのため破壊的変更はありません。

参考
- パッケージバージョンは kabusys.__version__ = "0.1.0" を参照。
- 以降のリリースでは、各モジュールの安定化、テストカバレッジ拡充、外部 API（J-Quants / kabuステーション / Slack）用のクライアント実装追加などが想定されます。