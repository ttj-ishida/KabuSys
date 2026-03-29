# Changelog

すべての重要な変更は「Keep a Changelog」仕様に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys のバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージ公開モジュール一覧を __all__ で制御（data, strategy, execution, monitoring）。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込み実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - OS 環境変数の保護（既存値を上書きしない仕組み）および .env.local による上書きルール。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス・クォート・インラインコメント対応、エスケープ処理）。
  - 必須設定を取得する Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベルなど）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを算出。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST 基準のウィンドウを UTC naive datetime へ変換）。
    - バッチ処理（最大 20 銘柄 / API コール）とトークン肥大対策（記事数・文字数のトリム）。
    - API 呼び出しのリトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 復元、results 構造・型チェック、未知コード除外、数値チェック、±1.0クリップ）。
    - DuckDB への冪等書き込み（部分失敗時に既存スコアを保護する DELETE→INSERT ロジック）。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch 等）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily, raw_news を参照し、calc_news_window と連携してウィンドウ内のマクロ記事を抽出。
    - OpenAI 呼び出し（gpt-4o-mini + JSON Mode）、リトライとフォールバック（API 失敗時は macro_sentiment = 0.0）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバックハンドリング。
    - look-ahead バイアス防止の設計（date 比較は target_date 未満／前日ベースで参照）。

  - ai パッケージ公開（src/kabusys/ai/__init__.py）: score_news を公開。

- データプラットフォーム関連（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を参照した営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録が無い場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - JPX カレンダー差分取得ジョブ calendar_update_job（J-Quants クライアントを経由し冪等保存、バックフィル、健全性チェックを含む）。
    - 最大探索日数・先読み・バックフィル等の安全パラメータを設定。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスで ETL の取得数・保存数・品質問題・エラーを集約。
    - 差分更新／バックフィルの設計方針、J-Quants クライアント連携、品質チェック（quality モジュール）との連携を想定。
    - etl モジュールは ETLResult を公開（再エクスポート）。

  - データユーティリティ: DuckDB テーブル存在チェックや最大日付取得などの内部ユーティリティを提供。

- リサーチ機能（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）。
    - Volatility / Liquidity: ATR 20 日、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（price / EPS、EPS が 0 または欠損なら None）、ROE（raw_financials からの最新値）。
    - DuckDB 上で SQL を用いて計算し、結果を dict リストで返す設計。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、データ不足時は None）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、必要レコード数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め対策あり）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。

  - research パッケージ公開（src/kabusys/research/__init__.py）: 主な関数を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 注意: OpenAI API キー（OPENAI_API_KEY）や各種トークンは機密情報のため環境変数で管理する設計。Settings は必須キー未設定時に ValueError を投げるため、運用時はシークレット管理に注意。

### Notes / Migration / Usage
- 環境変数自動ロード:
  - プロジェクトルートが検出できる場合、ルートの .env を先に読み込み、.env.local を上書き読み込みします（OS 環境変数は上書きされません）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
- OpenAI API:
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を利用します。api_key を関数引数で注入可能（テストや複数キー運用に対応）。
  - API 呼び出しは JSON Mode を想定。レスポンス検証・リトライが組み込まれています。
- Look-ahead バイアス対策:
  - 日付参照に datetime.today() / date.today() を直接用いない設計。すべて target_date ベースで計算し、prices_daily のクエリも target_date 未満などの排他条件で安全性を確保。
- テスト容易性:
  - OpenAI 呼び出しラッパー（_call_openai_api）が各モジュールで独立実装されており、テスト時にモック差し替え可能。
- DB スキーマ依存:
  - 多数の処理が DuckDB 内の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を前提にしています。初期化／マイグレーションは別途必要です。

### Known limitations
- 一部計算はデータ不足時に None または中立値（例: ma200_ratio=1.0, macro_sentiment=0.0）でフォールバックします。これにより安全性は高められていますが、データ品質に依存します。
- 現時点では PBR・配当利回りなどのバリューファクターは未実装。
- DuckDB の executemany による空リストバインドの挙動に対処した実装を行っていますが、利用する DuckDB バージョンによる差異に注意してください。

---

今後の変更例（想定）
- AI モデルやバッチサイズの運用パラメータを環境変数で調整可能にする。
- ETL の具体的な実行フロー（jquants_client の実装）や品質チェックレポート出力の強化。
- strategy / execution / monitoring の実装と公開（パッケージ __all__ に現状で宣言済み）。