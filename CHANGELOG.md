# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本リポジトリは初回リリース（v0.1.0）相当のコードベースから作成されています。以下はコード内容から推測してまとめた変更点・機能/設計の説明です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-29

Added
- 初期リリース。
- パッケージ名: kabusys。パッケージのバージョンは `__version__ = "0.1.0"`。
- パブリック API のエントリーポイント: `kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 環境変数 / 設定管理
  - `kabusys.config.Settings` を追加。環境変数または .env ファイルから設定を取得するユーティリティを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env → .env.local の順で読み込み。
    - OS 環境変数が保護されるよう protected keys を扱い、.env.local は上書き（override）を許可。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能（引用符、エスケープ、export 形式、インラインコメント処理などをサポート）。
  - 既定の設定と必須設定:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - 任意/デフォルト: KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）、DUCKDB_PATH（default: data/kabusys.duckdb）、SQLITE_PATH（default: data/monitoring.db）。
    - 環境: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかのみ許可。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール:
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON モードでセンチメントを評価して ai_scores テーブルへ書き込む。
      - 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC で前日 06:00 ～ 23:30）。時間ウィンドウ計算ユーティリティ calc_news_window を提供。
      - バッチ処理: 1 回の API コールで最大 20 銘柄（_BATCH_SIZE=20）。
      - 出力バリデーション: JSON 解析、"results" リスト、コード整合性、数値チェック、スコア ±1.0 にクリップ。
      - リトライ/フォールバック: 429（レート制限）、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ。致命的でない失敗はログ出力してスキップ（フェイルセーフ）。
      - テストしやすい設計: OpenAI 呼び出し箇所を patch 可能（_call_openai_api を差し替えられる）。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日本225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム ('bull'/'neutral'/'bear') を判定。
      - ma200_ratio の計算は prices_daily から target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
      - マクロ記事が存在する場合のみ OpenAI を呼び、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - レジームスコアはクリップされ、閾値によりラベル付け。
      - 結果は market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
      - OpenAI 呼び出しもテスト差し替え可能に設計。

- Data（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar）ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days など営業日判定機能を実装。
    - DB にカレンダーがない場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィル、健全性チェックあり）。
    - 最大探索日数、バックフィル日数など安全対策を実装している。
  - pipeline / etl:
    - ETLResult dataclass を提供（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得数／保存数／品質問題／エラー一覧を保持。has_errors / has_quality_errors / to_dict 等のユーティリティを持つ。
    - 差分更新・バックフィル・品質チェックの設計に基づいた構成（quality モジュールとの連携想定）。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得など。

- Research（kabusys.research）
  - factor_research モジュール:
    - calc_momentum(conn, target_date)
      - 約1ヶ月/3ヶ月/6ヶ月リターン、200日 MA 乖離（ma200_dev）を計算。
      - データ不足時は None を返す。SQL ウィンドウ関数を利用して効率的に計算。
    - calc_volatility(conn, target_date)
      - 20日 ATR、ATR 比率、20日平均売買代金、出来高比率などを計算。true_range の NULL 伝播に注意した設計。
    - calc_value(conn, target_date)
      - raw_financials から最新の財務データを取得して PER / ROE を計算。EPS=0 や欠損時は None。
      - PBR・配当利回りは未実装であることを明示。
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力制約あり（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank(values)
      - 平均ランク（同順位は平均）を算出。丸めで ties の検出漏れを防ぐ設計。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を算出する統計サマリー。

- その他
  - DuckDB を前提とした SQL 実装が多用されている（prices_daily, raw_news, market_regime, ai_scores, raw_financials, market_calendar 等）。
  - 多くの箇所で「ルックアヘッドバイアス防止」の設計が徹底されている（datetime.today() や date.today() を使用しない、SQL クエリの範囲を target_date 未満に制限など）。
  - OpenAI は gpt-4o-mini を指定、JSON Mode（response_format={"type": "json_object"}）を利用する想定。
  - API 呼び出しでのリトライ（指数バックオフ）、および非致命的失敗時のログフォールバックを多くのモジュールで採用。
  - テスト容易性のため OpenAI への実呼び出し箇所は差し替え可能に実装されている（patch 用の内部関数が明示）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Known issues / Notes
- news_nlp の出力に依存するため、LLM の挙動（JSON モードでも余分なテキストが付与される等）に対して復元処理を実装しているが、LLM 出力の多様性により完全ではない場合がある。
- calc_value では PBR・配当利回りは未実装（将来追加予定）。
- DuckDB の executemany に空リストが与えられると失敗する制約への対応がコード内にあり、運用時は互換性に注意。
- OpenAI API キーが未設定の場合、score_news/score_regime は ValueError を送出する（呼び出し側でキーを注入する必要がある）。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client の実装）に依存する。API 呼び出し失敗時は 0 を返して安全に終了する設計。

---

この CHANGELOG は現状のコードベースから推測して作成しています。実際の運用・リリースノートはリポジトリの履歴（コミット・タグ）に基づき更新してください。