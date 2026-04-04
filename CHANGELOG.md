CHANGELOG
=========
このファイルは Keep a Changelog の形式に従って作成されています。  
バージョニングはセマンティックバージョニングに準拠します。

[Unreleased]
------------

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)
- パッケージ構成（主要モジュール）の追加
  - kabusys.config: 環境変数・設定管理
    - .env / .env.local 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化
    - .env パーサーは export KEY=val、クォート（'"/""）とエスケープ、インラインコメントの扱いに対応
    - OS 環境変数を保護するための protected キーセット処理
    - Settings クラスを公開し、J-Quants / kabuステーション / LINE / DB /監視 / システム設定をプロパティで提供
      - 必須項目取得時は未設定だと ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
      - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証
      - デフォルトの DB パス（duckdb / sqlite）や監視閾値を環境変数で調整可能

  - kabusys.ai
    - news_nlp: ニュース記事のセンチメントスコアリング
      - 対象ウィンドウ: JST 前日15:00 ～ 当日08:30（内部は UTC naive で扱う）
      - 銘柄毎に記事集約（最新最大 _MAX_ARTICLES_PER_STOCK、文字数トリム）
      - OpenAI（gpt-4o-mini）へバッチ送信（1回で最大 20 銘柄）
      - JSON Mode でのレスポンス検証、部分失敗耐性（失敗したチャンクはスキップ）
      - リトライ: レート制限/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ
      - スコアは ±1.0 にクリップ
      - DuckDB 互換性確保: executemany に空リストを渡さないガード
      - テスト用に _call_openai_api の差し替え（unittest.mock.patch）を想定

    - regime_detector: 市場レジーム判定
      - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と
        マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）
      - LLM 呼び出しは gpt-4o-mini、JSON モード、レスポンスパース/エラー処理あり
      - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ
      - レジームは clip と閾値に基づきラベル付け（定数で閾値管理）
      - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施、失敗時は ROLLBACK を試行し上位へ例外伝播

  - kabusys.research
    - factor_research: ファクター計算（Momentum / Value / Volatility / Liquidity）
      - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
      - ボラティリティ: 20 日 ATR、相対 ATR、20 日平均出来高・売買代金、出来高比率
      - バリュー: PER（EPS が無効時は None）、ROE（raw_financials から取得）
      - 全関数は DuckDB で SQL を主体に実装し、prices_daily / raw_financials のみ参照

    - feature_exploration: 特徴量探索・統計
      - 将来リターン計算（指定ホライズンの LEAD による取得、デフォルト [1,5,21]）
      - IC（Spearman の ρ）計算：ランク相関、レコード不足時は None
      - rank ユーティリティ（同順位は平均ランク）
      - factor_summary：count/mean/std/min/max/median を算出

  - kabusys.data
    - calendar_management: マーケットカレンダー管理
      - market_calendar ベースの is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装
      - DB にデータがなければ曜日ベースのフォールバック（週末を非営業日）
      - calendar_update_job: J-Quants API から差分取得 → 保存（バックフィル・健全性チェックあり）
      - 最大探索日数やバックフィル、先読み等の定数設定

    - pipeline / etl: ETL パイプライン
      - ETLResult: ETL 実行結果を表す dataclass（品質問題リスト / エラー集計 / 書き込み件数 等）
      - 差分取得・保存（idempotent 保存を想定）・品質チェックの骨格を実装
      - デフォルトのバックフィルやカレンダー先読み等の方針実装

Changed
- 初回リリースのため "Changed" 項目なし。

Fixed
- 初回リリースのため "Fixed" 項目なし。

Security
- OpenAI API キーや各種トークンは環境変数経由で取得。未設定時は明示的に例外を投げる（AI 関連関数）。
- .env ロード時に OS 環境変数を上書きしないデフォルト動作、必要に応じて .env.local で上書き可能。

Notes / 実装上の重要事項（利用者向け）
- AI 機能を使うには OPENAI_API_KEY が必要（引数で注入可能）。未設定だと ValueError が発生します。
- DuckDB を用いたテーブル（例: prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols, market_calendar 等）が前提です。テーブルが存在しない場合は関連処理は該当データなし扱いまたは早期終了する設計です。
- .env の自動ロードはプロジェクトルートの検出に依存します。パッケージ配布後や CWD に依らない動作を意図していますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化してください。
- DuckDB の executemany は空リストを受け取れないバージョン互換の考慮が施されています（空チェックあり）。
- テスト容易性のため、OpenAI 呼び出し部分はモジュール内で独立実装され、テスト用に差し替え可能（patch を想定）。

Deprecated
- 初回リリースのため非推奨項目なし。

Removed
- 初回リリースのため削除項目なし。

Breaking Changes
- 初回リリースのため破壊的変更なし。

移行 / 利用開始ガイド（簡易）
- 環境変数を用意する:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（機能利用に依存）
  - AI 機能: OPENAI_API_KEY
  - 必要に応じて KABUSYS_ENV=development|paper_trading|live, LOG_LEVEL 等を設定
- DuckDB データベースを準備し、必要なテーブルを作成しておく（prices_daily, raw_news, raw_financials, news_symbols, ai_scores, market_calendar, market_regime 等）
- AI 機能をテストする場合は _call_openai_api をモックしてレスポンス検証が可能

Acknowledgements / Contributors
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しました。実際の貢献者リストはリポジトリのコミット履歴に基づいて追記してください。

--- 
（この CHANGELOG はコードの実装内容から推測して作成されています。実際のリリースノート作成時はコミットログや PR 説明を参照の上、適宜更新してください。）