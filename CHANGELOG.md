KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に従い、Semantic Versioning を想定しています。

Unreleased
----------
（次回リリースに含める変更をここに記載してください）

[0.1.0] - 2026-03-29
-------------------
Added
- 初回公開: KabuSys — 日本株自動売買・リサーチ基盤の初期実装を追加。
  - パッケージ構成: kabusys.{data,research,ai,config,...} を公開。
  - バージョン: __version__ = "0.1.0"。

- 環境設定/ロード (kabusys.config)
  - .env / .env.local の自動読み込み機能を追加。プロジェクトルートは .git または pyproject.toml を基準に探索して特定。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - 上書き制御（override）と OS 環境変数の保護（protected keys）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを取得可能。env と log_level は許容値検証を行い、不正値は ValueError を送出。
  - 必須設定取得用の _require() で未設定時に分かりやすい例外メッセージを返す。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を提供する calc_news_window を実装。
  - バッチサイズ、記事数・文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx）および指数バックオフを実装。失敗時は個別チャンクをスキップして継続するフェイルセーフ動作。
  - レスポンスの厳密なバリデーションと数値チェックを実装し、スコアは ±1.0 にクリップ。部分成功時に既存スコアを保護するため、対象コードのみ DELETE → INSERT で置換する冪等性を確保。
  - テスト容易性のために OpenAI 呼び出し部分（_call_openai_api）をモック置換可能に設計。
  - API キー未設定時に分かりやすい ValueError を送出。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - DuckDB からの過去データ参照時にルックアヘッドを防ぐため、target_date 未満のデータのみを使用。
  - OpenAI 呼び出しに対する再試行（指数バックオフ）と 5xx の扱い、API エラー時のフォールバック（macro_sentiment=0.0）を実装。
  - 結果は market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試み、上位へ例外を伝播。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。必要行数未満は None を返す。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出。EPS が 0/欠損の際は None。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装。ホライズンパラメータ検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データ不足（有効レコード < 3）時は None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクにするランク関数（丸めによる tie 検出の安定化を考慮）。
  - すべて DuckDB 接続を受け取り SQL と標準ライブラリで処理。外部の I/O（発注等）にはアクセスしない設計。

- データ基盤（kabusys.data）
  - calendar_management:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar テーブルを優先し、未登録日は曜日ベースのフォールバックを行う。
    - calendar_update_job: J-Quants API からの差分取得・保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）とバックフィル・健全性チェックを実装。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) を設け無限ループを防止。
  - pipeline / etl:
    - ETLResult データクラスを定義（取得数・保存数・quality issues・errors 等を保持）。to_dict で品質問題をシリアライズ可能。
    - ETL ユーティリティ関数: テーブル存在チェック、最大日付取得などを実装。差分更新・バックフィル・品質チェック（quality モジュールとの連携）を想定した設計。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

Changed
- 初期実装のため、各モジュールは「設計方針」ドキュメントコメントを含み、ルックアヘッドバイアス防止やフェイルセーフの設計を明示。
- DuckDB 互換性のため、executemany に対して空リストを渡さないガードロジックを追加（DuckDB 0.10 の制約対応）。
- OpenAI API 呼び出しに対するエラー処理を統一し、5xx / レートリミット / 接続エラーはリトライ対象、それ以外はスキップしてログ出力する挙動に統一。

Fixed
- JSON Mode のレスポンスに前後テキストが混入するケースに備え、最外の {} を抽出してパースする復元ロジックを追加（news_nlp）。
- market_regime / ai_scores への書き込みを冪等化し、部分失敗時に既存データを不必要に消さないように対策。

Notes / Implementation details
- OpenAI クライアント呼び出し箇所（_call_openai_api）はテスト用にモック差替え可能にしており、ユニットテストで外部 API を回避できる設計。
- 多くの処理で「失敗してもシステム全体を止めない」フェイルセーフを採用。ログ出力で状態を追跡することを想定。
- すべての日付処理は timezone-less な date / datetime オブジェクトで扱い、UTC/JST の変換は明示的に行う（ニュースウィンドウなど）。
- 環境変数の必須チェックや値検証で早期に不整合を検出できるように設計。

Known Issues
- 初期バージョンのため、実運用での耐障害性・スケール試験が未実施。API サービス側の仕様変更（OpenAI SDK の互換性等）により例外ハンドリングの微調整が必要になる可能性あり。
- raw_financials に依存する指標（PER 等）は財務データの鮮度と整合性に依存するため、品質チェックの運用が重要。

Acknowledgements
- DuckDB をデータレイヤに採用。
- OpenAI（gpt-4o-mini）を NLP 評価に利用する設計を採用。

-- End of changelog for 0.1.0 --