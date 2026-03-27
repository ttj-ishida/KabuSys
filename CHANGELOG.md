# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース: 0.1.0 (初版)

## [Unreleased]

- なし

## [0.1.0] - 2026-03-27

初回リリース。本パッケージは日本株自動売買システム（KabuSys）のコアライブラリ群を提供します。主にデータ取得 / ETL、マーケットカレンダー管理、リサーチ（ファクター計算・特徴量探索）、および AI ベースのニュースセンチメント / 市場レジーム判定のモジュールを含みます。以下は実装済みの主要機能・公開 API と設計上の注意点です。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージ（src/kabusys/__init__.py）
  - バージョン: 0.1.0

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスによる環境変数ベースの設定取得（settings インスタンスを提供）
  - 必須設定の取得メソッド（_require）と各種プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー
  - .env 自動読み込み機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読込
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - 高度な .env パーサー実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理を考慮

- AI 関連 (src/kabusys/ai/)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出
    - calc_news_window(target_date) によるニュース集計ウィンドウ（JST 前日15:00 ～ 当日08:30 相当）計算
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数のトリム制御
    - レスポンスの厳格なバリデーション（JSON モード対応、余分なテキスト復元、スコアのクリップ、未知コード無視）
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）、フェイルセーフで失敗時はスキップ
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - 日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み
    - 入力:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）
      - マクロ経済ニュースの LLM センチメント（重み 30%）
    - LLM 呼び出しは gpt-4o-mini、JSON mode を利用、リトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）
    - ルックアヘッドバイアス防止: target_date 未満のデータのみ参照、datetime.today() を参照しない
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す

- データ / ETL (src/kabusys/data/)
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基にした営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録がない日付は曜日ベースでフォールバック（週末を休日扱い）
    - カレンダー更新バッチ: calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得・冪等保存（バックフィル等を考慮）
    - 最大探索範囲制限・健全性チェックを実装
  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスで ETL 実行結果を集約（品質チェック結果・エラー情報を含む）
    - 差分更新・バックフィル・品質チェックの設計に準拠
    - ETLResult を etl モジュール経由で公開（ETLResult を再エクスポート）
    - 内部ユーティリティ: テーブル存在チェック・最大日付取得など

- リサーチ（研究）機能 (src/kabusys/research/)
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - ファクター計算（prices_daily / raw_financials を参照）:
      - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）
      - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio（20日 ATR 等）
      - calc_value(conn, target_date): per / roe（raw_financials の最新財務データを結合）
    - 設計方針: DuckDB 上の SQL と Python の組合せで再現性のある計算を行う
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を利用）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）の計算
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ
    - factor_summary(records, columns): 各列の統計量（count, mean, std, min, max, median）
  - research パッケージ初期化で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から再利用）

- 共通設計上の特徴
  - DuckDB を主要データストアとして想定（関数は DuckDB 接続を受け取る）
  - ルックアヘッドバイアス対策: 日付ベースのウィンドウ定義と「target_date 未満 / 以前」の厳格な使用
  - OpenAI 統合は API キー注入可能（api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照）
  - フェイルセーフ設計: API エラーやデータ不足時も例外を安易に投げず処理を継続する箇所が多い（ログ出力で警告）

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 初回リリースのため該当なし

---

使用上の注意（マイグレーション / 運用メモ）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能を使用する場合は OPENAI_API_KEY を設定すること（score_news / score_regime は未設定時 ValueError を送出）
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール先で動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御するか明示的に環境変数をセットしてください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提になります。ETL / pipeline を使って初期データをロードしてください。
- OpenAI 呼び出しはモデル gpt-4o-mini と JSON mode を前提に実装されており、レスポンス仕様に依存します。将来的に SDK 変更やモデル仕様変更があった場合、バージョンアップを検討してください。

---

貢献・バグ報告・フィードバックは issue を通じてお願いします。