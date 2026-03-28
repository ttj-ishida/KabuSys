Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - モジュール構成: data, research, ai, config, （将来的な）strategy / execution / monitoring 用の基盤をエクスポート。
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装（OS 環境変数が優先、.env.local が .env を上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - .env パーサー実装: コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 読み込み時の保護キー（protected）機能で OS 環境変数を上書きから保護。
  - Settings クラスを提供し、必須値取得（_require）・型検証・既定値・列挙検証（KABUSYS_ENV, LOG_LEVEL）などを行うプロパティを公開。
  - データベースパス（duckdb, sqlite）や Slack / kabu API / J-Quants トークン等の設定プロパティを提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から指定ウィンドウ（前日15:00 JST 〜 当日08:30 JST）を集計し、銘柄ごとに OpenAI (gpt-4o-mini) を用いてセンチメント評価して ai_scores に書き込む機能を実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたり記事数制限（_MAX_ARTICLES_PER_STOCK）、文字数トリム（_MAX_CHARS_PER_STOCK）を導入。
  - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とフェイルセーフ戦略を実装。API 失敗時は該当チャンクをスキップし全体処理を継続。
  - JSON Mode のレスポンスを堅牢にパース。周辺テキストが混在する場合は最外側の {} を抽出して復元を試みる。
  - レスポンス検証: results 配列・コードの整合性・スコアが数値かつ有限かをチェック。スコアは ±1.0 にクリップ。
  - DuckDB 互換性考慮: executemany に空リストを渡さない分岐を実装（DuckDB 0.10 の挙動への対応）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出・保存する機能を実装。
  - prices_daily からのルックアヘッド防止（date < target_date を使用）や、記事ウィンドウの計算（news_nlp.calc_news_window 利用）などフェアな設計。
  - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。API リトライ/バックオフ・500 系の扱い・JSON パース例外のフェイルセーフ（macro_sentiment=0.0）を備える。
  - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み、DB 書き込み失敗時は ROLLBACK を試行して上位例外に伝播。

- データ基盤ユーティリティ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存（save_market_calendar 呼出し）を行う。
    - カレンダー未取得時の曜日ベースフォールバック（主に土日判定）を採用し、DB データがまばらな場合でも一貫した next/prev/get_trading_days を提供。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day 等の営業日判定 API を提供。最大探索範囲の上限（_MAX_SEARCH_DAYS）や健全性チェック（_SANITY_MAX_FUTURE_DAYS）を実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得数・保存数・品質問題リスト・エラーリストを保持）。to_dict により品質問題を整形して出力可能。
    - 差分更新・バックフィル・品質チェック（quality モジュール想定）を想定した設計。jquants_client の save_* を用いて冪等保存する方針を反映。
    - DuckDB 存在チェックや最大日付取得等のヘルパーを実装。

- リサーチ / ファクター（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高指標）、Value（PER、ROE）などのファクター計算を実装。prices_daily / raw_financials のみ参照。
    - データ不足に対する None ハンドリング、結果を (date, code) キーの辞書リストとして返す設計。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。ホライズン検証（正の整数かつ <=252）を行う。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部依存なしで標準ライブラリのみで完結。
  - research パッケージは data.stats.zscore_normalize を再エクスポート。

- ロギングと堅牢性
  - 各所で詳細な logger メッセージを追加（info/debug/warning/exception）。
  - DB トランザクションでの ROLLBACK 保護とエラーロギングを徹底。
  - 日時操作はすべて明示的な引数（target_date 等）を使用し、datetime.today()/date.today() の過度な使用によるルックアヘッドバイアスを避ける方針。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（ただし DuckDB executemany の空リスト問題へ配慮した実装を導入）。

Known limitations / Notes
- OpenAI API（gpt-4o-mini）への依存があるため、実行環境に OPENAI_API_KEY の提供が必要。各 API 呼び出しは api_key 引数で注入可能。
- jquants_client、quality モジュールや実際のデータスキーマ（prices_daily, raw_news, news_symbols, raw_financials, market_calendar 等）は別ファイル/別モジュールとして想定。実動作にはこれらの実装と DuckDB スキーマが必要。
- 現フェーズでは sentiment_score と ai_score を同値で扱う（将来的に分離可能）。
- ニュース解析・レジーム判定の LLM 結果は確率的であり、実運用時は監視・手動検証の導入を推奨。

Authors
- kabusys 開発チーム

License
- プロジェクトのライセンスに従います（パッケージ内の LICENSE を参照してください）。