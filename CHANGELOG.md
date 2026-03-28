# Changelog

すべての注目すべき変更をここに記載します。慣例に従い、変更は semver に基づき整理しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数を読み込む自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env/.env.local の優先度処理（OS 環境変数 > .env.local > .env）。.env.local は上書き（override）される。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（export KEY=val 形式、シングル/ダブルクォート、インラインコメント対応、エスケープ処理）。
  - Settings クラスによる型安全な設定取得プロパティ（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
  - 必須環境変数の検査（_require）で未設定時は ValueError を送出。
  - 環境変数の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたり記事数・文字数の上限トリム、JSON mode レスポンスのバリデーション実装。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）は指数バックオフでリトライ。失敗したチャンクはスキップし、他チャンクへの影響を最小化。
    - DuckDB への冪等書き込み（DELETE → INSERT）で既存スコアの保護。
    - テスト用に _call_openai_api を patch できる設計。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini を使用。API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジーム結果を market_regime テーブルへトランザクションで冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出しは news_nlp と実装を分離（モジュール結合を避ける）。
    - テスト用に _call_openai_api を patch 可能。

- データ管理 (src/kabusys/data)
  - ETL パイプライン公開インターフェース (etl.py / pipeline.py)
    - ETLResult dataclass を実装（取得数、保存数、品質問題、エラー等を表現）。
    - 差分更新、バックフィル、品質チェックの設計方針を具現化（J-Quants クライアント抽象化）。
    - DuckDB を利用した最大日付検査・テーブル存在チェック等のユーティリティ。
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未登録日は曜日ベースでフォールバックする一貫した設計。
    - calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック、保存処理（jq.fetch_market_calendar / jq.save_market_calendar を想定）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）による無限ループ防止。

- リサーチ（src/kabusys/research）
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金, 出来高比）を DuckDB 上で計算。
    - データ不足時の None 処理、営業日スキャン範囲のバッファ設定など。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（任意 horizon）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリー。
    - pandas 等に依存しない純 Python 実装。

- 汎用 / その他
  - DuckDB を想定した SQL 実行や日付/型変換ユーティリティを多数実装。
  - ロギング、警告の付与、例外伝播の設計（DB 書き込み失敗時の ROLLBACK と再送出など）。
  - テスト容易性を考慮した設計（OpenAI 呼び出しの差し替えポイントなど）。
  - デフォルト DB パス: duckdb -> data/kabusys.duckdb, sqlite -> data/monitoring.db。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### 非推奨 (Deprecated)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 環境変数や API キーは直接コードに埋め込まず環境変数経由で取得（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。未設定時は明示的なエラーを発生させることで誤設定を検出しやすくしています。
- .env ファイル読み込みはプロジェクトルート検出に基づくため、誤った cwd に依存しないように設計。

---

注記:
- OpenAI との連携部分は外部 API 呼び出しに依存するため、API 変更やレート制限に応じて将来的な調整が必要になる可能性があります（モデル名や SDK の例外型等）。
- DuckDB のバージョンによる executemany の挙動差異（空リスト不可等）を考慮した実装が含まれています。
- 今後のリリースでは、ユニットテスト、型注釈の強化、外部クライアントの抽象化、実運用向けの監視・エラーレポーティングを予定しています。