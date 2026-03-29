# Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買システムのコアライブラリを提供します。

### 追加
- パッケージ初期化
  - kabusys パッケージと主要サブパッケージ（data, research, ai, monitoring, strategy, execution）の公開インターフェースを定義。
  - バージョン情報: 0.1.0。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込み順序: OS環境変数 > .env.local > .env（.env.local は上書き）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント取り扱い（直前が空白/タブの場合のみコメントとみなす）。
  - 環境変数取得ヘルパー（Settings）を提供（必須チェック・デフォルト値・値検証含む）。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
    - 環境モード検証: KABUSYS_ENV は development / paper_trading / live のいずれか、LOG_LEVEL 値検証。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルに保存する機能を実装。
  - 特徴:
    - JST に基づくニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - 1銘柄当たり最大記事数・文字数でトリム（トークン肥大化対策）。
    - 最大20銘柄をチャンク化してバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（JSON抽出・resultsキー・コード・スコア型検証）。
    - スコアを ±1.0 にクリップ。
    - 書き込みは冪等（DELETE → INSERT）かつ部分失敗時に既存データを保護する設計。
    - APIキーは引数で注入可能（テスト容易性）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ日次書き込みする機能を実装。
  - 特徴:
    - prices_daily から ma200_ratio を計算（ルックアヘッド防止のため target_date 未満データを使用）。
    - マクロニュースは news_nlp の窓計算を利用してフィルタ（マクロキーワードリスト）し、OpenAI で macro_sentiment を評価。
    - APIエラー時は macro_sentiment=0.0 のフェイルセーフ動作。
    - レスポンスは厳密JSONを期待しつつパース失敗時に安全にフォールバック。
    - DB書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保し、失敗時はROLLBACK。

- データ基盤ユーティリティ（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar を参照して営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DBにカレンダーがない場合は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理（バックフィル・健全性チェック含む）。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分更新ロジック、バックフィル日数、品質チェック（quality モジュール連携）の設計を含む。

- リサーチモジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily 組み合わせによる PER / ROE を算出。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 複数ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
  - 設計方針: DuckDB 接続のみを受け取り、外部 heavy ライブラリに依存しない実装。

### 変更（設計上の重要な方針）
- ルックアヘッドバイアス対策: AI モジュール・リサーチ関数は内部で datetime.today()/date.today() を参照せず、全て target_date を明示的に受け取り、その date を基準に処理を行う。
- DuckDB 書き込みの互換性: DuckDB 0.10 系の制約（executemany に空リスト不可）を考慮した実装。
- OpenAI 呼び出しは各モジュールで独立実装（モジュール間でプライベート関数を共有しない）し、ユニットテストで差し替え可能に設計。

### 修正（エッジケース / 耐障害性）
- OpenAI API 呼び出しの耐障害性強化:
  - RateLimitError / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
  - 非5xx の APIError や JSONパース失敗は警告ログを出して安全に 0.0 や空結果へフォールバック（例外を上げない）。
  - レスポンスパース時に前後余計なテキストが混入するケースに対し外側の {} を抽出して復元するロジックを導入。
- .env 読み込み失敗やファイルアクセスエラーは警告で扱い処理を継続。
- DB トランザクション処理での例外時に ROLLBACK 失敗を警告ログで記録。

### 既知の制約 / 注意事項
- 必須外部依存: DuckDB と OpenAI SDK が必要（OpenAI は gpt-4o-mini 想定）。
- OpenAI API キーは score_news / score_regime の引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する。
- DB テーブル想定:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など多数のテーブルを参照／更新。
- モデルとパラメータ:
  - デフォルトモデル: gpt-4o-mini（将来の変更に備えモデル名は定数化）。
  - 各種上限値（バッチサイズ、記事数、リトライ回数、ウィンドウ定義など）はモジュール内定数で定義。

### 破壊的変更
- なし（初期リリース）。

---

開発者向けメモ:
- テスト容易性のため OpenAI 呼び出し関数をモジュール内で patch 可能にしている（unittest.mock.patch を想定）。
- ロギングによる監査を重視しており、重要な分岐・フォールバックは logger に出力する設計になっています。