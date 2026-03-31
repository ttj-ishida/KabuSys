CHANGELOG
=========

すべての変更点は「Keep a Changelog」規約に従って記載しています。
セマンティクバージョニングを採用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にて version と公開モジュールを定義。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化サポート（テスト用）。
  - .env パーサを実装（export 付き行、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - 必須キー取得時の明示的エラー（_require）を実装。
    - サポートされる環境 (development, paper_trading, live) とログレベルの検証。
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など）を提供。

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとにテキストを結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / API コール）・トークン肥大化対策（記事数・文字数の上限）を実装。
    - JSON Mode による厳密なレスポンス検証とレスポンスパースの回復ロジック（余分な前後テキストから {} を抽出）。
    - レート制限 / ネットワーク断 / タイムアウト / 5xx に対する再試行（指数バックオフ）を実装。
    - DuckDB に対する冪等書き込み（該当日のコードのみ DELETE → INSERT）を実行。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）をサポート。
    - フェイルセーフ方針：API失敗時は該当チャンクをスキップして処理を継続。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily / raw_news / market_regime を参照し、ma200_ratio 計算・マクロニュース抽出・OpenAI 呼び出し（gpt-4o-mini）を実装。
    - LLM 呼び出しは独立した内部実装で、モジュール結合を軽減。
    - API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン用ユーティリティ (pipeline, etl)
    - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー収集、has_errors/has_quality_errors）。
    - 差分更新・バックフィル・品質チェック方針を反映した設計。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装。

  - マーケットカレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得、保存は idempotent）。
    - 営業日判定機能を多数実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末は非営業日）で一貫した処理。
    - 最大探索日数の安全策（_MAX_SEARCH_DAYS）やバックフィル・健全性チェックを実装。

- リサーチ/ファクター (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を DuckDB SQL で計算する関数を実装。
    - データ不足時の None ハンドリング（例: MA200 行数不足）を実装。
    - 設計により外部 API に依存せず、本番の発注 API へはアクセスしないことを保証。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、IC（Spearman）計算、ランク変換、ファクター統計サマリー等を実装。
    - pandas 等の外部依存なしで標準ライブラリと DuckDB を使用。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Notes / 実装上の重要ポイント
- 時間窓 / ルックアヘッド防止:
  - AI スコアリング・レジーム判定等の関数は date.today() を内部で参照せず、外部から target_date を受け取る設計でルックアヘッドバイアスを防止。
  - ニュースウィンドウは JST ベースで定義し、DuckDB の UTC 保存値と比較するため UTC naive datetime を用いて変換している（calc_news_window の仕様参照）。

- OpenAI 呼び出し:
  - gpt-4o-mini を利用する想定で JSON Mode を使用（response_format={"type":"json_object"}）。
  - API キーは関数引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照。
  - テスト時の差し替えを容易にするため、内部で _call_openai_api を分離している（unittest.mock.patch でモック可能）。

- DuckDB 対応性:
  - DuckDB の executemany の空リスト制約に対応するガード（空時は呼ばない）。
  - date 値の取り扱いや SQL 内ウィンドウ関数利用に注意を払って実装。

- フェイルセーフ設計:
  - LLM 呼び出しの失敗は局所的にフォールバック（0.0 やスキップ）し、処理全体を止めない設計。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。

依存・環境変数一覧（主なもの）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector / 他 AI 呼び出しで必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH, SQLITE_PATH: データベースファイルパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）
- KABUSYS_ENV: 開発環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

既知の注意点 / 今後の改善候補
- ai_score / regime 判定ロジックのパラメータ（重み・閾値）は将来的に設定可能にすることでチューニング容易性を向上できる。
- News/Regime の OpenAI 呼び出し実行時の課金・待ち時間対策としてローカルモデルや別実行方式を検討する余地がある。
- DuckDB の異なるバージョン間での互換性をより広くカバーするための追加テストが望ましい。

参考
- それぞれのモジュールの docstring に処理フロー・設計方針が記載されています。関数の使い方・引数仕様は該当ファイルを参照してください。