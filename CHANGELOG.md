# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースバージョンは semver を使用します。  
- 日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-27
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys。トップレベルに data / research / ai / ... のサブパッケージを公開。
  - バージョンを `__version__ = "0.1.0"` として設定。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は __file__ を基準に親ディレクトリを探索し `.git` または `pyproject.toml` を検出。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
  - .env のパース機能を実装:
    - `export KEY=val` 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での挙動の違い）に対応。
    - ファイル読み込み失敗時は警告を出すフェイルセーフ。
    - override / protected を利用した上書き制御（OS側の環境変数を保護）。
  - Settings クラスを実装し、プロパティ経由で設定取得を提供:
    - J-Quants / kabu API / Slack / DB パス等のプロパティ（必須項目は未設定時に ValueError）。
    - `duckdb_path` / `sqlite_path` のデフォルトを設定（`data/kabusys.duckdb`, `data/monitoring.db`）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証（許容値チェック）。
    - ユーティリティプロパティ: `is_live`, `is_paper`, `is_dev`。

- AI モジュール（OpenAI 統合）
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）にバッチ（最大 20 銘柄/リクエスト）で問い合わせてセンチメントを算出。
    - ニュース収集ウィンドウ計算（JST基準の前日15:00～当日08:30 -> UTC換算）: `calc_news_window` を実装。
    - 1銘柄あたりの最大記事数・文字数制限、JSON Mode レスポンスの検証、レスポンスパース冗長性（前後余白のある JSON から {} を抽出）に対応。
    - レート制限/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップし、取得したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - テストのため `_call_openai_api` を patch で差し替え可能に設計。
    - 公開 API: `score_news(conn, target_date, api_key=None)`（戻り値: 書き込んだ銘柄数）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワードでの抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、両者の線形合成と閾値判定を実装。
    - DB への冪等保存（BEGIN / DELETE / INSERT / COMMIT）。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 公開 API: `score_regime(conn, target_date, api_key=None)`（戻り値: 1 成功、API キー未設定時は ValueError）。

- Data モジュール
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX マーケットカレンダーの扱い（market_calendar テーブル）と夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装。
    - 営業日判定 API: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を提供。
    - market_calendar が未取得/まばらな場合は曜日ベースのフォールバック（土日非営業）で整合を保つ設計。
    - 最大探索範囲やバックフィル／健全性チェックの実装（設定された定数で制御）。
    - J-Quants クライアント経由の fetch/save を利用（jquants_client を使用）。

  - ETL パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETL の結果を表す `ETLResult` dataclass を実装（取得数・保存数・品質問題・エラー一覧など）。
    - 差分取得、バックフィル、品質チェックの方針を反映したユーティリティ関数と内部ヘルパー（テーブル存在確認、最大日付取得等）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン・ma200乖離）、Volatility（20日 ATR・相対ATR・流動性指標）、Value（PER, ROE）を DuckDB と SQL ロジックで計算する関数を実装:
      - `calc_momentum(conn, target_date)`
      - `calc_volatility(conn, target_date)`
      - `calc_value(conn, target_date)`
    - データ不足時は None を返す設計、計算は prices_daily/raw_financials のみ参照。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman ランク相関）。
    - ランク変換ユーティリティ: `rank(values)`（同順位は平均ランク）。
    - 統計サマリー: `factor_summary(records, columns)`（count/mean/std/min/max/median）。
  - research パッケージの __all__ で主要関数を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 / 運用メモ
- AI 機能（score_news / score_regime）は OpenAI API キーを必要とする:
  - 引数で `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定すること。未設定時は ValueError が発生する。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings のプロパティ参照）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - 必要に応じて環境変数 `DUCKDB_PATH`, `SQLITE_PATH` で変更可能。
- .env パースの挙動:
  - クォートありの場合は内部でバックスラッシュエスケープを処理し、以降のインラインコメントは無視します。
  - クォートなしでは '#' の直前にスペース/タブがある場合にそこでコメントと見なします（一般的な .env の曖昧さに配慮）。
- DuckDB に対する executemany の空リストバインド制約に配慮した実装（空リスト時は操作をスキップ）。
- 時間・日付関連処理はルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を直接参照しない設計を意識している箇所がある（score_news/score_regime 等）。

### セキュリティ (Security)
- 初回リリースのため該当なし。OpenAI キーや外部 API トークンは環境変数で管理することを想定。

もし詳細なリリースノート（各関数の入力/出力例、環境変数一覧やマイグレーション手順）の作成を希望される場合は、対象のモジュール/関数を指定してください。