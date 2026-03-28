# Changelog

すべての注目すべき変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初回リリース
  - パッケージメタ: `kabusys.__version__ = "0.1.0"`。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（優先順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルートの探索は `__file__` を起点に `.git` または `pyproject.toml` を探す実装で、CWD に依存しない挙動。
  - `.env` のパースロジックを独自実装:
    - `export KEY=val` 形式対応、コメント行・空行無視、シングル/ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメントの取り扱い。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テストや特殊な実行環境向け）。
  - OS 環境変数は保護（protected set）され、`.env.local` の上書きから保護可能。
  - `Settings` クラスを提供し、アプリケーション設定をプロパティで参照可能:
    - J-Quants / kabuステーション / Slack トークンなど（`_require` による必須チェック）。
    - DB パス設定（`duckdb_path`, `sqlite_path`）とパス展開。
    - `KABUSYS_ENV`（`development`, `paper_trading`, `live`）と `LOG_LEVEL` の入力検証。
    - 環境判定ヘルパ (`is_live`, `is_paper`, `is_dev`)。

- ニュース NLP / AI スコアリング（kabusys.ai.news_nlp）
  - ニュース記事を銘柄単位に集約し（前日15:00 JST 〜 当日08:30 JST のウィンドウ）、OpenAI (`gpt-4o-mini`) にバッチで送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
  - 実装上の特徴:
    - タイムウィンドウ計算関数 `calc_news_window(target_date)` を提供（UTC naive datetime を返す）。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・最大 3000 文字にトリムするサニティ処理。
    - OpenAI への JSON Mode （`response_format={"type":"json_object"}`）呼び出しと厳密なレスポンス検証。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。非リトライ対象・致命的なエラーはそのチャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンス検証で unknown code の無視、数値変換と有限値チェック、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗耐性を考慮して、取得済みコードのみを `DELETE` → `INSERT` で置換（DuckDB の executemany 空パラメータ回避に配慮）。
    - テスト容易性: `_call_openai_api` をモジュール内で分離しモック可能に設計。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（`bull` / `neutral` / `bear`）を判定。
  - 実装上の特徴:
    - MA200 乖離の計算は `target_date` 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロキーワードフィルタリングで最大 20 記事を抽出し、OpenAI に送信して `macro_sentiment` を得る。API 失敗時は `macro_sentiment=0.0` にフォールバック。
    - レジームスコア合成（重み付け + クリップ）と閾値によるラベル化。
    - `market_regime` テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実行。DB 書き込みエラー時は ROLLBACK を試行して上位へ例外を伝播。
    - テスト用に OpenAI 呼び出しの差し替えを想定（ `_call_openai_api` を別実装にしている点に注意）。

- データプラットフォーム関連（kabusys.data.*）
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定ユーティリティを提供: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB にカレンダーがない場合は曜日ベース（土日休み）でフォールバックするロジック。DB 登録値は優先、未登録日は曜日フォールバックで一貫した挙動。
    - 安全装置: 最大探索日数 `_MAX_SEARCH_DAYS`、バックフィル `_BACKFILL_DAYS`、先読み `_CALENDAR_LOOKAHEAD_DAYS`、健全性チェック `_SANITY_MAX_FUTURE_DAYS`。
  - ETL パイプライン（kabusys.data.pipeline / etl）:
    - ETL の設計方針に基づく差分取得・保存・品質チェックワークフローを実装（J-Quants クライアントと quality モジュールを使用）。
    - 結果を表す `ETLResult` データクラスを定義（取得件数、保存件数、品質問題リスト、エラーリストなど）。`data/etl.py` で `ETLResult` を再エクスポート。
    - 差分取得のための最小データ開始日 `_MIN_DATA_DATE`、既定のバックフィル `_DEFAULT_BACKFILL_DAYS` 等を定義。
    - DuckDB に対する互換性配慮（テーブル存在チェック / MAX 日付取得ユーティリティ / executemany 空リスト回避等）。
    - 品質チェックは Fail-Fast ではなく呼び出し元が判断できるよう、問題を収集する方針。

- リサーチ / ファクター計算（kabusys.research.*）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum: `calc_momentum(conn, target_date)`（1M/3M/6M リターン、200 日 MA 乖離）。
    - Volatility & Liquidity: `calc_volatility(conn, target_date)`（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）。
    - Value: `calc_value(conn, target_date)`（PER, ROE。raw_financials から最新財務を取得して組み合わせ）。
    - 実装は DuckDB を用いた SQL+Python ハイブリッド。データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（LEAD を用いた同一クエリでの取得、horizons の検証）。
    - IC 計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman ランク相関、有効レコードが 3 件未満で None を返す）。
    - ランク変換: `rank(values)`（同順位は平均ランク、丸めで ties を安定化）。
    - 統計サマリー: `factor_summary(records, columns)`（count/mean/std/min/max/median）。外部依存ライブラリ（pandas 等）に依存せず標準ライブラリで実装。

### Design / Implementation notes
- ルックアヘッドバイアス対策:
  - AI モジュール（news_nlp, regime_detector）および ETL/リサーチ系の関数は内部で `datetime.today()` / `date.today()` を参照せず、引数で渡された `target_date` のみを基準に計算する設計。
- OpenAI 呼び出し:
  - 使用モデルは一貫して `gpt-4o-mini` を想定。JSON Mode を使った厳密な JSON 応答を期待。
  - API 呼び出しロジックはモジュール内で分離されており、テスト時はパッチで差し替え可能。
  - レート制限・ネットワーク障害・サーバーエラーに対する指数バックオフリトライ実装。
- DB 書き込みの冪等性:
  - AI スコアやレジームなどの DB 書き込みは既存行の削除→挿入や ON CONFLICT を意識した設計で、部分失敗が発生しても既存データを不必要に消さないよう配慮。
- DuckDB 互換性:
  - `executemany` に空リストを渡さないチェック等、DuckDB の既知制約に対応。
- ロギングとフェイルセーフ:
  - API失敗やレスポンスパース失敗時は警告ログ出力の上、可能な限り処理を継続（特に外部 API に依存する AI スコア処理はフォールバック値やスキップで安全に継続）。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。  

もし CHANGELOG に追加してほしい詳細（例えば各関数の安定性注意点や公開 API の例、環境変数一覧など）があれば教えてください。必要に応じて別セクションで追記します。