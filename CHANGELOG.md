KEEP A CHANGELOG 準拠（日本語）

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

## [0.1.0] - 2026-03-27
初回リリース

### 追加 (Added)
- パッケージ初期構成
  - パッケージメタ情報: kabusys の __version__ = "0.1.0" を設定。
  - パッケージ公開 API: __all__ に ["data", "strategy", "execution", "monitoring"] を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ から親階層を探索して .git または pyproject.toml を検出して特定（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックスやシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - .env.local は .env の内容を上書き（OS 環境変数は保護）。
  - Settings クラスを公開（settings インスタンス）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須環境変数として取得するプロパティを実装。
    - DB パスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）と展開処理を提供。
    - KABUSYS_ENV と LOG_LEVEL の入力値検証（許容値を列挙）および is_live / is_paper / is_dev のユーティリティプロパティを提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini の JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む処理を実装。
    - スコア処理の特徴:
      - JST ベースの時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行い、内部では UTC naive datetime を使って DB クエリを行う。
      - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を設けてプロンプト肥大化を防止。
      - 最大バッチサイズ 20 銘柄でチャンク処理。
      - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフリトライを実装。
      - レスポンスのバリデーション（JSON 抽出、results 配列、code/score チェック、数値型検証）を行い、不正な応答はスキップして他の銘柄結果を保護。
      - スコアは ±1.0 でクリップ。
      - 書き込みは冪等性を考慮して DELETE（対象 code のみ）→ INSERT を行い、部分失敗時に既存スコアを保護。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api を経由しており、テスト時に patch により差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次で market_regime テーブルにレジーム（"bull"/"neutral"/"bear"）を書き込む機能を実装。
    - 主要処理:
      - prices_daily から 1321 の最新 close と MA200 を用いて ma200_ratio を算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得（最大件数制限）。
      - OpenAI（gpt-4o-mini）によりマクロセンチメントを取得（API 失敗時は macro_sentiment=0.0 でフォールバック）。
      - レジームスコアを合成後、閾値によりラベリング。
      - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - テスト容易性: news_nlp と同様に内部 OpenAI 呼び出しを差し替え可能な設計。

- リサーチモジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時は None を返す。
    - ボラティリティ / 流動性: 20 日 ATR（atr_20）、ATR 比率（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算する calc_volatility を実装。必要行数不足時は None を返す。
    - バリュー: raw_financials からの EPS/ROE を用いて PER・ROE を算出する calc_value を実装。target_date 以前の最新財務データを取得して結合。
    - 全て DuckDB 接続を受け取り SQL を中心に実装（外部 API にアクセスしない）。
    - ログ出力（debug/info）を含む。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（デフォルト horizons=[1,5,21]）を実装。horizons の検証、単一クエリで複数ホライズンの取得を行う。
    - IC（Information Coefficient）計算: calc_ic（スピアマン rho）を実装。十分なデータがない場合は None を返す。
    - ランク関数: rank（同順位は平均ランク）を実装。丸めで ties 判定を安定化。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）を実装。
    - 実装方針: pandas 等に依存せず標準ライブラリ + DuckDB のみで実装、ルックアヘッドバイアス回避（date.today() を参照しない）。

- データプラットフォーム関連 (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定 API を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がある場合は DB 値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - next/prev_trading_day は最大探索日数の上限を設けて ValueError で異常検出。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実行）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
      - ETL のメタ情報（取得数、保存数、品質問題、エラーメッセージ等）を保持し、辞書化機能 to_dict を提供。
      - has_errors / has_quality_errors のユーティリティを提供。
    - ETL の内部ユーティリティ: テーブル存在チェック、最大日付取得、カレンダーヘルパー（_adjust_to_trading_day を含む）などを実装。
    - ETL の設計方針: 差分更新、backfill（デフォルト 3 日）、品質チェックは検出しても処理を継続（呼び出し元で評価）など。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API の外部呼び出しは api_key 引数または環境変数 OPENAI_API_KEY で解決する設計。API キーが未設定の場合は明示的に ValueError を送出して失敗させることで不正利用を防止。

Notes / 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を使う場合）
- DuckDB を用いたテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）に依存するため、ETL によりこれらのスキーマ/データを準備してから利用してください。
- AI モジュールは gpt-4o-mini（JSON Mode）を想定しており、外部 API のエラーや不正レスポンスに対してはフォールバックやスキップ処理を行う設計です（例: macro_sentiment=0.0）。
- テスト容易性のため OpenAI 呼び出し (_call_openai_api) はモジュール内で分離されており、patch による差し替えで模擬応答を注入できます。
- ルックアヘッドバイアス対策として date.today()/datetime.today() をスコープ内で直接参照せず、関数引数の target_date を基準に処理を行う設計になっています。

今後の予定（想定）
- strategy / execution / monitoring の公開 API と実装詳細の追加。
- jquants_client の実装（本リポジトリでは参照されているがコードは別途提供の想定）。
- 単体テスト・統合テストの整備と CI ワークフローの構築。