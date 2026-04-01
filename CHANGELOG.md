# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初期リリースに相当する変更点を、ソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース（推測）。以下の主要機能・実装を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = 0.1.0 を定義。
  - パッケージ公開 API の予備: __all__ に ["data", "strategy", "execution", "monitoring"] を定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出: .git または pyproject.toml を基準にルートを探索する _find_project_root() を実装。
  - .env/.env.local の自動読み込み（OS環境変数優先、.env.local は上書き）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - インラインコメントの扱い（クォートあり／なしの差）を考慮。
  - 環境変数保護機構: OS 環境変数を protected として上書き抑止。
  - Settings クラスを追加し、アプリ設定をプロパティで提供（J-Quants、kabuステーション、Slack、DB パス、監視閾値、ログレベル等）。
  - 設定値のバリデーション: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
  - 必須環境変数取得ヘルパー _require() を追加（未設定時は ValueError）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄別センチメントスコアを算出。
    - バッチ処理: 1 API 呼び出しにつき最大 20 銘柄を処理するチャンクング。
    - 各銘柄の入力テキストは記事数（最大 10 件）と文字数（3000 文字）でトリム。
    - 再試行・バックオフ実装: 429, 接続断, タイムアウト, 5xx に対して指数バックオフでリトライ。
    - レスポンスバリデーション: JSON 抽出、"results" リスト・各要素の code/score 検証、未知コードの無視、スコアを ±1.0 にクリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガード（DuckDB 0.10 の制約への対応）。
    - テスト用フック: OpenAI 呼び出しを _call_openai_api() のパッチで差し替え可能。
    - calc_news_window(target_date) により JST の窓（前日 15:00 ～ 当日 08:30 JST に対応）を計算するユーティリティを提供。
    - score_news(conn, target_date, api_key=None) により ai_scores テーブルへ書き込み。API キーが未指定の場合は OPENAI_API_KEY 環境変数を参照し、未設定時は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とマクロニュースの LLM センチメント（ウエイト 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を用いた計算と、idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - マクロニュース抽出はマクロキーワードリストでフィルタ（最大 20 件）。
    - OpenAI 呼び出しは retry/backoff を備え、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - score_regime(conn, target_date, api_key=None) を提供。API キー未設定時は ValueError。

- データモジュール (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを想定した market_calendar テーブルの扱いと、営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - カレンダーデータが未取得のときは曜日ベースのフォールバック（週末除外）。
    - 次/前営業日の探索は最大探索日数制限（_MAX_SEARCH_DAYS）を設け、安全に失敗を通知。
    - calendar_update_job(conn, lookahead_days=...) により J-Quants クライアント経由で差分取得→保存する夜間バッチ処理を実装（バックフィルと健全性チェックあり）。
    - jquants_client を経由した fetch/save の呼び出し箇所を用意（外部クライアント統合ポイント）。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを定義し、ETL のメトリクス（取得/保存件数、品質問題、エラー一覧等）を構造化して返却できるようにした。
    - 差分更新・バックフィル・品質チェックを想定した設計方針、DB の最終取得日の取得ユーティリティ、テーブル存在チェック等を実装。
    - デフォルト設定（バックフィル日数、カレンダー先読み日数、初回ロードの最小日付など）を定義。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）や流動性指標（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の SQL を主体に算出する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily / raw_financials のみ参照し、本番注文 API にアクセスしない安全な設計。
    - 欠損・データ不足時の扱いを明確にし、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、値のランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）を受け付け、ホライズン上限チェックを実装。
    - calc_ic はスピアマンのランク相関を純粋 Python 実装で返却（外部依存なし）。

### 変更 (Changed)
- なし（初回リリースにつき新規実装が中心）。

### 修正 (Fixed)
- DuckDB 特有の互換性問題への対応を実装:
  - executemany に空リストを渡すと失敗する DuckDB 0.10 の制約を回避するため、空チェックを追加して不要な executemany 呼び出しを避ける（score_news 内の書き込み処理など）。
- OpenAI API 呼び出しの堅牢化:
  - JSON モードのレスポンスパース失敗に対し、文字列から最外側の {} を抽出して復元を試みるフォールバックを実装（news_nlp）。
  - APIError の status_code を安全に扱う（getattr）ことで SDK の将来変更に耐性を持たせた実装。

### セキュリティ (Security)
- 環境変数の必須チェックを導入（未設定時に ValueError を発生させ、誤った運用を早期に検出）。
- OS 環境変数を保護する protected 機構を .env 読み込みに導入（上書きを防止）。

### 既知の制限 (Known issues / Notes)
- 一部指標（例: PBR・配当利回り）は現バージョンで未実装（calc_value に注記あり）。
- OpenAI を用いる処理は外部 API に依存するため、API キーとネットワークが必須。API 失敗時はフォールバックロジック（スコア 0.0 やスキップ）を採用する設計。
- strategy / execution / monitoring パッケージ名は公開 API に含まれるが、本稿で参照したファイル群に実装が含まれていない箇所がある（将来の実装が想定される）。

---

もし特定の変更点をより詳細に記載したい、またはリリースノートの書式（英語、日本語の出し分け、もっと技術的な詳細など）を調整したい場合は指示してください。