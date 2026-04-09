# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

現在のリリース:
- [0.1.0] - 2026-04-09

## [0.1.0] - 2026-04-09
初回リリース。本リポジトリのコア機能群を実装しています。主に日本株データのETL・カレンダー管理・ファクター計算・AIを用いたニュース分析・市場レジーム判定・設定管理等を提供します。DuckDB を主要データ層として想定し、OpenAI（gpt-4o-mini）をニュース/NLP 用に利用する設計です。

### 追加 (Added)
- パッケージ初期化
  - kabusys.__init__ によるパッケージ構成（data, strategy, execution, monitoring を公開）。
  - バージョン情報: 0.1.0。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - 行パーサの実装：コメント・クォート・export 形式・インラインコメント等に対応した .env パース処理。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスでアプリケーション設定をプロパティ提供（J-Quants トークン、kabu API、LINE、DBパス、Paper Trading 設定、監視閾値、環境/ログレベル判定 等）。
  - 必須環境変数未設定時は _require() による ValueError を発生させる挙動。

- AI ニュース分析 (kabusys.ai.news_nlp)
  - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し、OpenAI にバッチ送信して ai_scores テーブルへ書き込む。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
  - バッチ処理、1チャンク最大20銘柄、記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しの再試行（429・ネットワーク・タイムアウト・5xx を指数バックオフでリトライ）、レスポンス検証、スコアの ±1.0 クリップ。
  - JSON Mode を想定したレスポンス復元ロジック（前後テキスト混入時に最外の {} を抽出）。
  - API 未設定時に ValueError を発生。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
  - マクロキーワードで raw_news をフィルタして LLM に渡す実装、API の再試行・フォールバック（API失敗時 macro_sentiment=0.0）。
  - Look-ahead バイアス防止のため datetime.today() を参照せず、prices_daily は target_date 未満のデータのみを使用する設計。
  - OpenAI 呼び出しはモジュール内専用実装で、モジュール間の結合を避ける。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダーの取得・更新バッチ（calendar_update_job）および is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定機能。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末は非営業日扱い）。
    - 最大探索日数・バックフィル・健全性チェック等を実装し無限ループや異常データを回避。
    - J-Quants クライアント経由で差分取得・冪等保存を想定。
  - etl / pipeline:
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質チェック結果やエラー一覧を保持）。
    - ETL の設計方針・差分更新・バックフィル・品質チェック等を実装するための基盤（jquants_client, quality モジュールと連携想定）。
    - DuckDB を前提とした保存処理（トランザクション、BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK の保護ログ）。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR（単純平均）/相対 ATR/平均売買代金/出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算。
    - DuckDB 上で SQL とウィンドウ関数を活用した実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマン（ランク相関）に基づく IC 計算（rank を用いた処理、最小レコード数チェック）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位は平均ランク処理（浮動小数の丸めで ties を安定化）。
  - data.stats の zscore_normalize を再エクスポート。

### 変更 (Changed)
- なし（初回リリースのため該当無し）。

### 修正 (Fixed)
- API/外部依存の堅牢化
  - OpenAI API 呼び出しに対して 429/接続断/タイムアウト/5xx を対象としたリトライ実装とフォールバック（必要に応じて 0.0 等の中立値を使用）を導入。
  - JSON パース失敗時の保護（news_nlp: 前後余計文字の復元、regime_detector: パース失敗は macro_sentiment = 0.0）。
  - DuckDB の executemany に空リストを与えない安全策（空の場合はスキップ）を実装。

### 削除 (Removed)
- なし。

### 非推奨 (Deprecated)
- なし。

### セキュリティ (Security)
- 環境変数の読み込み時に OS 環境変数を保護する仕組み（.env による上書きの protected キー）を実装し、テスト等で自動ロードを無効化できるフラグを提供 (KABUSYS_DISABLE_AUTO_ENV_LOAD)。

---

備考:
- 多くのモジュールは DuckDB 接続を受け取り、prices_daily / raw_news / ai_scores / market_regime / raw_financials / market_calendar 等のテーブルに依存します。実行前にスキーマ準備・データ投入が必要です。
- OpenAI を利用する機能は api_key 引数または環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError を発生させます。
- 本CHANGELOGはコード内容からの推測に基づいて作成しています。実際の開発履歴やコミット履歴と差異がある可能性があります。