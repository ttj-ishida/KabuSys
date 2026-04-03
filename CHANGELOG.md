CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
リリース日や内容はコードベースから推測して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - 高レベル概要：日本株の自動売買 / 研究 / データ基盤のユーティリティ群を含む初期実装。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を走査）。これにより CWD に依存せずパッケージ配布後も動作。
  - .env パーサー強化：
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなしの行でインラインコメント（#）を扱うルールを実装。
  - 読み込み時の上書き制御（override）と、OS 環境変数を保護する protected セットに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供（settings インスタンスを公開）：
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 等のプロパティを環境変数から取得。
    - デフォルト値と型変換（Path, float, bool）を適用。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（受け入れ可能な値を列挙してエラーを投げる）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント（銘柄ごと）スコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news と news_symbols を集約して銘柄毎に最新記事を結合し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを取得。
    - チャンク単位（最大 20 銘柄）での API 呼び出しとエクスポネンシャルバックオフ retry（429、ネットワーク断、5xx、タイムアウト対応）。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検証、数値チェック）と ±1.0 でのクリップ。
    - スコアは ai_scores テーブルへ冪等的に書き込み（該当コードのみ DELETE → INSERT）し、部分失敗で既存データを保護。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する calc_news_window。
    - 設計上、datetime.today()/date.today() を参照しない（ルックアヘッドバイアス回避）。API キーは引数注入可能。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用い、マクロキーワードでフィルタしたタイトルを LLM へ与える。
    - OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を想定。API エラー時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - レジームの合成スコアはクリップされ、market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等的に保存。エラー時は ROLLBACK を試みる。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar の有無に応じたフォールバックロジック（DB がない場合は曜日ベースで営業日の判断）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ユーティリティを提供。
    - next/prev の探索に上限（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
    - calendar_update_job を実装：J-Quants クライアント経由で差分取得し market_calendar を更新（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義し、ETL の実行結果（取得件数、保存件数、品質問題、エラー等）を構造化。
    - 差分取得、backfill、品質チェック（quality モジュール連携）等の方針を反映した実装方針を含むユーティリティ群。
    - DuckDB 前提でのテーブル存在チェックや最大日付取得ユーティリティを実装。
  - ETL の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールで量的ファクター群を実装：
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金（avg_turnover）・出来高比（volume_ratio）を計算。必要行数未満は None。
    - calc_value: raw_financials から当日以前の最新財務を結合して PER, ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも DuckDB を用いた SQL ベースの計算で、外部 API には依存しない設計。
  - feature_exploration モジュールで統計解析ユーティリティを実装：
    - calc_forward_returns: 指定基準日から見た将来リターン（任意ホライズン）を一括で取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装。有効レコード 3 件未満は None。
    - rank: 同順位は平均ランクで扱うランク付け実装（round(v, 12) による tie 回避）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- パッケージ API 露出
  - top-level パッケージ __all__ による主要サブパッケージの公開（data, strategy, execution, monitoring）。
  - 各モジュールで主要関数・クラスを __all__ 経由で公開（例: kabusys.ai.__all__ には score_news）。

Notes / 実装上の重要な設計判断（ドキュメント的に記載）
- ルックアヘッドバイアス回避：AI スコアリング・レジーム判定・ETL/研究系の関数は内部で datetime.today()/date.today() を参照せず、引数の target_date に基づいて全ての時間窓を決定します。
- OpenAI 統合：gpt-4o-mini を想定した JSON Mode を利用。429/ネットワーク断/タイムアウト/5xx に対するリトライ（指数バックオフ）を組み込み、サービス不可時は安全側（0.0 など）で処理継続する方針。
- DuckDB 前提：データ操作は DuckDB 接続を受け取り SQL／ウィンドウ関数で行う実装。部分失敗に備えたテーブル単位の限定削除と INSERT による冪等性を優先。
- エラーハンドリング：API パース失敗や不正応答は例外を投げずログを出してスキップする箇所が多く、失敗しても他の処理を止めないフェイルセーフ設計。
- テスト容易性：OpenAI 呼び出しや .env 自動ロードを無効化可能にするなど、ユニットテストで差し替えや注入が行いやすい設計（関数差し替えや patch がしやすい）。

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー等の機密情報は environment から取得する設計。.env の取り扱いは上書き保護と保護セットにより OS 環境変数の誤上書きを防止する配慮あり。

脚注
- 実際のリリース日・バージョンや追加の変更履歴は、リポジトリのコミット履歴やリリースノートに基づいて更新してください。