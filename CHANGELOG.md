# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - パッケージの公開モジュール一覧を __all__ で定義: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD 非依存）。
  - .env のパース実装:
    - export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（スペース/タブの直前の # をコメントとみなす等）。
    - ファイル読み込み失敗時は警告ログ。
    - 優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - Settings クラス（settings インスタンス）でアプリ設定を公開:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb / sqlite） / 環境種別（development/paper_trading/live）/ログレベル検証 等。
    - 必須キー未設定時は ValueError を送出する _require を提供。

- データプラットフォーム (kabusys.data.*)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と夜間バッチ更新ジョブ calendar_update_job を実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバック。最大探索日数ガードあり。
    - 健全性チェック・バックフィルの仕組みを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（data.etl に再エクスポート）。
    - 差分取得・保存・品質チェックを想定した ETL パイプラインユーティリティ設計。J-Quants クライアント経由で差分取得し idempotent に保存する方針。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - DuckDB を主要なストレージインターフェースとして利用する設計。

- AI（自然言語処理）機能 (kabusys.ai.*)
  - news_nlp (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出して ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウは JST 基準で「前日 15:00 JST ～ 当日 08:30 JST」を採用（UTC に変換して DB と比較）。
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）を送信、1 銘柄あたり最大記事数 10、最大文字数 3000（トリム）。
    - JSON Mode を利用し厳密な JSON の検証を行う。出力検証: "results" リスト、code と score の存在チェック、未知コード無視、数値変換・有限値チェック、スコアを ±1.0 にクリップ。
    - リトライ戦略: RateLimit/接続断/タイムアウト/5xx に対する指数バックオフ（最大試行回数・基底待機秒数の定義）。
    - API 失敗や検証失敗はフェイルセーフでスキップ。部分成功時は書き込み対象コードのみ DELETE→INSERT を行い既存スコアを保護（DuckDB executemany の互換性考慮）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト容易性: _call_openai_api をパッチ差し替え可能に設計。
    - ロギングを多用し処理状況を報告。
  - regime_detector (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを排除。
    - マクロニュースのキーワードフィルタを実装（日本・米国・グローバルをカバーするキーワード群）。
    - OpenAI 呼び出しは別実装でモジュール結合を避ける。API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフ。
    - 合成スコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値でラベル付け（_BULL_THRESHOLD/_BEAR_THRESHOLD = 0.2）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- リサーチ / ファクター計算 (kabusys.research.*)
  - factor_research:
    - モメンタムファクター calc_momentum:
      - mom_1m（約1ヶ月＝21営業日）、mom_3m（63）、mom_6m（126）、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
      - 大きなスキャン範囲を使って営業日不揃いを吸収する設計。
    - ボラティリティ / 流動性 calc_volatility:
      - atr_20（20日 ATR の単純平均）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio（当日 / 20日平均）を計算。入力データ不足時は None を返す。
      - true_range の NULL 伝播を明示的に制御。
    - バリュー calc_value:
      - raw_financials から target_date 以前の最新財務データを取得し PER（株価/EPS、EPS が 0/欠損の場合は None）と ROE を計算。
    - すべての関数は prices_daily / raw_financials のみ参照し、本番の発注等にはアクセスしない設計。
  - feature_exploration:
    - 将来リターン calc_forward_returns:
      - target_date の終値から各ホライズン（デフォルト [1,5,21]）後の終値までのリターンを計算。ホライズン先のデータがない場合は None。
      - horizons の妥当性チェック（正の整数かつ <= 252）。
    - IC 計算 calc_ic:
      - スピアマンのランク相関（ρ）を計算。有効レコード数が 3 未満なら None。
      - rank 関数は同順位を平均ランクで処理し、丸めを施して ties 判定の安定性を確保。
    - 統計サマリー factor_summary:
      - count/mean/std/min/max/median を算出（None 値除外）。

### 設計上の注記（重要）
- ルックアヘッドバイアス回避:
  - AI モジュール・リサーチモジュールともに datetime.today()/date.today() を内部で参照しない設計。必ず target_date を引数で受け取り、その日以前のデータのみを使用。
- DuckDB 互換性:
  - executemany に対する DuckDB 0.10 の制約を考慮した実装（空リスト送信を回避）。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON mode を利用。レスポンスの堅牢なパースと検証、部分成功の保護、リトライ（指数バックオフ）を実装。
  - リトライ対象の例外や 5xx の取り扱いを明示。
- フェイルセーフ:
  - API 失敗時は例外を投げずに安全なデフォルト（例: macro_sentiment=0.0）で継続する箇所がある。DB 書き込み失敗時はロールバックし例外伝播。
- ロギング:
  - 各処理は詳細な情報・警告・エラーをログ出力し運用時のトラブルシュートを支援。

### 公開 API（主な関数 / クラス）
- kabusys.config
  - settings: Settings インスタンス（settings.jquants_refresh_token, .kabu_api_password, .slack_bot_token, .duckdb_path, .env など）
- kabusys.ai
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - rank(values)
- kabusys.data
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
  - ETLResult (kabusys.data.etl.ETLResult)

### 既知の制限 / 今後の改善点
- strategy / execution / monitoring モジュールの具象実装は本リリースでは未提供（パッケージ公開用の名前空間は準備済み）。
- OpenAI API のクライアントは openai パッケージに依存。API 仕様変更時の互換性テストが必要。
- 一部の SQL は DuckDB の挙動（型バインドや日付型）に依存するため、他の RDB に移植する場合は調整が必要。

### セキュリティ (Security)
- 環境変数の自動読み込み機能はデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API キーは Settings または関数引数で受け取り、未設定時は ValueError を送出して明示的に要求します。