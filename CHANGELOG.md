# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はパッケージ内のバージョン番号（__version__ = "0.1.0"）に合わせて記載しています。

## [0.1.0] - 2026-04-03

### Added
- 初回公開リリース。
- パッケージ概要
  - kabusys: 日本株自動売買システムの基礎モジュール群を提供（data, research, ai, monitoring 等を想定）。
  - バージョン: 0.1.0。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル（.env / .env.local）や OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（配布後も動作）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサは export KEY=val 形式、クォート付き値、行末コメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティを取得可能。
  - 必須値未設定時は ValueError を投げる `_require` 実装。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）を実装。

- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信して ai_scores に保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して処理）。
    - バッチ処理、最大銘柄数・文字数制限、JSON Mode のパース・バリデーション。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API 失敗時は部分スキップして他銘柄に影響を及ぼさないようにする（フェイルセーフ）。
    - DuckDB の executemany の制約（空リスト不可）に対する互換性処理を実装。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードでフィルタし、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を算出。
    - LLM 呼び出し失敗時のフォールバック（macro_sentiment=0.0）やリトライ処理を実装。
    - データベースへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス回避（date 引数ベース、datetime.today() を参照しない設計）。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`data.calendar_management`)
    - market_calendar テーブルの存在・値に基づく営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得日は曜日ベースのフォールバック（週末除外）で一貫した振る舞い。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants から差分取得 → 保存（保存は jquants_client を介して冪等）。
    - 最大探索日数制限、バックフィル・健全性チェックを実装。
  - ETL パイプライン (`data.pipeline`)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得、保存、品質チェックのフレームワークに対応するためのユーティリティを実装。
    - jquants_client / quality モジュールと連携する設計。

- リサーチ（因子・特徴量解析） (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の計算関数を実装。
    - DuckDB を用いた SQL とウィンドウ関数中心の計算で、prices_daily / raw_financials のみ参照。
    - データ不足時の None 返却やログ出力を実装。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、統計サマリー（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリのみで実装。
  - z-score 正規化ユーティリティを data.stats から再エクスポート。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / 実装上の重要ポイント
- OpenAI 統合
  - 使用モデルは gpt-4o-mini。JSON Mode を前提にレスポンスを解析するが、パースに失敗する場合の復元ロジック（外側の {} 抽出等）やフォールバックを実装している。
  - API キーは関数引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
  - LLM 呼び出しの内部関数はモジュール間で共有せず、テスト時に patch しやすい設計（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- フェイルセーフ設計
  - LLM/API エラー発生時は基本的に例外を上位へ投げず（ただし DB 書き込み中の例外は伝播）、処理を継続する設計。これにより運用中の全体停止を回避。
- DuckDB 依存注意
  - executemany に対する空リストバインドの互換性（DuckDB 0.10 の制約）に対応するコードあり。異なる DuckDB バージョン間で挙動差異がある可能性があるため注意。
- 日付/時間の扱い
  - ルックアヘッドバイアスを防ぐため、各種処理は target_date 引数を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計を心がけている（一部バッチ job は今日の日付を利用）。
- 環境変数・設定項目（主なもの）
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
  - 自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### Migration / 利用時の注意
- OpenAI API の呼び出しはネットワークや利用料に依存するため、本番環境での使用前に API キー設定・レート制限の確認を行ってください。
- DuckDB のスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等）が前提となります。初期テーブル作成やデータ投入は別途必要です。
- ETL やカレンダー更新はバックグラウンドジョブとして定期実行する想定です。lookahead / backfill 設定に注意してください。

--- 

（今後のリリースでは Changed / Fixed / Security セクションを増やしていきます。）