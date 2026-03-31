Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは SemVer に準拠します。

[Unreleased]
------------

- （未リリースの変更はここに記載します）

0.1.0 - 2026-03-31
------------------

Added
- 初期リリース: kabusys パッケージを導入。
  - パッケージ公開情報: バージョン 0.1.0（src/kabusys/__init__.py）。
  - 主要サブパッケージ: data, research, ai（公開 API としては data, research, ai の関数・クラスを提供）。

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - export 形式・クォート・コメントを考慮した堅牢なパーサ実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（J-Quants, kabuAPI, Slack, DB パス, 環境/ログレベル判定など）。
  - 必須環境変数未設定時には明確なエラーメッセージを送出。

- ニュース NLP（AI）モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して銘柄ごとのニューステキストを生成。
  - OpenAI（gpt-4o-mini、JSON mode）を用いたバッチセンチメント評価を実装。
  - バッチサイズ、記事数・文字数上限、タイムウィンドウ（JST 基準）の定義。
  - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ。
  - レスポンスの厳格なバリデーションと数値スコアの ±1.0 クリッピング。
  - 結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時の保護）。
  - OpenAI API キー注入対応（引数または環境変数 OPENAI_API_KEY）。
  - フェイルセーフ挙動: API エラー時はスキップ継続（例外を投げず処理継続）。

- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）。
  - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み。
  - LLM コールは gpt-4o-mini（JSON 出力）を使用、API リトライや 5xx 判定を備える。
  - ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を使用しない、DB クエリは target_date 未満条件など）。
  - API 失敗時は macro_sentiment を 0.0 にフォールバック。

- 研究（Research）モジュール（src/kabusys/research/**）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離などモメンタム系ファクターを計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials と prices_daily から PER, ROE を算出（最新報告値を使用）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に実装。データ不足時は None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクターの基本統計量（count, mean, std, min, max, median）を算出。
    - rank: ランク付けユーティリティ（同順位は平均ランク）。
  - 研究向け API は外部依存を最小化（標準ライブラリ + DuckDB）している。

- データプラットフォーム（src/kabusys/data/**）
  - calendar_management.py:
    - JPX カレンダー管理、is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ロジックを提供。
    - market_calendar が未取得時の曜日ベースフォールバックを備え、一貫した挙動を維持。
    - calendar_update_job: J-Quants API から差分取得 → ON CONFLICT 相当で冪等保存、バックフィル・健全性チェックを実装。
  - pipeline.py:
    - ETLResult dataclass を提供（ETL のフェッチ数・保存数・品質チェック結果・エラー収集などを保持）。
    - 差分更新や最大日付取得ユーティリティを実装（_get_max_date, _table_exists 等）。
    - ETL の設計方針: 部分失敗を許容して問題を収集し、呼び出し元で判断可能にする（Fail-Fast ではない）。
  - etl.py:
    - pipeline.ETLResult を再エクスポート。

- DuckDB を中心とした DB 操作設計
  - DuckDB の挙動（executemany 空リストの問題等）を考慮した実装。
  - SQL はウィンドウ関数等を活用しパフォーマンスに配慮。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT や executemany を使った冪等性を重視。

- ロギング・障害耐性
  - 各所で詳細な info/warning/logger を出力。例外が発生した場合は可能な限りロールバックして上位へ伝播。
  - LLM/API 呼び出しではリトライとフォールバック（ゼロ値や空スコア）を設け、処理全体の堅牢性を確保。

Notes / 使用上の注意
- OpenAI API（gpt-4o-mini）を利用する機能は API キー（引数または環境変数 OPENAI_API_KEY）が必須。
- データベース上の期待スキーマ（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar）を満たす必要あり。
- 環境変数の例（.env.example 相当）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, etc.
- ルックアヘッドバイアス対策として、内部 API は target_date を明示的に受け取り、現在時刻の暗黙参照を避ける設計。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 特になし（ただし API キー・パスワードは環境変数で管理すること）。

---

上記はコードベースの実装から推測して作成した初期リリースの変更履歴です。リリース時に実際のリリース日・追加項目・既知の制約を適宜修正してください。