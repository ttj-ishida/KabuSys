# Changelog

すべての利害関係者向けに、人間が読める形式で本リポジトリの変更履歴を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: 本 CHANGELOG はソースコード（src/ 以下）の現状から機能や設計方針を推測して作成した初期リリース向けのまとめです。

## [0.1.0] - 2026-03-31

最初の公開リリース。日本株自動売買・データプラットフォームの基礎機能群を実装しています。主に以下の領域を含みます: 環境設定管理、データ ETL / カレンダー管理、AI を用いたニュースセンチメント・市場レジーム判定、リサーチ用ファクター計算・特徴量解析。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（バージョン: 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開（将来的なモジュール構成想定）。

- 設定 / 環境管理 (`kabusys.config`)
  - .env / .env.local からの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を手がかりに探索）。
  - .env パーサ実装（コメント、export プレフィックス、クォート内のエスケープ処理、インラインコメントの扱いなどに対応）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数参照用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY などの取得を想定）。
  - 環境値検証（KABUSYS_ENV による env 値チェック、LOG_LEVEL 値の検証）。
  - デフォルトの DB パス（duckdb/sqlite）を Settings で提供。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`news_nlp.py`)
    - raw_news / news_symbols テーブルから銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存するフローを実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数制限、JSON Mode パース、レスポンス検証、スコアクリップ（±1.0）を実装。
    - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx をエクスポネンシャルバックオフでリトライするロジックを実装。
    - ルックアヘッドバイアス対策: datetime.today() を用いない、target_date ベースのウィンドウ計算。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - DuckDB の prices_daily / raw_news を参照、結果を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しのリトライ / フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
    - モデル: gpt-4o-mini を使用する想定。API キーは引数または環境変数 OPENAI_API_KEY で供給。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`calendar_management.py`)
    - JPX マーケットカレンダーを扱う一連のユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job。
    - DB にデータがない場合の曜日ベースフォールバック、DB 値優先の設計、探索範囲の上限設定、バックフィルの考慮、健全性チェックを実装。
    - J-Quants クライアント（jquants_client）経由での差分フェッチ・保存フロー（calendar_update_job）。
  - ETL / パイプライン (`pipeline.py`, `etl.py`)
    - ETLResult データクラスを公開（ETL の取得件数・保存件数・品質問題・エラー情報などを保持）。
    - 差分取得、バックフィル、品質チェック連携を想定したパイプライン設計（jquants_client / quality モジュールと連携）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、market calendar 調整ヘルパー等を実装。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ（研究）モジュール (`kabusys.research`)
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装。
    - DuckDB の prices_daily / raw_financials を用いた SQL ベースの計算。データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（複数ホライズン対応）、IC（スピアマンのランク相関）計算、ファクター統計サマリー、ランキング（同順位の平均ランク）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。

- 共通
  - DuckDB をメインのデータ格納/クエリエンジンとして使用する前提で実装。
  - ロギングを各モジュールで活用し、重要なフォールバックやエラーは WARN/INFO/DEBUG で記録。

### Changed
- (初版のため該当なし)

### Fixed
- (初版のため該当なし)

### Deprecated
- (初版のため該当なし)

### Removed
- (初版のため該当なし)

### Security
- 環境変数からの機密情報取得（API トークン等）を前提としているため、.env ファイルの取り扱い・アクセス権限に注意してください。
- OpenAI / J-Quants / Slack 等の API キーは環境変数で与える設計（必須チェックを実装）。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI スコア、レジーム算出、ニュースウィンドウ等、すべて target_date ベースで過去のデータのみを参照するよう設計されています（datetime.today() を直接参照しない）。
- フェイルセーフ:
  - OpenAI API の呼び出し失敗時は例外を上位に投げず、スコアを 0.0 にフォールバックする等、処理継続性を重視する実装です（ただし、API キー未設定は ValueError を送出）。
- DuckDB バージョン互換性:
  - executemany に空リストを渡すと失敗する制約（DuckDB 0.10 系列）を考慮して、空チェックを行った上で executemany を実行します。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）はモック差替えを想定して実装されています（unittest.mock.patch での置換が容易）。

---

今後のリリースで想定される追加事項（例）
- execution / monitoring / strategy モジュールの実装・公開（発注実行ロジック、運用監視）。
- J-Quants クライアント実装詳細の追加・安定化。
- テストカバレッジと CI/CD の整備、型チェック・静的解析の強化。
- パフォーマンス最適化（ETL の並列化、DuckDB クエリ最適化）。

もし特定モジュールについて CHANGELOG に追記・修正したい点があれば対象箇所（ファイル名・関数名）を教えてください。