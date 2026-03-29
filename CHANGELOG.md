# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

（現時点のリリースは 0.1.0 のみ。将来の変更をここに記載します）

---

## [0.1.0] - 2026-03-29

最初の公開リリース。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージと __version__ = "0.1.0" を追加。
  - サブパッケージ公開: data, strategy, execution, monitoring（__all__ にてエクスポート）。

- 環境設定・ロード機能
  - settings を提供する Settings クラスを実装。
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロード無効化のための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - 必須環境変数チェックを行う _require() を実装。
  - 主要な設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL
    - is_live/is_paper/is_dev ヘルパー

- AI モジュール（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）用の calc_news_window を提供。
    - バッチサイズ、最大記事数、最大文字数等のパラメータを適用してプロンプト肥大化を抑制。
    - リトライ（429・接続断・タイムアウト・5xx に対する指数バックオフ）・レスポンス検証・スコアの ±1.0 クリップ。
    - スコア書き込みは部分的失敗に配慮して、対象コードのみ DELETE → INSERT による置換で行う（冪等性）。
    - テスト用に _call_openai_api をパッチ差替え可能。
  - kabusys.ai.regime_detector:
    - ETF(1321) の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily/raw_news を参照し、計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - マクロニュース抽出用キーワードリスト、OpenAI 呼び出しとリトライ戦略を実装。
    - API エラー時は macro_sentiment=0.0 でフォールバックするフェイルセーフ設計。
    - テスト用に _call_openai_api を差し替え可能。

- データモジュール（Data Platform ヘルパー）
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar）機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日（土日）ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants クライアント経由で差分取得 → 保存（ON CONFLICT 相当）を行う。
    - 探索範囲上限 (_MAX_SEARCH_DAYS) やバックフィル・健全性チェックを導入。
  - kabusys.data.pipeline:
    - ETLResult データクラスと ETL パイプラインの骨組みを実装。
    - 差分取得、保存（jquants_client 経由）、品質チェック（quality モジュール）を想定した設計。
    - duckdb との互換性考慮（executemany に空リストを渡さない等）。
  - kabusys.data.etl:
    - pipeline.ETLResult を再エクスポート。

- リサーチ/分析機能
  - kabusys.research.factor_research:
    - Momentum（1/3/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）等の計算関数を実装。
    - DuckDB を利用した SQL ベースの処理で、prices_daily / raw_financials を参照。
    - 計算結果を (date, code) をキーとする dict のリストで返す設計。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず純粋な Python 実装。
  - kabusys.research.__init__ で主要関数をエクスポート。

### 変更 (Changed)
- 設計方針の明示化（各モジュール内 docstring）:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない方針を各 AI / リサーチ関数で採用。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT や ON CONFLICT 相当）し、部分的失敗時の既存データ保護を考慮。
  - OpenAI 呼び出しはモジュールごとに独立したラッパー実装とし、モジュール間のプライベート関数共有を避ける設計。
- エラーハンドリングとログ出力を強化:
  - OpenAI 呼び出しの各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対するリトライ/フォールバック処理。
  - JSON レスポンスパース失敗や想定外フォーマットに対して警告ログを出して安全にスキップ。
- DuckDB 互換性対応:
  - executemany に空リストを渡さないチェックや、list 型バインドの回避（個別 DELETE）など互換性考慮。

### 修正 (Fixed)
- データ不足時の安全フォールバックを追加:
  - MA200 計算や ATR 計算でデータが不足する場合に中立値（例: ma200_ratio=1.0、None 等）を返す挙動を明示化。
  - カレンダー未登録日の扱いを一貫したフォールバックにより改善。

### セキュリティ (Security)
- センシティブ情報の読み込み:
  - OpenAI API キー等は環境変数から解決する設計（api_key 引数で上書き可能）。必須未設定時は ValueError を投げる。

### 互換性に関する注意 (Notes for Users)
- OpenAI API:
  - news_nlp.score_news および regime_detector.score_regime は OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）を必要とします。キー未設定時は ValueError が発生します。
- 環境変数名（主なもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, KABUSYS_DISABLE_AUTO_ENV_LOAD
- データベーススキーマ（想定テーブル）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などを参照/更新します。これらの存在が前提となる処理が多く含まれます。

### 未実装 / TODO（推定）
- strategy、execution、monitoring パッケージの中身はこのリリースでは公開インターフェースのみが示されている可能性があり、実装が別ブランチ・別モジュールで管理されていることが想定されます。

---

今後のリリースでは、テストカバレッジの追加、各モジュールの外部 API 呼び出し抽象化、monitoring/strategy/execution の充実、パフォーマンス改善（バッチ並列化等）を予定してください。