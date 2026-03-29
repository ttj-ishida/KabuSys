# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys 以下）の現状から推測して作成した初期のリリース記録です。

※ 日付はこのドキュメント作成日です。

## [Unreleased]

### 追加
- なし

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買・リサーチ用ライブラリの基礎機能を実装。

### 追加
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定し、主要サブパッケージ（data, research, ai, execution, monitoring 等）を __all__ で公開。

- 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能をプロジェクトルート（.git または pyproject.toml）から行う実装を追加。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装:
    - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理等を考慮した堅牢なパース。
    - ファイル読み込み失敗時は警告を出す。
  - 必須設定を要求する _require() 実装（未設定時は ValueError）。
  - 主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出し ai_scores テーブルへ保存。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供（UTC naive datetime を返す）。
    - 1銘柄あたりのトークン肥大対策（記事数制限、文字数トリム）。
    - バッチ処理（最大 20 銘柄／回）と、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション処理（JSON 抽出、results 構造検査、未登録コード無視、数値検証、±1.0 でクリップ）。
    - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - API 呼び出し関数はテストで差し替え可能な分離実装。
    - DB 書き込みは部分失敗時に既存スコアを保護する方法（DELETE → INSERT をコード単位で実行）。
    - DuckDB executemany の互換性考慮（空リストの場合実行しない）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算するロジック（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出して LLM（gpt-4o-mini）で macro_sentiment を評価。
    - LLM / API エラー時のフェイルセーフ（macro_sentiment=0.0）とリトライ処理。
    - スコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - モジュール内での設計方針として「datetime.today()/date.today() を参照しない」ことを徹底（ルックアヘッドバイアス防止）。

- データモジュール (kabusys.data)
  - ETL パイプラインの公開 (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開。ETL の取得・保存・品質チェックの結果を格納。
    - 差分取得・バックフィルの方針や DuckDB の最大日付取得ユーティリティ等を実装。
    - テーブル存在チェック、最大日付取得を提供。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定・次/前営業日検索・期間内営業日一覧取得などの関数群を実装。
    - DB 登録がない場合の曜日ベースのフォールバック処理を定義。
    - calendar_update_job() を実装し、J-Quants API から差分取得して market_calendar に冪等保存する夜間バッチ処理を提供（バックフィル機能・健全性チェック含む）。
    - 最大探索日数・先読み日数・バックフィル日数等の定数を定義。
    - market_calendar における NULL 値、未登録日の扱いに関するログ出力の保守性考慮。

  - jquants_client（外部モジュールとして参照）との連携ポイントを確保（fetch/save 関数の利用を想定）。

- 研究モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金 等）の計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_value(conn, target_date)
      - calc_volatility(conn, target_date)
    - DuckDB SQL を用いた実装で、外部 API にはアクセスしない設計。
    - データ不足時の取り扱い（必要数未満なら None）を明確に定義。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
      - 複数ホライズンを一度のクエリで取得、入力検証（horizons の範囲チェック）。
    - IC（Information Coefficient）計算 calc_ic(...)
      - スピアマンランク相関（ランクの計算は ties を平均ランクで処理）。
      - 有効レコードが少ない場合は None を返す堅牢設計。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク、丸めによる ties 対策）。
    - 統計サマリー factor_summary(records, columns)（count/mean/std/min/max/median）。
  - 研究用ユーティリティ（各関数と kabusys.data.stats.zscore_normalize を __all__ で再公開）。

### 変更
- なし（初回リリース）

### 修正
- DuckDB 互換性や堅牢性に関する実装上の注意点を反映
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約を考慮）。
  - OpenAI / HTTP エラーの扱い（5xx はリトライ、それ以外はフェイルセーフでスキップ）を明文化。
  - JSON モードでのパース失敗に対して最外側の {} 部分を抽出して再パースする復元処理を実装（news_nlp）。
  - .env パーサでクォート内のエスケープ処理やインラインコメントの扱いを改善。

### 既知の制限 / 注意事項
- OpenAI API に依存する機能（news_nlp, regime_detector）は API キー（api_key 引数または OPENAI_API_KEY 環境変数）が必須。未設定時は ValueError を送出する。
- LLM 呼び出しは外部ネットワークに依存するため、API 障害時は該当処理をスキップまたは 0.0 にフォールバックする設計（フェイルセーフ）。しかし、結果に影響しうるため運用時は監視が必要。
- 日付取り扱いはすべて date / datetime オブジェクト（timezone-naive）を前提としており、JST/UTC 変換の仕様はドキュメント通り（ニュースウィンドウ等）に従うこと。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols 等）に依存。適切なスキーマ準備が必要。
- 現在のスコア値は ±1.0 にクリップされる設計。
- OpenAI 呼び出しは gpt-4o-mini を想定している（モデル名は定数で管理）。

### セキュリティ
- .env 自動読み込みはデフォルトで有効だが、テスト等で無効化するためのフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
- 環境変数の読み込み時に OS 環境の既存キーを保護する仕組みを実装（.env 読み込み時の protected set）。

---

過去リリースや将来の変更はここに追記してください。必要であれば各モジュールごとのより詳細な変更履歴や設計ノートを別ファイルとして展開できます。