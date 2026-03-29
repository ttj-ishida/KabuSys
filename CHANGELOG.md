# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買 / リサーチプラットフォームのコア機能を提供します。

### 追加
- パッケージ構成
  - kabusys パッケージの公開インターフェースを定義（data / strategy / execution / monitoring を __all__ でエクスポート）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルや環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env ファイルパーサ実装:
    - `export KEY=val` 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの扱い等を考慮。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
    - ヘルパープロパティ: is_live / is_paper / is_dev
  - 必須設定未提供時は明示的に ValueError を発生させる `_require` を導入。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを扱うユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - カレンダー未取得時は曜日（土日）ベースのフォールバックを使用。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した ETL 設計。
    - DuckDB を想定した最大日付取得ユーティリティ等を実装。
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを付与。
    - タイムウィンドウ定義（JST ベース）を提供: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたり最大記事数と文字数上限でトリム。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーションを実施。
    - リトライと指数バックオフ（429/ネットワーク断/タイムアウト/5xx）実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - スコアは ±1.0 にクリップ。結果は ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - ユニットテスト支援のため、内部の OpenAI 呼び出し関数をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッドを防止）、マクロ記事の抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価を実装。
    - API 失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ。
    - 最終結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。
- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200 日 MA 乖離（ma200_dev）を算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、volume_ratio 等を算出。真の範囲（true_range）の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS が 0/NULL の場合は None）。
    - 設計上、prices_daily / raw_financials のみ参照し、外部 API へはアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。引数のバリデーションあり。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。十分な有効レコードがない場合は None。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸め処理で ties の検出漏れを回避）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - zscore_normalize は kabusys.data.stats から再エクスポート。
- その他
  - OpenAI SDK（OpenAI クライアント）を利用する実装。デフォルトモデルは gpt-4o-mini。
  - DuckDB を主体としたクエリ実行（DuckDB 接続を引数に受ける設計）。
  - ロギングを多用し、重要処理のログ出力を実装（INFO/DEBUG/WARNING 等）。

### 設計上の注意点 / 既知の挙動
- ルックアヘッドバイアス防止
  - 各モジュール（news_nlp / regime_detector / research 等）は内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date に基づいて処理します。
  - DB クエリは target_date 未満 / 排他的条件を使う等、未来データの参照を避ける実装になっています。
- 冪等性・部分失敗耐性
  - DB 書き込みは基本的に削除→挿入の方式を採り、部分失敗時に既存の他レコードを消さない工夫がされています（ai_scores の場合は対象 code のみ削除して再挿入など）。
- フェイルセーフ
  - OpenAI API の失敗時は例外を投げずフェイルセーフなデフォルト（0.0 やスキップ）で継続する設計箇所が多くあります。
- テスト容易性
  - OpenAI 呼び出しを内部 function として切り出しており、ユニットテスト時にモック可能。
- 外部依存
  - DuckDB, OpenAI SDK, J-Quants クライアント（kabusys.data.jquants_client を想定）等の外部モジュールに依存します。
- 環境変数バリデーション
  - KABUSYS_ENV / LOG_LEVEL には許容値チェックが入り、不正値は ValueError となります。

### 変更点（その他）
- 初版のため大幅な API 設計が含まれます。今後、API の安定化や追加機能（発注ロジック、モニタリング、戦略実行部分）の実装・公開を予定しています。

### セキュリティ
- 本リリースでは機密情報（API キー等）は環境変数経由で扱うことを想定しています。設定ファイル管理やシークレット管理の運用方針に注意してください。

---

今後のリリースで予定している改善案（例）
- strategy / execution / monitoring モジュールの具体実装とドキュメント整備
- API 呼び出しのメトリクス収集と監視用エンドポイント
- ai モジュールの推論結果のキャッシュ化やコスト最適化
- テストカバレッジ拡充と CI パイプライン整備

---