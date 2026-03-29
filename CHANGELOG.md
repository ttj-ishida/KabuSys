# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各リリースは ISO 日付付きで記載

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。本パッケージは日本株の自動売買・リサーチ・データ基盤を支援するユーティリティ群を提供します。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開。バージョンは __version__ = "0.1.0"。
  - パッケージ外部公開シンボルとして data, strategy, execution, monitoring を提供。

- 環境設定 / config
  - .env または環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
  - .env と .env.local の優先順位を実装（OS 環境変数を保護する機能を含む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 行パーサ実装: export プレフィックス対応、シングル/ダブルクォート内エスケープ、インラインコメント処理等をサポート。
  - 必須環境変数検査（_require）と各種設定プロパティ（J-Quants / kabu / Slack / DB パス / 環境名 / ログレベル / is_live 等）。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と記事トリム（最大記事数・文字数）を実装。
    - バッチ処理（最大 20 銘柄/コール）、JSON Mode の使用、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定するスコアリング機能を追加。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しのリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - モデル: gpt-4o-mini、出力は厳密な JSON 想定。

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録がない日については曜日ベースのフォールバック（週末除外）を提供し、DB とフォールバックの整合性を保つ設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理を実装。バックフィルと健全性チェックを内蔵。

  - pipeline / etl:
    - ETLResult データクラスを公開し、ETL の取得/保存件数・品質問題・エラー情報を統一的に表現。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計文書に基づく実装を用意。
    - DuckDB 互換性を考慮したヘルパー関数（テーブル存在チェック、最大日付取得など）を実装。

  - etl / jquants_client 連携や保存は冪等性を重視（ON CONFLICT DO UPDATE / 個別 DELETE → INSERT の順序など）。

- Research (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金/出来高比率）、バリュー（PER, ROE）等の定量ファクター計算関数を実装。
    - DuckDB の SQL 窓関数を活用し、prices_daily / raw_financials のみを参照する実装。
    - 結果は (date, code) 単位の辞書リストで返却。

  - feature_exploration:
    - 将来リターン算出（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

### 変更 (Changed)
- 設計上の重要な方針を明文化してコードに反映
  - ルックアヘッドバイアス防止: 各種スコアリング・集約関数は内部で datetime.today()/date.today() を参照せず、必ず呼び出し側から target_date を受け取る設計。
  - DuckDB 互換性向上: executemany に空リストを渡さない等、DuckDB の制約に配慮した実装。

### 修正 (Fixed)
- API 呼び出し時の堅牢性向上
  - OpenAI API 呼び出しでの各種例外ハンドリングと段階的リトライ（RateLimit, Connection, Timeout, 5xx）を追加。
  - JSON レスポンスのパース失敗・余分テキスト混入への復元処理を追加（外側の {} を抽出してパース試行）。

### セキュリティ (Security)
- 環境変数保護
  - .env の自動読み込み時に既存 OS 環境変数を protected として上書きから保護。
  - 必須値が未設定の場合は明示的な ValueError を送出して安全に停止。

### 既知の制約 (Known issues / Notes)
- DuckDB のバージョン依存性（executemany の空パラメータ等）に注意。コード内に互換性考慮の処理を入れているが、利用環境によっては追加対応が必要。
- OpenAI 呼び出しは gpt-4o-mini を想定しているため、別モデルや将来の SDK 変更に伴う微調整が必要になる可能性がある。
- news_nlp / regime_detector は外部 API（OpenAI）に依存するため、API キーや利用制限に応じた運用設計が必要。

---

（注）各モジュールの内部実装詳細・設計方針はソースコード内のドキュメンテーション文字列（docstring）に記載されています。リリース後のバグ修正や機能追加は本 CHANGELOG の Unreleased セクションに追記してください。