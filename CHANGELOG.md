# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトでは「Keep a Changelog」形式に準拠し、Semantic Versioning を意識してバージョニングしています。

## [Unreleased]
（現時点での未リリース変更はありません）

## [0.1.0] - 2026-04-04
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - パッケージの公開 API として主要サブパッケージを想定（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）または環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に __file__ から探索（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数を上書きしない保護機能（protected set）。
  - .env パース機能: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱いなど。
  - 必須設定取得ヘルパー `_require` と Settings クラスを提供。主なプロパティ:
    - J-Quants / kabuStation / LINE / データベース (duckdb/sqlite パス) / 監視設定 (PID・kill flag・閾値) / 環境 (development/paper_trading/live) / ログレベル
  - 不正な KABUSYS_ENV、LOG_LEVEL の値検証（ValueError）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを算出・`ai_scores` テーブルへ保存する `score_news` を実装。
    - 時間ウィンドウ計算（JST ベース、UTC 変換）関数 `calc_news_window` を提供。
    - バッチサイズ制御、記事・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証・スコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ DELETE → INSERT）などを実装。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - prices_daily / raw_news を参照、MA 計算、マクロキーワードで記事フィルタ、OpenAI 呼び出し（gpt-4o-mini JSON mode）、フェイルセーフ（API失敗時 macro_sentiment=0.0）等を備える。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ai パッケージの公開 API として `score_news`, `score_regime` の利用を想定（ai/__init__.py にエクスポート）。

- データ基盤 (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job`、market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末非営業日）を一貫して適用。
    - 最大探索幅や健全性チェック、バックフィル挙動を実装して異常検出をサポート。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL 実行結果を表す dataclass `ETLResult` を提供（取得件数・保存件数・品質問題・エラーの収集）。
    - 差分更新・バックフィル・品質チェック方針に沿った基盤実装（jquants_client, quality モジュールとの連携を想定）。
    - data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）などを計算する関数群 `calc_momentum`, `calc_volatility`, `calc_value` を実装。
    - DuckDB 上で SQL とウィンドウ関数を活用して高速に計算する設計。
    - 不足データ時は None を返す等の堅牢性を持つ。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応）、IC（Spearman ρ）計算 `calc_ic`、ファクター統計サマリ `factor_summary`、ランク付け `rank` を提供。
    - pandas 等の外部依存を持たない純粋 Python 実装。

- 一般設計の特徴
  - DuckDB を中心としたローカルデータベース設計（DuckDB 接続を各関数が受け取る）。
  - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() に依存しない設計（target_date を明示）。
  - OpenAI 呼び出しは JSON Mode を用い、レスポンスの頑健なパース処理やパース失敗時のフォールバックを実装。
  - テスト容易性を考慮し、OpenAI 呼び出し箇所の差し替えポイントを確保。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 実運用での安定性を考慮した実装上の配慮を多数導入:
  - DuckDB の executemany に空リストを渡さないガード（互換性対策）。
  - OpenAI API エラー処理で 5xx とそれ以外を区別し、適切にリトライ／フォールバックを行う実装。
  - JSON mode のレスポンスに余分なテキストが混ざるケースに対する復元処理（最外の {} を抽出してパース）を追加。
  - market_calendar の NULL 値検出時に警告を出し、曜日フォールバックする挙動の実装。

### セキュリティ (Security)
- 環境変数や .env の取り扱いについて:
  - 必須シークレット（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 内で必須化（存在しない場合は ValueError）。
  - .env 自動読み込みは既存 OS 環境変数を上書きしない（保護）設計。テスト時は自動読み込みを無効化可能。
  - OpenAI API キーは引数で注入可能。未設定で score_news / score_regime を呼ぶと ValueError を返す。

### 互換性 (Compatibility)
- 初版リリース。後方互換性確保のため、公開関数は明示的に target_date と conn（DuckDB 接続）を取る設計としています。将来のバージョンで API 変更がある場合はメジャーバージョンアップで通知します。

### 利用上の注意 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須（Settings 内で _require により検証）。
- OpenAI API:
  - score_news / score_regime は OpenAI API（gpt-4o-mini）を利用する想定。API キーは引数 api_key か環境変数 OPENAI_API_KEY を利用してください。
  - API 呼び出しは外部ネットワークや課金が発生するため、本番運用前に十分なテストを行ってください。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - 必要に応じて環境変数で上書きしてください（DUCKDB_PATH, SQLITE_PATH）。

---

もし特定の変更点（例: リリース日や追加で強調したい API）があればその旨を教えてください。CHANGELOG をバージョン履歴に合わせて更新します。