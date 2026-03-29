CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。日本株自動売買プラットフォーム「kabusys」のコア機能を実装。
  - パッケージメタ情報
    - pkg: kabusys、バージョン 0.1.0 を __version__ に設定。
  - 設定管理 (kabusys.config)
    - .env / .env.local の自動読み込み実装（プロジェクトルート判定は .git または pyproject.toml を参照）。
    - export 文形式、クォート有無、インラインコメント等に対応した .env パーサー実装。
    - OS 環境変数を保護する protected オプション、.env.local が .env を上書きする優先度ルールを採用。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等の取得と検証を行う（不正値は ValueError）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - AI モジュール (kabusys.ai)
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news と news_symbols をもとに銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
      - バッチサイズ、トリム文字数、最大記事数等の肥大化対策を実装。
      - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフリトライ実装。失敗時はスキップして継続（フェイルセーフ）。
      - レスポンスの堅牢な検証とスコアの ±1.0 クリップ。
      - calc_news_window により JST の前日 15:00 ～ 当日 08:30 のウィンドウ（内部は UTC naive datetime）を提供。
      - テスト容易性のため、API 呼び出し部分は差し替え（patch）可能に設計。
      - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。API キー未設定時は ValueError。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
      - OpenAI（gpt-4o-mini）の JSON モードを使用。最大リトライ・バックオフ・5xx 分岐を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
      - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
      - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キー未設定時は ValueError。
  - データモジュール (kabusys.data)
    - カレンダー管理（kabusys.data.calendar_management）
      - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し保存。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
      - 探索の最大日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを導入して安全性を担保。
    - ETL パイプライン（kabusys.data.pipeline）
      - ETL の設計（差分取得、保存、品質チェック）に基づくユーティリティを実装。
      - ETLResult dataclass を定義し、取得/保存件数・品質問題・エラー情報を集約。to_dict により品質問題をシリアライズ可能。
      - 内部で DuckDB テーブルの最大日付取得やテーブル存在チェックを提供。
    - etl モジュールから ETLResult を再エクスポート（kabusys.data.etl）。
    - jquants_client / quality 等のクライアント抽象を想定した設計（実際のクライアントは別モジュールとして参照）。
  - Research モジュール (kabusys.research)
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を計算。データ不足時は None。
      - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比等を計算。必要行数未満は None。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS=0/欠損は None）。
      - 全関数は DuckDB の prices_daily / raw_financials を参照し、外部 API にアクセスしない設計。
    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
      - calc_ic: Spearman ランク相関（Information Coefficient）を計算。有効レコードが 3 未満なら None。
      - factor_summary: 指定カラムの基本統計量（count/mean/std/min/max/median）を算出。
      - rank: 同順位は平均ランクとするランク化実装（丸めによる ties 処理あり）。
    - research パッケージの公開 API を __all__ で整理（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - 共通事項
    - データベースは DuckDB を想定し、DuckDB 接続オブジェクトを関数引数として受ける設計。
    - 全体的に「ルックアヘッドバイアスを防ぐ」ため、date.today() / datetime.today() を直接参照しない実装方針を徹底（target_date に依存）。
    - OpenAI 呼び出しは API キー注入（引数 or 環境変数 OPENAI_API_KEY）を必須にし、テストのため差し替え可能な設計。
    - ログ出力（logger）を各モジュールで使用し、失敗やフォールバック時は WARNING/INFO/DEBUG を適切に記録。
    - DB 書き込みは可能な限り冪等に設計（DELETE → INSERT や ON CONFLICT 相当の保存等）。
    - エラー時はフェイルセーフ: API 失敗やパース失敗は局所的にログ記録して処理を継続（例外を上げないケースが多い）。ただし DB 書き込み失敗は上位へ伝播。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- OpenAI API キーなどの機密値は Settings 経由で取得する設計。.env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

注記 / マイグレーションガイド
- OpenAI 関連
  - score_news / score_regime は api_key を引数で受け取れます。CI/本番では環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
  - モデルは gpt-4o-mini を想定し、JSON Mode を使用しています。API 応答のパースは堅牢化されていますが、SDK の挙動変化に注意してください。
- データベース
  - DuckDB を使用するため、接続オブジェクト（DuckDBPyConnection）を各関数に渡してください。DuckDB のバージョン差異（executemany の空リスト制約等）に配慮した実装になっています。
- カレンダー / ETL
  - calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を呼び出します。実運用では該当クライアントの実装と API 資格情報の準備が必要です。
- テスト
  - OpenAI 呼び出し箇所は _call_openai_api をパッチすることでモック化可能です（ユニットテスト用のフックを提供）。

開発上の設計決定（要約）
- ルックアヘッドバイアスを防ぐため、全ての「当日」参照は明示的な target_date に基づく。これにより再現性のあるバッチ処理とテストが可能。
- 外部 API の失敗は局所的にフォールバックして継続するフェイルセーフ設計（部分失敗の影響を最小化）。
- DuckDB と SQL ウィンドウ関数を多用して大量データを効率的に集計。
- Idempotent な DB 操作とログによる監査性の重視。

今後の予定（未実装・拡張案）
- PBR・配当利回りなどの追加バリュー指標の実装。
- Slack 通知用のユーティリティ（Settings に Slack トークンはあるが使用箇所は今後追加予定）。
- jquants_client / kabu API 実装の具体化とエンドツーエンドの ETL ジョブ統合。
- モデル切替・プロンプトチューニング用の構成機構強化。

---