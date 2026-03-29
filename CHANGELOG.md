# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-29

### Added
- 初回リリースを公開。
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, research, ai, execution, monitoring などの想定）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード順序: OS環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env パースの強化:
    - コメント・空行無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理のサポート。
    - クォートなしの値でのインラインコメント検出（直前が空白またはタブの場合）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）など。
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）とログレベル検証。
    - ヘルパー: is_live / is_paper / is_dev。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DBは UTC 保存前提で変換した半開区間）。
    - バッチ/トークン制限: 最大 20 銘柄/チャンク、記事は銘柄毎に最新 10 件・最大 3000 文字にトリム。
    - JSON Mode のレスポンス検証と堅牢なパース/バリデーションを実装。未知コードは無視、スコアは ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。部分失敗時でも他銘柄の既存スコアを消さない（DELETE→INSERT の部分置換）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロセンチメントは OpenAI（gpt-4o-mini）で JSON レスポンス（{"macro_sentiment": x}）を期待し、API失敗時は 0.0 にフォールバック。
    - ma200_ratio は利用可能データ不足時に中立値 1.0 を返す。
    - 結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。例外時は ROLLBACK を試行。
- データモジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）を扱うユーティリティと夜間バッチ calendar_update_job を実装。
    - 営業日判定・探索ツール: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未登録日は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - 最大探索日数やバックフィル、健全性チェックの実装により無限ループや過剰な未来日付を防止。
  - pipeline / etl:
    - ETLResult データクラスを定義（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェックを想定した ETL 設計（backfill による後出し修正の吸収、品質問題は収集して呼び出し元で判断）。
- Research モジュール（kabusys.research）
  - ファクター計算・特徴量探索ツールを提供:
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（統計要約）、rank（平均ランク処理）。
  - 外部ライブラリに依存せず DuckDB と標準ライブラリのみで実装。
- ロギングと堅牢性
  - 各モジュールで詳細なログ出力（info/debug/warning/exception）を実装。
  - 外部 API 呼び出し失敗時のフォールバック（中立化やスキップ）により ETL・解析パイプラインの停止を防止。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### 注意事項 / 移行ガイド
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を利用する場合）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 必要な DuckDB テーブル（想定）:
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など（各モジュールが参照/書込を行います）。
- OpenAI SDK と DuckDB が必須ランタイム依存です。OpenAI の呼び出しは OpenAI クライアントの chat.completions.create を利用する前提で実装されています。
- 時間処理に関する設計:
  - ルックアヘッドを防ぐために datetime.today() / date.today() の直接参照を避ける実装方針が取られています（関数は target_date を引数で受け取ります）。ただし calendar_update_job など明示的に現在日付を使う箇所もあります（バッチ用途）。
- Python バージョン:
  - 型ヒントに X | Y 形式を使用しているため、Python 3.10 以降を想定しています。

---

（今後のリリースでは Unreleased セクションを用いて変更履歴を積み上げてください。）