# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/ 以下）の内容から推測して作成しています。

注記: バージョン番号はパッケージの __version__ = "0.1.0" に合わせています。

## [Unreleased]

- 今後の予定（推測）
  - ai モジュールの追加モデル対応（モデル選択の外部化）
  - jquants_client の具体的実装例・テスト用モックの追加
  - データ品質チェック機能（quality モジュール）の強化と UI/レポート化
  - DuckDB スキーマ定義 / 初期化スクリプトの付属化

---

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買 / データ基盤 / リサーチ用ユーティリティ群を提供。
- 基本構成
  - パッケージエントリポイント: `kabusys`（__init__ にて data, strategy, execution, monitoring を公開）。
  - バージョン情報: `__version__ = "0.1.0"`。

- 環境設定管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパースロジックを細かく実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、コメント扱いのルール）。
  - Settings クラスを提供し、主要設定をプロパティで取得:
    - J-Quants / kabuステーション / Slack / DB パス / 環境(env)/ログレベル等。
    - 必須項目未設定時は ValueError を送出する `_require` を実装。
    - `env` と `log_level` は許容値チェックを行い不正値は例外を送出。
    - `duckdb_path`, `sqlite_path` は Path オブジェクトで取得。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約し銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）で一括センチメント評価。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの最大記事数と最大文字数でトリム。
    - レスポンス JSON のバリデーションとスコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し関数を patch で差し替え可能に設計。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロ記事抽出はキーワードリストでフィルタし、最大件数制限あり。
    - OpenAI 呼び出しは JSON モードを利用し、失敗時は macro_sentiment=0.0 でフォールバック。
    - 結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行し例外を再送出。
    - OpenAI クライアントは `OpenAI(api_key=...)` を利用。API キー未提供時は明示的な ValueError を送出。

- リサーチ / ファクター処理 (`kabusys.research`)
  - ファクター計算群 (`factor_research`)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: raw_financials から最新財務を取得して PER（EPS が 0/欠損なら None）と ROE を算出。
    - すべて DuckDB を用いた SQL ベース実装で外部 API への依存なし。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（calc_forward_returns）: デフォルト [1,5,21] 営業日。horizons の妥当性チェックあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関に基づく実装。3 レコード未満で None を返す。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を提供。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。

- データ基盤 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX 市場カレンダー管理ロジック、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを実装。
    - market_calendar が未取得の場合は曜日（平日のみ営業）によるフォールバックを使用。
    - calendar_update_job により J-Quants から差分取得 → 市場カレンダーを冪等で保存（fetch/save を jquants_client に委譲）。
    - バックフィル・健全性チェック（将来大幅に日付がある場合スキップ）等を実装。
  - ETL パイプライン (`pipeline.ETLResult`, `etl` の公開)
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーメッセージ等を集約）。
    - 差分更新・バックフィル・品質チェック方針の設計（コメントとして明記）。
    - DuckDB の最大日付取得やテーブル存在チェック等のユーティリティ関数を実装。
    - DuckDB の executemany の空リスト制約（0.10 で問題になる点）を回避するための防護実装。

- 汎用的な設計上の注意点（ドキュメントとしてコード内に明記）
  - datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。全 API は target_date 引数で日付を受け取る設計。
  - OpenAI 呼び出しはテストで差し替え可能（モックしやすい）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 等を想定）。
  - ネットワーク/API エラーはフェイルセーフで継続する設計（必要な場面ではログ警告・部分スキップ）。

### Changed
- 初期リリースにつき「変更」よりは仕様の確定を記載
  - DuckDB と連携する関数は明示的に connection を受け取り、テスト・実行環境を分離。
  - OpenAI 呼び出しのレスポンス処理は JSON モード前提で厳密にパースし、余分な前後テキストが混ざる場合のリカバリを実装。

### Fixed
- 安定性向上のための例外処理強化:
  - OpenAI API 呼び出しの各種エラー（RateLimit/Connection/Timeout/5xx）に対してリトライ戦略を実装し、最終的にフォールバック動作（0.0 スコア等）を行う。
  - DB 書き込みの失敗時に ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告ログを出力する実装。

### Security
- 環境変数による機密情報（OpenAI API キー等）を想定し、Settings で必須チェックを行う。自動ロードを無効化できるフラグを提供。

### Compatibility / Notes
- 必須環境変数:
  - `OPENAI_API_KEY`（score_news / score_regime 呼び出し時に省略可能だが、未指定なら ValueError）
  - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` は Settings で必須としている（使用箇所に依存）。
- DuckDB スキーマ（期待するテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などがコードの各所で参照される。これらのテーブル定義は別途用意する必要あり。
- DuckDB バージョン特性
  - executemany に空リストを渡せない問題（DuckDB 0.10 を想定）に対する防護コードを含む。
- タイムゾーン
  - news の時間ウィンドウやカレンダーは UTC naive datetime を前提に内部で計算（JST→UTC の固定変換ロジックを使用）。
- テスト容易性
  - OpenAI 呼び出しをラップした内部関数は patch で差し替えられる設計になっているため、ユニットテストで API をモック可能。

---

作者注: 上記は src/ 以下のコードとドキュメント文字列から推測して作成しています。実際のリリースノートでは、変更日・具体的なマイグレーション手順・既知の制限・既存ユーザーへの影響（breaking changes）があればそれらを補足してください。