# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  
このパッケージはセマンティックバージョニングに従います。

全般的な設計方針（コードベース全体に共通）
- ルックアヘッドバイアス防止のため、date/datetime の基準は関数引数の target_date を用い、datetime.today()/date.today() を業務ロジックで直接参照しない設計が採用されています。
- DuckDB を一次データストアとして想定し、SQL と Python を組み合わせた処理を行います。DB 書き込みは冪等（DELETE→INSERT / ON CONFLICT 等）を意識しています。
- OpenAI（gpt-4o-mini）呼び出しにはリトライ／エクスポネンシャルバックオフを導入し、API障害時は例外を投げずフォールバックやスキップで安全性を確保します。
- テスト容易性を考慮し、外部API呼び出し部（OpenAI呼び出し等）を差し替え可能にしています（ユニットテストでのモックが容易）。
- DuckDB バージョン差異への互換性考慮（executemany の空パラメータ回避や配列バインド回避など）を行っています。

Unreleased
- なし

[0.1.0] - 2026-03-28
Added
- パッケージ初期リリース。
- パブリック API:
  - パッケージルート: kabusys.__version__ = "0.1.0"、__all__ = ["data", "strategy", "execution", "monitoring"] を定義。
- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序と上書きルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を提供。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート外）に対応。
  - Settings クラスを提供し、各種必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やパス（DUCKDB_PATH、SQLITE_PATH）、環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証を実装。
  - 環境値の検証に不正値検出時は ValueError を送出する設計。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを生成し、OpenAI（gpt-4o-mini）の JSON mode を用いて一括（最大 20 銘柄 / チャンク）でセンチメントを取得。
    - トークン肥大対策: 1銘柄あたり記事数上限(_MAX_ARTICLES_PER_STOCK=10)、文字数上限(_MAX_CHARS_PER_STOCK=3000) を設定。
    - レスポンスの堅牢なバリデーション実装（JSONパース補正・"results" 構造検証・コード検査・数値チェック・スコアクリップ）。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）は指数バックオフでリトライ、その他はスキップ。失敗時は部分的にスコアを無視して継続。
    - 書き込みは部分失敗で既存データを消さないよう、取得済みコードのみ DELETE → INSERT する方式を採用。
    - テスト用フック: OpenAI 呼び出し箇所は _call_openai_api を経由しており、unit test でパッチ可能。
    - calc_news_window: JSTベースの収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC naive datetime に変換）を提供。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA200 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。データ不足時は中立（1.0）を採用してフォールトトレラントに処理。
    - マクロニュース抽出はタイトルベースでキーワードフィルタリング（複数キーワード）し、最大件数制限あり。
    - OpenAI 呼び出しに対するリトライ戦略と非同期に備えたエラーハンドリング（APIError の status_code を安全に扱う）を実装。API失敗時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）を実装。
- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録ありの場合は登録値優先、未登録日は曜日フォールバックで補完する一貫した挙動。
    - calendar_update_job: J-Quants クライアント経由でカレンダー差分取得 → market_calendar へ冪等保存。バックフィル（直近 _BACKFILL_DAYS）・健全性チェック実装。
  - ETL パイプライン (pipeline / etl)
    - ETLResult データクラスを実装し、ETL 実行結果（取得件数、保存件数、品質問題、エラー概要）を返却可能。
    - 差分取得・バックフィル・品質チェック（quality モジュール呼び出し）を想定した設計。J-Quants クライアントを用いた idempotent な保存を前提。
  - jquants_client のラッパーを利用する設計（fetch/save 関数呼び出しを想定）。
- リサーチ機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ / 流動性（20日 ATR、相対ATR、20日平均売買代金、出来高比率）、バリュー（PER、ROE）などの計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL を駆使して窓関数等で高速に集計。データ不足時は None を返すなど堅牢性を確保。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: target_date から指定ホライズン（デフォルト [1,5,21]）までのリターンを一括で取得する SQL ベースの実装。horizons のバリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装し、データ不足（有効レコード<3）時は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクにし、浮動小数の丸めによる tie 判定漏れを防ぐため round(..., 12) を使用。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算するユーティリティ。
- その他ユーティリティ
  - 複数モジュールで OpenAI クライアント呼び出しは client.chat.completions.create(..., response_format={"type":"json_object"}) を用いる想定で実装。テスト時に差し替え可能。

Changed
- 初回リリースのため、API を安定させるために上記設計上の命名・戻り値・例外仕様を確定。

Fixed
- OpenAI API 呼び出しや DB 書き込みでの部分失敗時にアプリ全体が停止しないよう、フォールトトレラントな挙動（例: APIエラーでのマクロスコア=0.0フォールバック、スコアレスポンス無効時のスキップ、DB トランザクションの ROLLBACK ハンドリング）を多数導入。

Security
- 環境変数に依存する API キーやトークンは Settings 経由で明示的に取得する設計。未設定時は ValueError を送出して安全に検出可能。

Notes / Implementation details
- DuckDB の互換性問題（executemany に空リストを渡せない等）に対して注意深く回避処理を実装しています。
- news_nlp と regime_detector は OpenAI 呼び出しを独立して実装しており、モジュール間でプライベート関数を共有しないことで結合度を下げています。
- タイムゾーンは内部で UTC naive datetime を使用する箇所があり（ニュースウィンドウ等）、明示的な JST→UTC 変換ロジックをコメントで説明しています。

既知の制約・今後の改善点（将来対応予定）
- モデルや API のバージョン変更に伴うパラメータ調整や SDK 互換性の確認が必要（OpenAI SDK の変更に弱い部分が存在）。
- current バージョンでは PBR や配当利回りなど一部バリューファクターは未実装（calc_value にて注記あり）。
- 一部関数は外部 jquants_client / quality モジュール実装に依存しており、本パッケージ単体で完結しない箇所がある（連携により機能する設計）。

---

以上がこのコードベースから推測して作成した CHANGELOG.md の内容です。必要であれば、各変更項目をより短く／詳細に分割したり、リリース日や著者情報を追加したりできます。どの形式がよいか教えてください。