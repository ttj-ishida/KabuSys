# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」形式に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-31
初回リリース

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本構成・環境設定
  - 環境変数・設定管理モジュールを実装（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
  - Settings クラスで必須設定の取得と検証を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - env（development / paper_trading / live）や LOG_LEVEL の値検証を実装。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を提供。

- AI（自然言語処理）機能
  - ニュースセンチメント解析（kabusys.ai.news_nlp）を実装。
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルに書き込み。
    - チャンクサイズ、1銘柄あたりの最大記事数・文字数トリム、JSON-mode レスポンス検証、スコアの ±1.0 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライを実装。
    - API レスポンスの堅牢なバリデーションとフォールバック（失敗時は該当チャンクをスキップ）。
    - テストしやすいように _call_openai_api を patch 可能。
    - calc_news_window で JST ベースのニュース収集ウィンドウ（前日15:00〜当日08:30 JST）を提供。

  - 市場レジーム判定（kabusys.ai.regime_detector）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースのマクロセンチメント（重み 30%）を合成して日次で regime_score / regime_label（bull / neutral / bear）を計算。
    - OpenAI 呼出しは独立した実装で、API エラーや JSON パース失敗時は macro_sentiment=0.0 として継続するフェイルセーフ設計。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー注入可能（api_key 引数）でテスト容易性を確保。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError。

- データ基盤（Data）
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - 差分取得、保存（jquants_client の save_* を想定した冪等保存）、品質チェック統合を設計。
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 最小データ開始日、デフォルトバックフィル等の設定を持つ。

  - マーケットカレンダー管理（kabusys.data.calendar_management）を実装。
    - market_calendar テーブルを用いた営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - JPX カレンダーを J-Quants から差分取得して更新する calendar_update_job を実装（バックフィル、健全性チェック、冪等保存を考慮）。
    - DB 未取得時は曜日ベース（週末除外）でフォールバックする堅牢設計。
    - 検索範囲上限（_MAX_SEARCH_DAYS）を設け無限ループを防止。

- リサーチ（研究）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB を使った SQL で実装。
    - データ不足時の None 扱い、結果は (date, code) キーを持つ dict のリストで返却。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず、標準ライブラリ + DuckDB で実装。
    - calc_ic は Spearman（ランク相関）を実装し、データ不足（有効レコード < 3）時は None。

- テスト・運用向け設計
  - OpenAI 呼び出しの差し替えが容易（ユニットテストで _call_openai_api を patch 可能）。
  - API キーの注入が可能（関数引数での key 指定）で副作用を抑制。
  - 多くの DB 書き込みは冪等化（DELETE → INSERT / ON CONFLICT を想定）やトランザクションで保護。
  - ロギングを詳細に出力することで運用時のデバッグ性を向上。

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 非推奨 (Deprecated)
- 初回リリースのため該当なし

### 削除 (Removed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- OpenAI API キーや各種機密は環境変数経由で管理する設計。自動読み込み時に既存 OS 環境変数は保護される（protected keys の扱い）。

---

注:
- 本リリースはソースコードの初期実装に基づく changelog であり、実際の API エンドポイント名や外部クライアント実装（jquants_client 等）は別モジュールとして想定されています。
- 各関数はドキュメンテーションストリングで設計方針・副作用・例外条件・返却値を明示しています。テスト時は環境依存部分（.env 自動読み込み、OpenAI 呼び出し等）を環境変数やモックで制御してください。