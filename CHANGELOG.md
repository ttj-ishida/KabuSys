# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います: MAJOR.MINOR.PATCH

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（monitoring は将来的に実装を想定）。

- 環境設定 / .env ローダー (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の行パーサー実装（export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 読み込み時の挙動:
    - 優先順位: OS環境変数 > .env.local > .env
    - .env.local は override=True（ただし既存の OS 環境変数は protected で上書き不可）
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得:
    - J-Quants / kabu / LINE / DB (duckdb, sqlite) / 監視閾値 / システム環境 (env, log_level) 等のプロパティを実装
    - 必須項目未設定時は _require が ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- AI 関連機能 (kabusys.ai)
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを取得。
    - バッチ処理、1チャンクあたり最大20銘柄、1銘柄あたり最大10記事・3000文字にトリム。
    - JSON Mode を利用し、レスポンスのバリデーション（results 配列、code/score の検証、未知コード除外、スコアの ±1.0 クリップ）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - テスト用に _call_openai_api を patch して差し替え可能。
    - calc_news_window を提供（タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC naive datetime で返す）。
    - score_news は取得したスコアのみを対象に ai_scores テーブルへ DELETE → INSERT の形で冪等的に書き込む（部分失敗時に他のコードを保護）。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の直近200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は predefined なマクロキーワードで raw_news からタイトルを取得（最大20件）。
    - OpenAI への呼び出しは gpt-4o-mini / JSON Mode、レスポンスパース失敗や API エラーは macro_sentiment=0.0 にフォールバック。
    - リトライ・バックオフ戦略を実装（RateLimit / 接続エラー / タイムアウト / 5xx を考慮）。
    - 計算結果（regime_score, regime_label, ma200_ratio, macro_sentiment）を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を上位に伝播。

- 研究 (research) モジュール (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR（平均 true range）、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: EPS/ROE から PER/ROE を算出（raw_financials と prices_daily を参照、最新の報告日を取得）。
    - 設計上、外部 API への依存はなく DuckDB と SQL を中心に実装。
  - feature_exploration モジュール
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21 営業日）を LEAD を用いて一括計算。
    - calc_ic: スピアマンランク相関（IC）を実装（結合と欠損除外、3 銘柄未満は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。
  - research.__init__ で主要関数を再エクスポート。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - DB 登録がある場合は DB 値優先、未登録は曜日ベース（週末）でフォールバック
      - 最大探索範囲を設けて無限ループ防止
    - calendar_update_job を実装（J-Quants API クライアント経由で差分取得 → 保存、バックフィル・健全性チェックあり）
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass を実装（取得数/保存数/品質問題/エラー情報を保持、to_dict メソッドあり）。
    - 差分取得・保存・品質チェックの設計に対応するユーティリティ（jquants_client / quality と連携する想定）。
  - etl モジュールは ETLResult を再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げて安全に停止。

### 設計上の注意点 / 動作保証
- ルックアヘッドバイアス対策: すべての "target_date" ベースの関数は内部で datetime.today() / date.today() を参照せず、過去データのみを使用するよう設計されています。
- フェイルセーフ: AI API の失敗時はスコアを 0.0 にフォールバックしたり、該当チャンクをスキップするなどして全体処理を止めない設計です（ログ出力あり）。
- テスト容易性: OpenAI 呼び出し部分はモジュール内の _call_openai_api を patch して差し替え可能。
- DuckDB 互換性: executemany に空のパラメータを渡さない等、DuckDB の挙動差分に配慮した実装が行われています。

---

注: 実装はコードベースから推測して記載しています。実際の外部 API クライアント実装（jquants_client 等）や strategy / execution / monitoring の詳細実装はこのリリース時点では含まれていないか、別モジュールで提供される想定です。