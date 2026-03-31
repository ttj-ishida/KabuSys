# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って管理されています。  
主な変更点は下記のリリースノートに記載します。

全ての変更は SemVer に従います。  

---

## [Unreleased]
- （未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。以下はコードベースから推測してまとめた実装内容と設計上の重要ポイントです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの順序: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサ実装（コメント、export プレフィックス、クォート／エスケープ対応、インラインコメント処理等）。
  - 環境変数の取得ヘルパと必須チェック（_require）。
  - Settings クラスを提供（プロパティ経由で設定を取得）。
    - 主要プロパティ例:
      - JQUANTS_REFRESH_TOKEN（jquants_refresh_token）
      - KABU_API_PASSWORD / KABU_API_BASE_URL
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリミング（最大記事数・最大文字数）を実装。
    - JSON Mode を使いレスポンスを厳密に検証。パース失敗や不正レスポンスは安全にスキップ。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx をエクスポネンシャルバックオフでリトライ。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。window 計算は calc_news_window 関数で明確化。
    - 戻り値: 書き込んだ銘柄数（int）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロセンチメントを計算し、market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出し部分は独立実装で、API の失敗は macro_sentiment=0.0 としてフォールバックするフェイルセーフ。
    - リトライ（RateLimit, 接続エラー, タイムアウト, 5xx）を行う実装。

- データ関連モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ロジックを提供。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB データがない場合の曜日ベースフォールバック（週末を非営業日扱い）。DB 値があれば優先。
    - 夜間バッチ calendar_update_job により J-Quants API から差分取得→保存（バックフィル・健全性チェックあり）。
  - ETL とパイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py は ETLResult を再エクスポート）。
    - 差分取得、保存、品質チェックのフレームワークを実装する設計（J-Quants クライアントと quality モジュール連携を想定）。
    - 最終取得日の算出ユーティリティ、テーブル存在チェックなどを実装。
    - バックフィル日数の取り扱い、calendar の先読みなどを考慮。
  - jquants_client（参照のみ: calendar_management などで想定され使用）を介した外部データ取得を想定。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily 参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から PER・ROE を算出（直近の財務データを JOIN）。
    - 各関数は date, code をキーとした dict のリストを返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 将来リターン（複数ホライズン）を一発クエリで取得可能。
    - calc_ic: スピアマンランク相関（IC）を計算。最小有効レコード数のチェックを実装。
    - rank: ランク計算（同順位は平均ランク、丸めによる ties 対応）。
    - factor_summary: カラムごとの基本統計量（count, mean, std, min, max, median）を計算。
  - zscore_normalize は kabusys.data.stats から再利用可能に設計（research/__init__ で再エクスポート）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で渡すか環境変数 `OPENAI_API_KEY` を使用する設計。未設定時は ValueError を送出し誤動作を防止。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set を用いた上書き制御）を実装。

### 設計上の注記 / フェイルセーフ
- ルックアヘッドバイアス防止:
  - 各 AI / ETL / research モジュールは内部で datetime.today() / date.today() を直接参照しない。target_date を外部から与える方式で実装。
  - DB クエリは date < target_date / date BETWEEN などの排他条件を明確に使用。
- OpenAI 呼び出しは JSON Mode を利用し厳密にパース。パース失敗や不正レスポンスはログとともにフォールバック（通常は 0.0 やスキップ）し、処理全体は継続するフェイルセーフ設計。
- テスト容易性:
  - OpenAI 呼び出しラッパー（各モジュール内の _call_openai_api）を patch してテスト可能。
  - .env 自動ロードは環境変数で無効化可能（テスト用）。
- DuckDB 側の互換性への配慮:
  - executemany に空リストを渡さないチェックなど、DuckDB バージョン差異を考慮した実装。

---

その他の参考情報
- データベース表名（コードから参照される主要テーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials
- 環境変数の主なキー
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY

---

貢献・バグ報告・改善提案は Issue/PR で受け付けてください。