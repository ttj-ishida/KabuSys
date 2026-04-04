# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

フォーマットは以下の通り:
- バージョンはセマンティックバージョニングに従います。
- 日付はリリース日を YYYY-MM-DD 形式で記載します。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。日本株のデータプラットフォーム、リサーチ、AI/NLP スコアリングおよび運用に関する基盤機能を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（src/kabusys/__init__.py）。
  - バージョンを 0.1.0 に設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない。
  - .env パーサ実装（エスケープ・引用符・コメント処理をサポート）。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE チャネル周り（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）
    - データベース経路（DUCKDB_PATH, SQLITE_PATH）
    - 監視関連ファイルパス / 閾値（PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK thresholds 等）
    - 環境種別（KABUSYS_ENV: development/paper_trading/live）とログレベル検証
    - ヘルパープロパティ: is_live / is_paper / is_dev

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約して銘柄ごとに記事を結合。
      - OpenAI（gpt-4o-mini）の JSON Mode を用いて一括（最大 20 銘柄/チャンク）でスコア算出。
      - チャンクサイズ、トリム（最大記事数・文字数）やリトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
      - レスポンスの厳密なバリデーションとスコア ±1.0 クリップ処理。
      - 成功スコアのみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時は他銘柄を保護）。
    - calc_news_window(target_date) により、ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST の UTC 変換）を計算。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
      - マクロセンチメントは raw_news からマクロキーワードでフィルタしたタイトルを LLM に投げて評価。
      - LLM 呼び出しに対してリトライ／フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM の入出力は厳密な JSON を想定、失敗時のログ出力とフォールバックを備える。

- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等）を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末は非営業日）。
    - calendar_update_job(conn, lookahead_days=90) にて J-Quants から差分取得し保存（バックフィル、安全性チェック、ON CONFLICT 動作想定）。
    - 最大探索日数やバックフィル・健全性チェックの定数を設定し無限ループを防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質検査結果、エラー一覧を保持）。
    - 差分取得／バックフィル／保存（jquants_client 経由で冪等保存）／品質チェックのワークフロー設計方針とユーティリティを実装。
    - _get_max_date 等の DB ユーティリティ（テーブル存在チェック等）を含む。
  - etl.py は pipeline.ETLResult を再エクスポート。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。データ不足時の None 処理。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value(conn, target_date): raw_financials と株価を組み合わせて PER、ROE を算出（EPS欠損/0時は None）。（PBR・配当利回りは未実装として明記）
    - 設計上、prices_daily / raw_financials のみ参照し、本番口座・発注 API にはアクセスしない。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト: [1,5,21]）を営業日ベースで算出。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。記録数が少ない場合は None を返す。
    - rank(values): 同順位は平均ランクで処理。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す。
  - research パッケージの公開 API を整備（calc_momentum, calc_value, calc_volatility, zscore_normalize（data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Notes
- OpenAI API の利用
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とする。未設定時は ValueError を送出。
  - レスポンスは JSON Mode を想定してパースするが、パース失敗時のフォールバックや安全なクリップ処理を実装している。
- 環境変数の必須項目
  - JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は Settings のプロパティで必須となる（未設定時は ValueError）。
- データベース
  - DuckDB を前提に実装（Path デフォルト: data/kabusys.duckdb）。SQLite パス設定も存在（監視用途）。
- 設計上の制約・方針
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照しない設計（関数は target_date を引数に取る）。
  - リサーチモジュールは本番発注ロジックを呼ばないよう分離されている。
  - DuckDB バインディングや executemany の仕様（空リスト不可等）に配慮した実装を行っている。

### Known limitations / TODO
- 一部ファクター（PBR・配当利回り）は未実装（calc_value に明記）。
- AI レスポンスは LLM の出力品質に依存するため、運用時にモデル挙動監視が必要。
- jquants_client、quality モジュールの具象実装はこの差分からは推測できないため、連携実装やテストが必要。
- 本リリースはライブラリ基盤であり、実際の「発注」「実行」「監視」ロジックの CLI/サービスは別途実装される想定。

---

（以降のリリースでは、Added / Changed / Fixed / Security セクションを用いて差分を記載してください。）