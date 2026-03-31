# Changelog

すべての注記は Keep a Changelog の慣習に準拠して書かれています。  
初回リリース v0.1.0 の内容をコードベースから推測して日本語でまとめています。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージの公開インターフェースを定義（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む（CWD に依存しない挙動）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env ファイルのパースは export KEY=val、クォートあり／なし、インラインコメント等に対応。
    - .env.local は .env の設定を上書き可能（ただし既存の OS 環境変数は保護）。
  - 必須環境変数取得ユーティリティ _require と、アプリ設定をプロパティとして提供する Settings クラスを公開。
    - 主要な必須変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - その他デフォルト値を持つ設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV
    - LOG_LEVEL / KABUSYS_ENV のバリデーション（許容値のチェック）を実装。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント解析 (news_nlp.py)
    - DuckDB に格納された raw_news / news_symbols を読み、銘柄単位で記事を集約。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄／API コール）、記事数・文字数トリム（最大記事数・最大文字数）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時はスキップして継続するフェイルセーフ設計。
    - API レスポンスの堅牢なバリデーション（JSON 抽出、キー/型チェック、未知コードの無視、数値化、±1.0 でクリップ）を実装。
    - 結果を ai_scores テーブルへ冪等（DELETE → INSERT）で書き込み、部分失敗時にも既存データを保護。
    - 公開関数: score_news(conn, target_date, api_key=None) を提供。
    - ユーティリティ: calc_news_window(target_date)（JST 基準の時間ウィンドウ計算）を提供。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - DuckDB の prices_daily / raw_news を参照し、OpenAI を呼んで macro_sentiment を算出。API エラー時は macro_sentiment=0.0 で継続。
    - レジームスコアの合成、ラベル判定し market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None) を提供。
    - LLM 呼び出し部分は独自実装とし、news_nlp と内部関数を共有しない設計。

- Data / ETL / カレンダー (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを使用した営業日判定ロジックを提供。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - next/prev_trading_day は探索上限を設定して無限ループを防ぐ（_MAX_SEARCH_DAYS）。
    - calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェック含む）。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを定義し、ETL の取得数・保存数・品質チェック結果・エラーを構造化して返す設計。
    - ETL パイプライン設計に基づくユーティリティ（差分取得、バックフィル、品質チェック統合）を用意するための基盤コード。
    - 内部ユーティリティ: テーブル存在チェック・最大日付取得など（DuckDB 用）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- Research（研究用）モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER, ROE）等を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - calc_momentum, calc_volatility, calc_value を提供。結果は (date, code) をキーとする辞書リストで返却。
    - 計算においてデータ不足時は None を適切に返す（健全な欠損処理）。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターンの計算 calc_forward_returns（任意ホライズン対応、ホライズンの検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンρ、結合・欠損フィルタリング済み）。
    - ランク関数 rank（同順位は平均ランク、丸め処理を含む）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
  - research パッケージ __init__ で上記主要関数をエクスポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- 環境ファイル読み込みの堅牢化
  - .env パースにおいてクォート内のバックスラッシュエスケープやインラインコメントの扱いを適切に処理。
  - .env 読み込み失敗時に警告を出して処理継続する安全な挙動。

- OpenAI 統合の堅牢化
  - news_nlp / regime_detector 双方で API 呼び出しに対してリトライとエラー分類（429/ネットワーク/タイムアウト/5xx）を実装し、API 異常時は例外を上位に投げずフェイルセーフで継続する設計。
  - JSON レスポンスのパースで余計な前後テキストが混在するケースに備えた復元処理を実装。

- DuckDB 書き込みの冪等性確保
  - ai_scores / market_regime 等への書き込みは DELETE → INSERT や individual executemany を用い、部分失敗時に既存データを保護する実装。

### 注意点 / 既知の制限 (Notes)
- OpenAI API キー（OPENAI_API_KEY）は score_news / score_regime の引数に注入可能。未指定の場合は環境変数を参照し、未設定なら ValueError を送出する。
- news_nlp と regime_detector は gpt-4o-mini と JSON Mode を前提に設計されている（厳密な JSON 出力を期待）。
- 多くの処理は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）存在を前提としている。実行前にスキーマ準備が必要。
- 時刻処理はルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない設計（target_date を明示的に与える方式）。
- DuckDB のバージョンや SQL バインドの違い（list バインドの挙動など）に配慮して実装しているが、環境差分に依存する箇所が残る可能性がある。

### 互換性の破壊 (Breaking Changes)
- （初期リリースのため該当なし）

---

もし CHANGELOG に追記したいポイント（特に実際の変更日や追加で記載したい修正／制約）があれば教えてください。必要に応じて各セクションをより詳細に分割して記載します。