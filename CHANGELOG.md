# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な機能と実装上の設計方針は以下の通りです。

### Added
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring（サブパッケージ構成を想定）

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パースロジックの強化:
    - コメント行・空行の無視
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォート外、直前が空白/タブ の場合のみ）
  - 環境設定ラッパー Settings を提供。主なプロパティ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token, slack_channel_id （SLACK_BOT_TOKEN/SLACK_CHANNEL_ID 必須）
    - duckdb_path / sqlite_path（デフォルトパスを提供、Path 型で返却）
    - env / log_level のバリデーション（許可値を限定）
    - is_live / is_paper / is_dev の判定ユーティリティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルを用いた銘柄別ニュース集約と LLM（OpenAI gpt-4o-mini）によるセンチメントスコアリング機能を実装。
  - 処理の主な仕様:
    - ニュースウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）
    - 銘柄ごとに最新記事を上限 _MAX_ARTICLES_PER_STOCK（デフォルト 10）で集約し、文字数トリム（_MAX_CHARS_PER_STOCK）
    - バッチ送信: 1 API コールあたり最大 _BATCH_SIZE（デフォルト 20）銘柄
    - JSON Mode の利用（厳密な JSON を期待）とレスポンスのバリデーション（results 配列、code・score の確認）
    - エラー時のリトライ戦略（429, ネットワーク, タイムアウト, 5xx を指数バックオフで再試行）
    - スコアを ±1.0 にクリップ、部分成功時は対象コードのみ置換（DELETE → INSERT）し既存データを保護
  - テスト容易性: 内部の OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch を想定）

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を算出・保存する機能を実装。
  - 主な仕様:
    - ma200_ratio の算出（target_date 未満のデータのみ使用、データ不足は中立扱いで ma200_ratio=1.0）
    - マクロ記事抽出: raw_news からキーワードフィルタ（日本・米国などのマクロキーワード群）
    - LLM (gpt-4o-mini) 呼び出しと JSON パース、API 障害時は macro_sentiment=0.0 にフォールバック
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 判定閾値（BULL_THRESHOLD=0.2, BEAR_THRESHOLD=0.2）によるラベリング
    - 結果は market_regime テーブルに冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
  - エラー時の安全策: API 失敗やパース失敗は例外にせず警告ログとフォールバック値で継続

- データプラットフォーム / ETL（kabusys.data.pipeline, etl, calendar_management）
  - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
  - ETL pipeline の基礎実装:
    - 差分取得ロジック（テーブルの最新日付を検出して未取得範囲のみ取得）
    - backfill による直近数日再取得（デフォルト backfill_days=3）
    - 保存は jquants_client の save_* 関数を用いて冪等的に行う設計想定
    - 品質チェック（quality モジュール）で検出した問題は収集するが ETL は継続（呼び出し元で判断）
  - カレンダー管理（kabusys.data.calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の実装
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック
    - DB 登録があればその値を優先、未登録日は曜日フォールバックで一貫した判定を返す
    - 夜間ジョブ calendar_update_job: J-Quants API からカレンダー差分取得と保存、バックフィルと健全性チェックを実装
    - 探索上限 _MAX_SEARCH_DAYS により無限ループを防止

- リサーチ/ファクター計算（kabusys.research）
  - factor_research:
    - momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - value（per, roe）— raw_financials を参照して target_date 以前の最新財務データを使用
    - DuckDB + SQL を中心とした実装で、データ不足時は None を返す設計
  - feature_exploration:
    - calc_forward_returns（複数ホライズンに対応、データ不足は None）
    - calc_ic（Spearman ランク相関の実装、最小有効数 3）
    - rank（同順位は平均ランクで処理）
    - factor_summary（count, mean, std, min, max, median を計算）
  - 実装方針: 外部依存を避け標準ライブラリと DuckDB で完結。ルックアヘッドバイアス回避のため datetime.today() を直接参照しない。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 実装上の注意
- OpenAI API を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数 api_key によるキー注入を必須とします。未設定時は ValueError を送出します。
- DuckDB に対する executemany の挙動（空リストを渡せない等）を考慮して安全に実装しています。
- JSON Mode を利用する場合でも稀に前後に余分なテキストが混入することを想定しており、パース時に最外側の {} を抽出して復元する救済処理を実装しています。
- テストの容易性を考慮し、内部の API 呼び出し箇所（_call_openai_api 等）は patch による差し替えを想定しています。
- 環境変数キーの主な必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- デフォルトのローカル DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

### Breaking changes
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）