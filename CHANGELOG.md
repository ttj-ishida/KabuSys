# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載します。  
このプロジェクトの初回リリースとして v0.1.0 を公開しました。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン: 0.1.0

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に判定（CWD に依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によって無効化可能。
    - .env ローダーは上書き制御（override）と OS 環境変数の保護（protected set）をサポート。
  - .env パース機能:
    - コメント行・空行・export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理と閉じクォート探索を実装。
    - インラインコメント検出ロジック（クォート外・直前が空白/タブの場合のみ）を実装。
  - Settings クラスによりアプリケーション設定をプロパティとして提供:
    - J-Quants / kabuステーション / LINE / DB（duckdb, sqlite）/監視（PID, kill flag,閾値）/システム設定（env, log_level, is_live/paper/dev）等のプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出する `_require` を利用。
    - KABUSYS_ENV と LOG_LEVEL の有効値チェックを実装。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い、ai_scores テーブルへ書き込む。
    - ニュース集計ウィンドウ（JST 基準）を計算するユーティリティ calc_news_window を提供（前日 15:00 JST 〜 当日 08:30 JST）。
    - バッチ処理: 最大 20 銘柄 / API 呼び出し、1 銘柄あたり最大記事数・文字数でトリム。
    - OpenAI JSON Mode 利用想定。レスポンスの堅牢な検証（JSON 抽出、results 構造、コード照合、数値チェック）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフのリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗耐性を考慮し、対象コードのみ DELETE → INSERT（executemany）で置換。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し、日次で market_regime テーブルに書き込む。
    - マクロニュースは raw_news からマクロキーワードでフィルタして取得。LLM（gpt-4o-mini）を使った JSON 出力で macro_sentiment を取得。
    - レジームスコア合成ロジック、閾値によるラベル判定（bull / neutral / bear）を実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックし継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）を行い、例外時は ROLLBACK を試行。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム / ETL (`kabusys.data`)
  - ETL パイプラインインターフェース (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETLResult データクラスを導入（取得件数、保存件数、品質チェック、エラー一覧などを保持）。data.etl から ETLResult を再エクスポート。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を行う設計方針を実装（詳細は pipeline モジュールコメントに記載）。
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得し市場カレンダーを保存）。
    - 営業日判定ユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - カレンダー未取得時は曜日ベース（週末除外）でフォールバックする一貫した振る舞いを提供。
    - 最大探索日数上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
    - バックフィル・先読み・健全性チェック（過度に未来日付がある場合はスキップ）を実装。
  - jquants_client（外部連携想定）を利用する箇所を明示（fetch/save 操作の呼び出し）。

- リサーチ / ファクター分析 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum, Value, Volatility, Liquidity 等のファクター計算を実装:
      - calc_momentum(conn, target_date): mom_1m/3m/6m, ma200_dev（データ不足時は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（必要行数未満は None）
      - calc_value(conn, target_date): per, roe（raw_financials から最新財務を取得）
    - DuckDB SQL を主に利用し、prices_daily / raw_financials から計算。外部 API へはアクセスしない設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
      - デフォルト horizons=[1,5,21]、horizons の検証（1..252）あり。
      - 1 クエリで複数ホライズンを取得する実装。
    - IC（Information Coefficient）計算 calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関を実装（ties は平均ランクで処理）。有効レコードが 3 件未満の場合は None。
    - rank(values), factor_summary(records, columns) を提供。
  - 研究用途の設計方針:
    - datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）。
    - DuckDB 接続を受け取り SQL ベースで高速に計算。

- パッケージ公開インターフェース
  - src/kabusys/__init__.py で __all__ = ["data", "strategy", "execution", "monitoring"] を設定（主要サブパッケージの存在を示唆）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意事項 / 実装上の留意点
- 多くの機能が DuckDB を前提としており、prices_daily / raw_news / raw_financials / market_regime / market_calendar / ai_scores 等のスキーマを想定しています。実行前に DB スキーマ準備が必要です。
- OpenAI（gpt-4o-mini）を利用する機能は API キーを引数または環境変数 OPENAI_API_KEY で指定する必要があります。未設定時は ValueError を送出します。
- AI 系処理は外部 API 呼び出しに依存するため、レート制限や一時的なネットワーク障害を考慮したリトライ・フォールバック実装があります。失敗時はスキップして継続する設計です（安全側フェイルセーフ）。
- .env の自動ロードはパッケージ配布後も __file__ を起点にプロジェクトルートを探索するため、CWD に依存しません。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

もしリリースノートに追記したい項目（例: 実装上の既知の制約や今後の予定機能）があれば教えてください。必要に応じて追補して更新します。