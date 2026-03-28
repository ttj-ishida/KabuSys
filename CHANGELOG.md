# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なおこの変更履歴は、提供されたコードベースの実装内容から推測して作成しています。

## [0.1.0] - 2026-03-28

### Added
- 初回公開（ベース実装）
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- パッケージ公開インターフェース
  - src/kabusys/__init__.py により、public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env と .env.local のロード順序（OS 環境変数 > .env.local > .env）。.env.local は上書き（override）を許可。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - export KEY=val 形式・クォート・エスケープ・インラインコメント等に対応した堅牢な .env パーサを実装。
    - OS 環境変数を保護するため protected セットを使用して上書きを制御。
    - Settings クラスを提供し、以下の設定プロパティを取得可能:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のいずれか、デフォルト: development）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか、デフォルト: INFO）
      - is_live / is_paper / is_dev のブール判定ユーティリティ

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメント解析機能を実装（score_news）。
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のウィンドウで記事を収集（calc_news_window）。
    - 銘柄ごとに記事を集約し（最大記事数、文字数でトリム）、最大 20 銘柄をバッチで OpenAI に投げる。
    - gpt-4o-mini + JSON mode を利用した応答パース。レスポンスは厳密な JSON を期待。
    - レスポンス検証ロジックを実装（results キーの存在確認、code と score の検証、スコアの ±1.0 クリップ）。
    - API 呼び出し周りにリトライ（429/ネットワーク断/タイムアウト/5xx を指数バックオフ）を実装。
    - API 失敗やパース失敗時は該当チャンクをスキップして処理継続するフェイルセーフ設計。
    - DuckDB への書き込みは部分書き換え（該当 code の DELETE → INSERT）で冪等性と部分失敗耐性を確保。
    - テストしやすいように内部の _call_openai_api をパッチ可能に実装。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（＝日経225連動ETF）の 200 日移動平均乖離（70%）と、ニュース由来のマクロセンチメント（30%）を合成して日次市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、LLM 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みの一連処理を提供。
    - OpenAI 呼び出しに対するリトライ・エラー処理・JSON パースの堅牢化。
    - API 失敗時は macro_sentiment=0.0 とするフェイルセーフ動作。
    - テスト容易性のため内部の _call_openai_api を差し替え可能。

- リサーチ・ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 約1M/3M/6M リターン、ma200 偏差（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比、20 日平均売買代金、出来高比率を計算。必要行数未満は None を扱う。
    - calc_value: raw_financials から最新財務データを取得し PER（EPS に基づく）、ROE を計算。
    - DuckDB を用いた SQL ベースの実装。外部 API には依存しない設計。
    - 出力は (date, code) をキーとする dict のリスト。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算。3 件未満は None。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（浮動小数丸めによる ties 処理を考慮）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー関数。
    - 実装は標準ライブラリのみで pandas などに依存しない。

- データ基盤（Data Platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にカレンダーがない場合は曜日ベース（土日除外）でのフォールバックを採用。
    - next/prev/get で DB の登録値を優先し、未登録日は一貫した曜日フォールバックで補完する設計。
    - calendar_update_job: J-Quants API から差分取得 → market_calendar へ冪等保存。バックフィルと健全性チェックを実装。
    - 最大探索日数など安全策を導入して無限ループや誤った未来日付処理を防止。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを定義（ETL の取得件数、保存件数、品質問題、エラー等を保持）。
    - ETL パイプラインのヘルパー（テーブル存在チェック、最大日付取得、トレードデイ調整等）を実装。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - etl モジュールで ETLResult を再エクスポート。

- その他・ユーティリティ
  - DuckDB 互換性や制約（executemany に空リストを渡せない等）へ配慮した実装。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を AI/スコアリング関数の内部で直接参照しない設計（target_date を明示引数として扱う）。
  - ロギングを各所で備え、失敗時に情報を残す実装。

### Fixed
- （初期リリースに合わせた既知の堅牢化）
  - OpenAI レスポンスの JSON パースに対して、前後の余計なテキストが混入した場合に最外の {} を抽出して復元する処理を追加（news_nlp の _validate_and_extract 等）。
  - OpenAI API のエラー種別に応じたリトライ判定を実装（RateLimit/接続/タイムアウト/5xx をリトライ、それ以外は即スキップ）。
  - DB 書き込み失敗時に ROLLBACK を試み、さらに ROLLBACK 自体の失敗を警告ログで記録して上位へ例外を伝播する安全設計。

### Changed
- （特になし：初回リリース）

### Removed
- （特になし：初回リリース）

### Deprecated
- （特になし：初回リリース）

### Security
- API キーや機密情報は環境変数で管理する想定（Settings による必須チェック）。
- .env の自動読み込みはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- AI 関連機能（score_news, score_regime）は OpenAI API（OPENAI_API_KEY）を要求します。キー未設定時は ValueError を投げます。
- DuckDB 接続を前提とする関数群（research, ai, data）は、適切に構築された DuckDB スキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等）が必要です。
- 本 CHANGELOG は提供されたソースコードに基づく推測的な記述です。実際のリリースノートとして配布する際は、実装・動作確認結果やドキュメント（README, DataPlatform.md, StrategyModel.md 等）を参照して補足・修正してください。