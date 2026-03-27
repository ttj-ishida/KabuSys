# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
初版リリース (v0.1.0) の内容をコードベースから推測してまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初期リリース。日本株自動売買・データ基盤・リサーチ・AI スコアリングの基礎モジュール群を追加。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンと公開モジュールを追加（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数を自動読み込みするユーティリティを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - export KEY=val やクォート・インラインコメントに対応したパーサを実装。
    - ファイル読み込み失敗時は警告を出力して安全に継続。
  - Settings クラスを提供（settings インスタンスを公開）。
    - 必須環境変数取得メソッド（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - データベースパスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証ロジック。
    - is_live / is_paper / is_dev のヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news, news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実行）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・最大文字数 3000 でトリム。
    - リトライ方針: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出、"results" 配列、各要素の code/score 検証、score を ±1.0 にクリップ。
    - 書き込みは冪等的に実施（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約に配慮。
    - API キーは引数から注入可能（テスト容易性）または環境変数 OPENAI_API_KEY を使用。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロセンチメントは独立実装の LLM 呼び出しで評価（gpt-4o-mini, JSON Mode）。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - API 呼び出し失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に保存。
    - リトライ・エラーハンドリングを実装（RateLimit/接続/タイムアウト/5xx など）。

- データ (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を利用した営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル・健全性チェックを含む）。
    - 最大探索日数やバックフィル、先読み日数等の定数を設定。
  - ETL パイプライン (pipeline.ETLResult, etl の公開)
    - ETLResult dataclass を定義（取得件数、保存件数、品質問題、エラー一覧など）。
    - pipeline モジュールで差分取得→保存→品質チェックのフレームワークを実装（jquants_client, quality を利用）。
    - _get_max_date/_table_exists 等のユーティリティを含む。
    - デフォルトのバックフィル日数等を定義。
  - jquants_client へのインターフェース使用を仮定（fetch/save 関数を呼び出す設計）。

- リサーチ (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を利用し、date と code をキーにした出力を返す。
    - データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存を使わず標準ライブラリのみで実装。
  - research パッケージの __all__ で主要関数を再公開（zscore_normalize を data.stats から再エクスポート）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: AI モジュールやリサーチ関数は datetime.today()/date.today() を直接参照しない。target_date ベースで運用する設計。
- フェイルセーフ: OpenAI API の失敗や部分的な取得失敗は例外でプロセス全体を停止させず、ログ記録して（場合により 0.0 やスキップで）継続する設計。
- 冪等性: DB 書き込みは原則的に冪等（DELETE→INSERT、ON CONFLICT を使う保存設計など）を意図。
- リトライ戦略: OpenAI 呼び出しは RateLimit/接続エラー/タイムアウト/5xx を対象に指数バックオフでリトライ。非再試行エラーはスキップして続行。
- DuckDB 互換性: executemany に empty params を渡せないバージョン（例: 0.10）を考慮した実装が一部にある（空配列チェックなど）。
- OpenAI とのやり取りは JSON Mode（response_format={"type":"json_object"}）想定。レスポンスの前後に余計なテキストが混入するケースを復元する処理を含む。
- テスト容易性: OpenAI 呼び出し部分は内部関数として切り出し、unittest.mock.patch による差し替えを想定。

### Known limitations / TODO（コードから推測）
- strategy、execution、monitoring の具体的な実装は公開モジュールに含まれるが、本差分では詳細が未記載（今後の実装対象）。
- 一部機能は外部クライアント（jquants_client）や quality モジュールに依存するため、利用時はそれらの実装／認証情報が必要。
- OpenAI モデル名やレスポンス仕様に将来の変更があると互換性問題が発生する可能性あり。レスポンスパースは堅牢化されているが完全ではない。

### Required environment variables (主要)
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD (kabuステーション API 用)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能を利用する際）

---

（本 CHANGELOG はコードベースの内容を読み取って自動的に推測したものであり、実際のリリースノートや運用ドキュメントと差異がある場合があります。必要であれば追記・修正します。）