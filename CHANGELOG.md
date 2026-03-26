# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

最新の変更は上にあります。

## [Unreleased]

- （現在未リリースの変更はありません）

## [0.1.0] - 2026-03-26

初回公開リリース。

### Added
- パッケージ初期化
  - kabusys.__version__ = 0.1.0 を設定し、主要サブパッケージ（data, research, ai, ...）を __all__ で公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動で読み込む自動ローダ実装。  
    - 読み込み優先度: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env 行パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
  - 環境設定ラッパ（Settings）を提供:
    - 必須トークン/キー検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などは _require で未設定時に ValueError を送出）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL 検証。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - ニュースウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で処理）。
    - バッチ処理: 最大 20 銘柄／API 呼び出し、1銘柄あたり最大 10 件、3000 文字にトリム。
    - 再試行: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の整合性、数値チェック）。
    - スコアは ±1.0 でクリップ。部分失敗時に既存スコアを保護するため、書き込みは対象 code に限定した DELETE → INSERT の冪等処理。
    - API キーは引数または環境変数 OPENAI_API_KEY で注入可能。未設定時は ValueError。

  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - MA200 の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロキーワードに基づき raw_news からタイトルを抽出し、OpenAI（gpt-4o-mini）で JSON レスポンス化して macro_sentiment を取得。
    - API 失敗時は macro_sentiment = 0.0（フォールバック）で継続。再試行・5xx 処理あり。
    - レジームスコアを clip(-1,1) し、閾値によりラベル付け（BULL / BEAR 閾値: 0.2）。
    - market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT による冪等書き込み。失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - API キーは引数または環境変数 OPENAI_API_KEY で注入可能。未設定時は ValueError。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M / 3M / 6M リターン、200日 MA 乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials の最新財務データを用いて PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL ベース実装。prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。有効データが 3 件未満で None。
    - factor_summary: count/mean/std/min/max/median 等の基本統計量を計算。
    - rank: 同順位は平均ランクを割り当てる実装（float の丸めを用いた安定化）。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar がない場合は曜日ベースでフォールバック（土日非営業日）。
    - calendar_update_job: J-Quants API（jquants_client を介した fetch/save）から差分取得して market_calendar を更新。バックフィル（直近 _BACKFILL_DAYS）・健全性チェック（将来日付の異常検知）に対応。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
  - ETL / pipeline:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェックのためのユーティリティ（テーブル存在確認、最大日取得など）を実装。
    - ETL の設計は差分単位を営業日ベース、バックフィルを行い品質検査の結果を集約して上位に返す方針。

- 実装設計上の注意点（全体）
  - ルックアヘッドバイアス回避: 多くの関数で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DuckDB をメインのローカル分析 DB として使用。
  - OpenAI 呼び出しは JSON mode を用い、レスポンスの厳密なパースとバリデーションを実装。
  - API 呼び出し失敗に対するフォールバック（ゼロセンチメント、スキップ等）により、ETL/分析パイプラインの堅牢性を確保。
  - DB 書き込みは可能な限り冪等性を担保（DELETE → INSERT、ON CONFLICT 等を想定）し、トランザクション制御（BEGIN/COMMIT/ROLLBACK）を導入。

### Changed
- （初回リリースのため過去の変更はありません）

### Fixed
- （初回リリースのため過去の修正はありません）

### Security
- 環境変数に依存する秘密情報は Settings._require により明示的に検出される。自動 .env ロードはプロジェクトルート検出に基づくが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

注: 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートに含めるべき細かい API 使用例、既知の制約、互換性情報（例: DuckDB バージョン制約、OpenAI SDK バージョン互換等）は別途プロジェクトのリリースポリシーに沿って補完してください。