# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
初回リリースの内容はコードベースから推測・要約した機能説明です。

今後のリリースでは Unreleased セクションに変更を記載してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

概要: KabuSys 初回公開リリース。日本株のデータ取得・ETL・特徴量計算・AI ベースのニュースセンチメント/市場レジーム判定・マーケットカレンダー管理など、リサーチおよび自動売買の基盤となる主要モジュールを実装。内部データストアに DuckDB を使用し、OpenAI（gpt-4o-mini）を用いた NLP 処理を組み込んでいます。

### Added
- パッケージの基本情報
  - パッケージ名 kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出ロジック: __file__ を基点に .git または pyproject.toml を探索してプロジェクトルートを特定し、.env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーは export 付き行、クォート文字列（エスケープ処理対応）、インラインコメント処理等に対応。
  - .env の読み込み時に OS 環境変数を保護する protected set を導入し、.env.local の上書き挙動などを制御。
  - 必須設定取得用の _require と各種プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須項目。
    - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH 等のデフォルトパス設定。
    - CPU/MEM/ディスク閾値やログレベル、環境（development/paper_trading/live）の検証ロジックを実装。
  - 設定値の検証（有効な環境/ログレベルのチェック）を実装。

- AI（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に対応する calc_news_window を実装。
    - バッチ処理（デフォルト 20 銘柄／回）および 1 銘柄あたり最大記事数・文字数のトリムでトークン肥大化に対応。
    - レート制限（429）、接続断、タイムアウト、5xx サーバーエラーに対する指数バックオフリトライを実装（最大リトライ回数設定）。
    - OpenAI 応答の堅牢なバリデーション（JSON 抽出・results 構造検査・スコア数値化・未知コード無視）を実装し、スコアを ±1.0 にクリップ。
    - 部分失敗に備え、ai_scores への書き込みは対象コードのみに DELETE → INSERT を行う（冪等かつ既存データ保護）。
    - テスト容易性: OpenAI 呼出し部分は内部関数を patch 可能（_kabusys.ai.news_nlp._call_openai_api）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - prices_daily, raw_news, market_regime を利用。MA 計算でルックアヘッドバイアスを排除（target_date 未満のみ使用）。
    - マクロニュースはキーワードフィルタリングで抽出し、OpenAI で macro_sentiment を評価。API エラー時は 0.0 にフォールバックするフェイルセーフ設計。
    - レジームスコアの閾値判定、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼出しのリトライ・エラー処理、レスポンスパース時の保護的なエラーハンドリングを実装。
    - テスト容易性: _call_openai_api を patch 可能。

- リサーチ（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時は None を返す。
    - Volatility & Liquidity: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金（avg_turnover）・出来高比（volume_ratio）を算出する calc_volatility を実装。true_range の NULL 伝播を考慮。
    - Value: raw_financials から直近財務を取得して PER・ROE を算出する calc_value を実装（PBR 等は未実装で今後の拡張対象）。
    - すべて DuckDB 上の SQL を利用し、prices_daily / raw_financials のみ参照。外部取引 API にはアクセスしない設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（デフォルト horizons [1,5,21]）を実装。ホライズン検証（1..252）を行い、1 クエリでまとめて取得する実装。
    - IC（Spearman の ρ）計算 calc_ic を実装（rank 関数を内部で提供、同順位は平均ランク）。
    - factor_summary による統計サマリ（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存なしで実装。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理、market_calendar を基に is_trading_day/next_trading_day/prev_trading_day/get_trading_days/is_sq_day を実装。
    - market_calendar 未取得時は曜日ベースのフォールバック（土日非営業日）を採用し、DB の値が優先される一貫した挙動を提供。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得 → 保存（fetch/save の呼び出しとエラーハンドリング）を実装。バックフィル・健全性チェックを導入。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（進捗・件数・品質問題・エラー概要を保持）。
    - 差分更新・バックフィルの方針、品質チェックとの連携（quality モジュール）に基づく設計を実装。
    - jquants_client 経由の保存処理を前提とした差分フェッチ/保存フローを実装（エラー耐性を重視）。
    - etl モジュールは ETLResult を再エクスポート。

- 共通・インフラ
  - DuckDB を主要データストアとして利用する SQL 実装。
  - 多くの関数で「ルックアヘッドバイアスを防ぐ」方針を徹底（datetime.today()/date.today() を直接参照しない、target_date を明示）。
  - OpenAI API 呼び出しはクライアント注入（api_key 引数または環境変数 OPENAI_API_KEY）を可能にし、テストや CI での差し替えを容易化。
  - ロギングを各モジュールに組み込み、警告・情報ログで状態を報告。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- API キーは引数または環境変数（OPENAI_API_KEY）から取得。未設定時は ValueError を発生させ早期検出。
- .env 読み込みにおいて OS 環境変数を保護する設計（override/protected）を実装。

### Known limitations / Notes
- 一部指摘済みの未実装項目:
  - calc_value: PBR・配当利回りは未実装（コード内に明記）。
- DuckDB の executemany に関する互換性を考慮した保護（空リスト渡し回避）を実装しているため、古い DuckDB バージョンとの互換性に配慮。
- OpenAI のレスポンスは JSON Mode を前提にしているが、稀に前後に余計なテキストが入るケースに対しても復元ロジックを実装。
- market_calendar の未取得状態では曜日フォールバックを使用するため、完全な JPX カレンダーがあることが前提ではない。

---

開発チームは今後、機能の追加（戦略/実行モジュールの具現化、より詳細な品質チェック、追加ファクター、PBR/配当等の拡張）、テストカバレッジ拡充、ドキュメント整備を予定しています。README と API 使用例は別途整備してください。