# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

現在のリリースは初期バージョンの実装に基づく推測ドキュメントです。日付はコード解析時点の日付 (2026-03-28) を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28

### Added
- パッケージ基礎
  - パッケージ名 kabusys を導入。バージョン `0.1.0` を設定。
  - パッケージの公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 環境設定・ロード機能 (`kabusys.config`)
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml による探索）を実装し、CWD に依存しない読み込みを実現。
  - .env パーサを実装：
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いなどに対応。
    - 読み込み時に OS 環境変数は保護（上書き回避）し、.env.local は override（上書き）で適用。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ固有の設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定検証。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/…）のバリデーション。
    - DuckDB / SQLite のデフォルトパス取得ユーティリティ。

- AI モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信し銘柄別スコアを取得。
    - バッチサイズ、記事数、文字数制限などのトークン肥大対策を実装（_BATCH_SIZE、_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）実装（指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検査、code の整合性、スコア数値検証）。
    - duckdb への冪等書き込み（DELETE → INSERT）を実装し、部分失敗時に既存スコアを保持する設計。
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定。
    - ニュースウィンドウ計算ユーティリティ calc_news_window を提供（JST 基準で前日 15:00 ～ 当日 08:30 をカバー）。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp のウィンドウ計算を利用して抽出。
    - OpenAI 呼び出しは独立実装で、API 失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 内部でのルックアヘッドバイアス回避に配慮（target_date 未満のデータのみ参照、datetime.today() を参照しない）。

- データモジュール (`kabusys.data`)
  - マーケットカレンダー管理 (`data.calendar_management`)
    - market_calendar テーブルを基に営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録がない日付は曜日ベース（平日）でフォールバックする一貫した挙動。
    - 最大探索範囲を設定して無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル（直近数日再フェッチ）して market_calendar を冪等保存。
    - 健全性チェック（未来に極端に飛んだ last_date はスキップ）とエラーハンドリングを追加。

  - ETL パイプライン基盤 (`data.pipeline`, `data.etl`)
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーの集計）。
    - 差分更新、バックフィル、品質チェック統合を想定した処理設計（J-Quants クライアントと quality モジュールとの連携を想定）。
    - DuckDB を前提にしたテーブル存在チェックや最大日付取得ユーティリティを提供。

  - jquants クライアントのラッパ（想定）を利用するためのフックを用意（jq.fetch_* / jq.save_* の呼び出しを期待）。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER・ROE）などの定量ファクターを実装。
    - DuckDB SQL を活用した窓関数による計算を行い、結果を (date, code) を含む辞書リストで返す。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。
    - IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを提供。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。

### Changed
- 初回リリース（基盤機能の追加）。変更履歴なし。

### Fixed
- 初期設計段階での堅牢性強化（実装段階で下記を想定）：
  - OpenAI 呼び出しでの各種エラー（RateLimit / タイムアウト / ネットワーク / 5xx）に対するリトライとフォールバックを実装。
  - JSON パース失敗時の復元ロジック（文字列から最外の {} を抽出して再パース）を導入し、LLM 出力のばらつきに耐性を持たせた。
  - DuckDB に対する executemany の挙動（空リスト不可）を考慮したガード実装。
  - DB 書き込み失敗時のトランザクションロールバック処理とログ出力を実装。

### Notes
- OpenAI の呼び出しは gpt-4o-mini を想定しており、JSON Mode を利用する設計。API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。
- DB は DuckDB を中心に設計されている（SQL の互換性を考慮した実装）。
- 外部 API クライアント（J-Quants、kabu station、Slack など）は設定値（環境変数）経由で参照し、実際の HTTP 呼び出しはそれらクライアントモジュールに委譲する想定。
- 本 CHANGELOG は提供されたソースコードから推測して作成した初期リリース向けの要約です。将来的な変更はここに追記してください。