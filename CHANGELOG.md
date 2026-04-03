# Changelog

すべての注目すべき変更をここに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ初期版を追加。バージョンは `0.1.0`。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - OS 環境変数は保護（protected set）され、`.env.local` の上書きは制御可能。
  - .env パーサ実装:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - クォートなしでのインラインコメント認識（直前がスペース／タブの場合）。
  - 必須環境変数取得用 `_require` ユーティリティ。
  - 各種設定プロパティ（J-Quants トークン、kabu API、LINE トークン、DB パス、監視用ファイルパス、リソース閾値、実行環境/ログレベル判定など）を `Settings` クラスとして提供。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許可値は固定集合）。

- AI 関連 (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価して `ai_scores` テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC 変換で前日 06:00 〜 23:30）を採用。calc_news_window ユーティリティを提供。
    - 銘柄あたりの上限: 最大記事数と文字数（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）でトリム。
    - バッチ処理: 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ。
    - レスポンス検証: JSON 抽出・構造検証（results リスト・code/score）とスコアの ±1.0 クリッピング。
    - DB 書き込みは部分失敗耐性あり（成功したコードのみを DELETE → INSERT で置換し、他の既存スコアを保護）。
    - テスト用に API 呼び出し関数を差し替え可能（unittest.mock.patch 対応）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースは news_nlp の calc_news_window を使ってウィンドウ抽出、LLM は gpt-4o-mini、JSON Mode で評価。
    - スコア合成後に閾値でラベル化（BULL/BEAR の閾値定義あり）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - API 失敗時は macro_sentiment = 0.0 としてフォールバック（フェイルセーフ）。
    - OpenAI クライアント呼び出しは独立実装で、モジュール間のプライベート関数共有を避ける設計。

- リサーチ / ファクター (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金/出来高比率）、Value（PER/ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの実装。prices_daily / raw_financials テーブルのみ参照し、外部 API は呼ばない設計。
    - データ不足時は None を返す等の堅牢な取り扱い。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（複数ホライズン、デフォルト [1,5,21]）を一クエリで取得するロジック。
    - Spearman（ランク相関）による IC 計算（calc_ic）を実装。3 銘柄未満では None を返す。
    - ランク化ユーティリティ（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
  - data.stats の zscore_normalize を再エクスポート（src/kabusys/research/__init__.py）。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの保持・判定ロジックを実装（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータが無い場合は曜日ベースのフォールバック（土日非営業日）。
    - calendar_update_job を実装し J-Quants API から差分取得 → 保存（jq クライアント経由）する夜間バッチ処理を提供。
    - バックフィル、健全性チェック（将来日付の異常検出）、最大探索日数制限等の安全対策を導入。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装して ETL 実行結果を集約（取得数、保存数、品質問題、エラー一覧等）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）・idempotent 保存（jquants_client の save_*）の方針を実装。
    - ETLResult を etl モジュールで公開（ETLResult の再エクスポート）。

### 変更 (Changed)
- 設計上の注意点（全体）
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を直接参照しない関数設計を採用（target_date 引数に依存）。
  - DuckDB を主要な永続化層として使用（標準ライブラリと DuckDB + OpenAI SDK に依存）。
  - OpenAI 呼び出しは JSON Mode を想定し、レスポンスの堅牢なパース・検証処理を導入。
  - テスト容易性のため、API 呼び出し部分をモック差し替え可能に実装。

### 修正 (Fixed)
- フォールバック / フェイルセーフの強化
  - AI API エラー時はスコアを 0.0 にフォールバックして処理継続（例外のバブリングを抑制）する実装を導入。これにより外部サービス障害時でもパイプライン全体の継続が可能。
  - DB 書き込み中の例外ハンドリングで ROLLBACK を試み、失敗時は警告ログを出すように変更。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API キーは必須（関数引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- DuckDB の executemany に空リストを渡すとエラーとなるため、書き込み時に空チェックを行っている（互換性対策）。
- J-Quants クライアント（jquants_client）は外部依存であり、API 呼び出しや保存処理の実装は別モジュールに分離されている。
- 初期リリースでは PBR・配当利回りなど一部バリューファクターは未実装。

### セキュリティ (Security)
- 環境変数の自動ロード時に OS の環境変数を保護する仕組みを導入（protected set）。.env による意図しない上書きを防止。

---

貢献者: 初期開発チーム

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴に基づく正確な変更履歴はリポジトリの VCS ログを参照してください。）