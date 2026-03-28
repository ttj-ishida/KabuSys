# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

履歴は後方互換性の保証を必ずしも意味しません。重要な設計判断・既知の挙動・必要な環境変数などは各リリースの説明に含めています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムのコアライブラリを公開します。主に以下の機能・モジュールを実装しています。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージ初期版を追加。バージョン: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env/.env.local からの自動環境変数ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行い、CWD に依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースはコメント、export プレフィックス、クォートやバックスラッシュエスケープを考慮して堅牢に実装。
    - OS 環境変数の保護（既存のキーを保護する protected セット）をサポート。
  - Settings クラスを提供し、環境変数経由で主要設定にアクセス可能に：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のブールヘルパー

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダー管理と営業日判定ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の際の曜日ベースのフォールバック（週末除外）をサポート。
    - calendar_update_job により J-Quants API からの差分取得 → 冪等保存（ON CONFLICT）を行う。バックフィル・健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを導入（ETL 実行結果の構造化）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）などの設計に対応するユーティリティ。
    - _table_exists / _get_max_date のユーティリティを実装。
  - etl モジュールで ETLResult を公開再エクスポート（kabusys.data.ETLResult）。

- AI（自然言語処理） (kabusys.ai)
  - news_nlp モジュール
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON mode でセンチメント評価。
      - バッチサイズ、記事数・文字数の上限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
      - レスポンスの厳密なバリデーションとスコアクリッピング（±1.0）。不正応答はスキップしてフェイルセーフに処理。
      - 成功した銘柄のみ ai_scores テーブルに DELETE → INSERT の冪等更新（トランザクション）を実行。
    - calc_news_window(target_date) を提供（前日15:00 JST ～ 当日08:30 JST を UTC naive で計算）。
    - JSON レスポンスパース時の前後余計テキスト抽出ロジックなど堅牢化を実装。
  - regime_detector モジュール
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
      - _calc_ma200_ratio によるルックアヘッド防止（target_date 未満のデータを使用）、データ不足時のフェイルセーフ（中立）。
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出、OpenAI 呼び出しで macro_sentiment を算出（失敗時は 0.0 にフォールバック）。
      - OpenAI 呼び出しは独立実装（モジュール結合を最小化）。
      - トランザクション（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK の安全処理を実装。
  - 公開 API:
    - kabusys.ai.score_news（ai/__init__.py でエクスポート）
    - kabusys.ai.regime_detector モジュール経由で score_regime を利用可能

- リサーチ / ファクター (kabusys.research)
  - factor_research モジュール
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)
      - 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算。NULL 伝播を考慮した true_range 実装。
    - calc_value(conn, target_date)
      - raw_financials の最新財務（report_date <= target_date）と当日の株価を組み合わせて PER / ROE を算出。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で取得。horizons の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank(values)
      - 同順位は平均ランクを与えるランク変換（round により ties の安定化）。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を計算する統計サマリー（None は除外）。

- ロギング & エラーハンドリング
  - 各コンポーネントで詳細な logger 呼び出しを追加（info/warning/debug/exception）。
  - OpenAI 呼び出し時の再試行ロジック、5xx とそれ以外の判別、API の失敗でのフォールバック方針を明示。
  - DB 書き込み時はトランザクションと ROLLBACK を適切に扱い、ROLLBACK 失敗時の警告ログを追加。

### 設計上の注意点 / 既知挙動 (Notes)

- ルックアヘッドバイアス防止
  - AI スコアリング系・レジーム判定・ファクター計算はいずれも内部で datetime.today()/date.today() を直接参照せず、呼出し側が target_date を与える設計になっています。
  - DB クエリは target_date 未満 / 以前の条件を明示してルックアヘッドを防止しています。

- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は ValueError を送出します。
  - 使用モデルは gpt-4o-mini（定数で管理）。JSON mode を前提とした厳密パース処理を行っています。

- DuckDB との互換性
  - DuckDB のバージョン差異（executemany での空リスト等）に配慮した実装（空リストチェック等）。
  - SQL 中の ROW_NUMBER / WINDOW 関数を多用しています。対象テーブル（prices_daily, raw_news, news_symbols, raw_financials, ai_scores, market_regime, market_calendar 等）のスキーマを前提とします。

- フォールバック動作
  - カレンダーデータ未取得時は曜日ベースで営業日判定を行うため、calendar_update_job を実行する前でも基本的な判定は機能します。
  - AI API の一時的失敗（ネットワーク/429/5xxなど）は再試行・最終的に 0.0 やスキップでフェイルセーフとなります（例外を上げず処理を継続）。

### 依存関係（実行に必要な外部ライブラリ / 環境）
- duckdb（DB 操作）
- openai（OpenAI API クライアント）
- jquants_client（kabusys.data.jquants_client として想定される外部モジュール）
- 環境変数設定のため .env/.env.local の配置を推奨

### 破壊的変更 (Breaking Changes)

- 初回リリースにつき該当なし。

### セキュリティ / 秘匿情報取り扱い

- 環境変数（API キー・パスワード等）を利用する設計のため .env ファイル・環境変数の管理に注意してください。Settings._require は未設定時に ValueError を投げます。

---

フィードバック・バグ報告・改善提案は issue を通じてお願いします。