# Changelog

すべての重大な変更点はここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [0.1.0] - 2026-04-04

初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを追加（バージョン 0.1.0）。
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 実行時にプロジェクトルート（.git または pyproject.toml）を探索して .env をロード（cwd に依存しない実装）。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパース機能を強化（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理をサポート）。
    - .env の読み込み失敗時は警告を出力。
  - 必須環境変数の取得ヘルパー _require を実装（未設定時は ValueError を送出）。
  - アプリケーション設定をまとめた Settings クラスを提供（settings = Settings()）。
    - J-Quants / kabuステーション / LINE API / DB パス（duckdb/sqlite）/ 監視関連（pid/killflag/閾値）/システム環境（KABUSYS_ENV, LOG_LEVEL, is_live 等）をプロパティとして取得可能。
    - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション実装。

- AI モジュール（自然言語処理 / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を使って銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウの計算（JST 前日 15:00 ～ 当日 08:30 相当の UTC 範囲）。
    - チャンク処理（最大 20 銘柄／コール）、1 銘柄あたりの記事数と文字数上限（デフォルト: 10 件 / 3000 文字）。
    - JSON Mode を利用した厳格なレスポンス検証およびスコアの ±1.0 クリップ。
    - エラー・429・ネットワーク断・5xx を対象とした指数バックオフによるリトライ実装。非リトライエラーはスキップ（フェイルセーフ設計）。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - kabusys.ai.regime_detector
    - 日次で市場レジーム（bull / neutral / bear）を判定するアルゴリズムを実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成してスコアを算出。
    - マクロキーワードによるニュース抽出、OpenAI 呼び出し、冪等的な market_regime への DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - OpenAI SDK の各種エラー型（RateLimitError, APIConnectionError, APITimeoutError, APIError）をハンドリングしリトライ戦略を実装。

- データプラットフォーム関連
  - kabusys.data.pipeline / etl / quality（quality は参照のみ）設計に沿った ETLResult データクラスを追加。
    - ETL 実行結果のメタ情報（取得数、保存数、品質チェック結果、エラーリスト等）を保持・辞書化可能。
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の API を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末を非営業日とする）。
    - calendar_update_job により J-Quants API から差分取得して冪等的に保存（バックフィル、健全性チェックを含む）。
    - jquants_client 経由での取得・保存処理を想定（エラー時にログ出力して 0 を返すフェイルセーフ）。

- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、ATR 比率）、流動性（平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、ログ出力。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、rank ユーティリティ、factor_summary（基本統計量）を実装。
    - pandas 等の外部依存を用いず標準ライブラリ + DuckDB SQL での実装。

- テスト・開発配慮
  - OpenAI 呼び出しをユニットテストで差し替えやすいように内部関数を分離（_call_openai_api を patch 可能）。
  - DuckDB 固有の制約（executemany に空リストを渡せない等）への対応実装。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更はありません。

### 修正 (Fixed)
- 初期リリースのためありません。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 初期リリース時点で特記すべきセキュリティ修正はありません。ただし OpenAI / J-Quants 等の外部シークレットは環境変数（または .env）で管理する設計です。

---

### 重要な注意点・移行メモ
- AI 機能（score_news, score_regime）は OpenAI API キーが必要です。関数引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定の場合、ValueError が発生します。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN（J-Quants API を利用する ETL/カレンダーで必須）
  - KABU_API_PASSWORD（kabu ステーション API を利用する場合）
  - OPENAI_API_KEY（AI 評価機能を利用する場合）
- .env の自動ロードはプロジェクトルートの特定に依存します（.git または pyproject.toml を探索）。パッケージ配布後や CI 環境などで不要な自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を利用するため、環境に duckdb と openai SDK が必要です。モデル名はデフォルトで gpt-4o-mini に設定されていますが、実際の利用はコストとポリシーを確認の上、適宜変更してください。
- データベース書き込みは冪等性を意識した実装（DELETE→INSERT、ON CONFLICT など）になっていますが、DB スキーマと権限は事前に用意してください。

フィードバックや改善提案は歓迎します。