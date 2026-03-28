# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ導入
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開インターフェース: kabusys.data / kabusys.strategy / kabusys.execution / kabusys.monitoring（__all__ にて公開）

- 環境設定・ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード機能を追加。CWD に依存しない探索。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサ実装（export KEY=val の形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。
  - _load_env_file の override/protected オプションにより OS 環境変数を保護しつつ .env.local で上書き可能。
  - Settings クラスを導入し、アプリケーション設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得（未設定時に ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を設定。
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）を検証。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- AI（自然言語）モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive に変換して扱う）。
    - バッチサイズ、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証（JSON 抽出、results 配列・型検査、未知コードの無視、スコア数値化、±1.0 クリップ）。
    - 書き込みは部分的に安全な方式（取得したコードのみ DELETE → INSERT）で実行し、DuckDB の executemany 空リスト制約に配慮。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - API 呼び出し部はテストで置き換え可能（unittest.mock.patch 用の内部関数）。
    - API 失敗時はスキップして継続するフェイルセーフ設計。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を使ってウィンドウを決定し、raw_news からマクロキーワードでフィルタ。
    - OpenAI（gpt-4o-mini）呼び出しと JSON パース、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。API 失敗時は macro_sentiment=0.0 として処理継続（フェイルセーフ）。
    - レジームスコア合成、閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - ルックアヘッドバイアス防止のため、クエリは target_date 未満のみを参照し、datetime.today() を参照しない設計。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - market_calendar を使った営業日判定ロジックの実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB に calendar データがあれば優先して使用し、未登録日は曜日ベース（平日）でフォールバックする一貫した挙動。
    - 最大探索日数の制限と安全性チェックを実装（無限ループ防止）。
    - calendar_update_job により J-Quants API から差分取得 → market_calendar に冪等保存（fetch/save は jquants_client 経由）。
    - バックフィル（直近 N 日を再フェッチ）と最終取得日の健全性チェックを実装。

  - pipeline / ETL:
    - ETLResult データクラスを追加。ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分更新、backfill、品質チェック（quality モジュールとの統合）を想定したパイプライン用ヘルパーを実装（テーブル存在チェック、最大日付取得等）。
    - 設計上、品質チェックは例外で処理を止めない（呼び出し元で評価）。

  - etl.py は ETLResult を再エクスポート。

- リサーチ・ファクター分析（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS = 0/欠損時は None）。
    - すべて DuckDB の prices_daily / raw_financials のみ参照、外部 API による副作用なし。
    - 結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日ベース）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクで扱うランク変換。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージの __all__ に主要関数を公開。zscore_normalize は kabusys.data.stats から再利用している。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 実装上の設計判断
- ルックアヘッドバイアス防止: AI モジュールや研究モジュールは内部で datetime.today()/date.today() を参照しない設計（すべて target_date ベース）。
- OpenAI 呼び出しは JSON Mode を利用しレスポンスの構造化を試みるが、リトライ政策・レスポンスパース失敗時のフォールバックを厳密に実装しており、外部 API の不安定さを考慮した堅牢性を重視。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 等を前提）し、トランザクションと ROLLBACK による保護を実装。
- テスト容易性のため、内部の API 呼び出しラッパー（_call_openai_api 等）をモック差し替え可能にしている。
- DuckDB の executemany の制約（空リスト不可）に対応したガードを実装。

---

今後の予定（例）
- strategy / execution モジュールの詳細実装（実注文フロー、paper/live モード切替）
- monitoring 用のデータベース蓄積・アラート連携（Slack 通知等）の追加
- より多様なファクター・リスク管理ロジックの導入

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて更新してください。）