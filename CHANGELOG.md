# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ付けされているバージョンはパッケージ内部の __version__（0.1.0）に基づきます。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-09
初期リリース。以下の主要機能とモジュールを実装しています。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ識別子とバージョンを src/kabusys/__init__.py にて定義（__version__ = "0.1.0"）。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込みする実装。
    - 読み込み優先順位: OS 環境変数 > .env.local (> .env)
    - プロジェクトルートは __file__ の親ディレクトリ列挙で `.git` または `pyproject.toml` を探索して特定。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは export 形式、クォート・エスケープ、インラインコメント処理などをサポート。
  - Settings クラスを提供。主要設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY の参照元、DB パス、Paper Trading 用設定、監視閾値、環境・ログレベル検証など）をプロパティ経由で取得可能。
  - 環境値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）により不正値を検出して例外を投げる。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄候補選定: select_candidates — スコア降順・同点タイブレーク実装。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重。全スコア0なら等分フォールバックと WARNING）。
  - リスク調整: apply_sector_cap（セクター集中上限チェック、売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは上限未適用）、calc_regime_multiplier（市場レジームに応じた投下資金乗数、未知レジームは警告ログを出してフォールバック）。
  - 株数決定: calc_position_sizes（allocation_method="risk_based"|"equal"|"score" サポート、単元株丸め、1銘柄上限、利用可能現金に基づく aggregate cap、cost_buffer による保守的コスト見積り、スケーリングと残差処理による再配分ロジック）。

- 研究（リサーチ）モジュール (src/kabusys/research/)
  - ファクター計算: calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）、calc_value（PER/ROE の計算。raw_financials から最新レコードを取得）。
  - 特徴量探索: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（ファクターと将来リターンのスピアマンランク相関）、factor_summary（基本統計量: count/mean/std/min/max/median）、rank（同順位は平均ランクで処理、丸めで ties 検出安定化）。
  - 実装方針: DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、外部 API にはアクセスしない。

- AI 系機能 (src/kabusys/ai/)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）に送信し、銘柄別センチメントスコアを ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄当たり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - API 呼び出しは JSON Mode を利用、レスポンスの堅牢なバリデーションと ±1.0 でのクリッピング。
    - 429/ネットワーク/タイムアウト/5xx のリトライ・指数バックオフを実装。致命的でない失敗時はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）で、部分失敗時に他コードの既存スコアを保持する。
    - 日時処理でルックアヘッドバイアスを避ける設計（datetime.today() を参照しない）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime: ETF 1321 の ma200 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を決定し market_regime テーブルへ書き込む。
    - マクロ記事抽出はキーワードベース、API 失敗時は macro_sentiment=0.0 でフォールバック。
    - LLM 呼び出しと retry ロジックを備え、DB 書き込みはトランザクションで実施。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を用いた MonitoringDB 初期化関数 init_monitoring_db を提供（複数テーブルとインデックスを作成する冪等スクリプト）。
  - テーブル例: system_status, trade_logs, positions, risk_logs（スキーマはコード内に定義）。

- モジュールエクスポートの整備
  - pakage-level __all__ を用いて主要 API（portfolio / research / ai）をエクスポート。

### 変更 (Changed)
- 初期リリースのため、既存コードからの変更点はありません。

### 修正 (Fixed)
- 初期リリースのため、バグ修正履歴はありません。

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーや各種機微情報は環境変数経由で取得する設計。キー未設定時は明示的に ValueError を投げる箇所があるため、運用時は環境変数（例: OPENAI_API_KEY）や .env を適切に設定してください。

---

補足 / 注意事項
- 本リリースは「初期実装」を含みます。将来的に以下の改善が想定されています:
  - 単元株（lot_size）の銘柄別対応（現状は全銘柄共通の lot_size）。
  - price の欠損時のフォールバック（前日終値や取得原価の利用）に関する拡張。
  - DuckDB / SQLite のバージョン互換性や executemany の空リストに関する注意（コード内に対応が記載されています）。
- 本パッケージは DuckDB と OpenAI Python SDK（openai）への依存を想定しています。利用前に必要パッケージと環境変数を整えてください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）。

----- 
（この CHANGELOG はコードから推測して作成しています。運用上の正式なリリースノートは実際のコミット履歴やリリース手順に基づき更新してください。）