# Changelog

すべての変更は https://keepachangelog.com/ja/ のフォーマットに準拠しています。

エントリはセマンティックバージョニングに従います。初回リリースは 0.1.0 です。

## [Unreleased]

（現在のコードベースは初回リリース 0.1.0 相当です。今後の変更はここに記載します。）

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ全体
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数・設定読み込みモジュール（kabusys.config）
    - .env / .env.local の自動ロード機構（OS 環境変数を保護する仕組み含む）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .git または pyproject.toml を起点にプロジェクトルートを探索して .env を読み込む（カレントワーキングディレクトリに依存しない）。
    - .env のパース実装（export 形式、クォート対応、インラインコメント処理など）。
    - Settings クラスを提供（settings インスタンスをエクスポート）。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV 値検証（development/paper_trading/live）
      - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev ヘルパー
- AI（自然言語処理）機能
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）に JSON Mode で投げてスコア化。
    - バッチ処理（デフォルト _BATCH_SIZE=20）・記事トリミング（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JST 基準のニュース時間ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換）を calc_news_window で提供。
    - 再試行（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）、レスポンス検証、スコアの ±1.0 クリップ。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock.patch 推奨）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。API キーは引数で注入可（テスト容易性）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で 'bull'/'neutral'/'bear' を判定。
    - マクロキーワードによる記事フィルタリング、OpenAI（gpt-4o-mini）呼び出し、レスポンスの JSON パース、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う score_regime(conn, target_date, api_key=None) を提供。
- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research パッケージを追加。主要関数を公開:
    - factor_research.calc_momentum(conn, target_date)
      - 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - factor_research.calc_volatility(conn, target_date)
      - 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - factor_research.calc_value(conn, target_date)
      - raw_financials から最新財務データを取得して PER / ROE を計算。
    - feature_exploration.calc_forward_returns(conn, target_date, horizons=None)
      - 将来リターン（翌日/翌週/翌月デフォルト）を計算（複数ホライズンに対応）。
    - feature_exploration.calc_ic(factors, forwards, factor_col, return_col)
      - スピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - feature_exploration.rank(values)／factor_summary(records, columns)
      - ランク化・統計サマリーを標準ライブラリのみで実装。
  - zscore_normalize は kabusys.data.stats から再公開（__init__）。
- データ基盤（Data）
  - kabusys.data パッケージの主要モジュール:
    - calendar_management
      - JPX マーケットカレンダーの判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB がない場合は曜日（土日）ベースのフォールバックを行う。
      - 夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=90)（J-Quants クライアント経由で差分取得・保存、バックフィル・健全性チェックあり）。
    - pipeline
      - ETLResult データクラス（ETL 実行の集約結果を保持）。差分取得、保存、品質チェックのフローを想定。
      - 内部ユーティリティ: テーブル存在確認・最大日付取得など。
    - etl.py で ETLResult を再エクスポート。
  - jquants_client（インポート参照）との連携を前提。ETL とカレンダー更新は jquants_client.fetch_* / save_* を使用。
- ロギング・堅牢性
  - 多くの処理で警告/情報ログを出すよう実装。DB トランザクションの失敗時は ROLLBACK を試行し、失敗時には警告ログを残す。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接スコア計算や API 呼び出しの基準に使用しない設計。
  - DuckDB を主要な分析 DB として使用（関数は DuckDB 接続を受け取るインタフェース）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env 読み込み時、既存の OS 環境変数を protected set として扱い誤って上書きされるのを防止（.env.local は override=True だが protected に入ったキーは上書きしない）。

### 注意事項 / 既知の設計判断
- OpenAI API に依存する機能（score_news, score_regime）は API キーが必須。api_key を関数引数で注入でき、テスト時の差し替えが容易。
- DuckDB の executemany に空リストを渡せない制約（DuckDB 0.10）に配慮した実装（空チェックあり）。
- raw_news / prices_daily / raw_financials / market_regime / ai_scores 等のテーブルスキーマが前提。テーブルが存在しない場合は多くの関数が None や空結果を返す設計。
- LLM レスポンスは厳密な JSON を期待するが、JSON mode を使用しても余計なテキストが混入するケースに備えたパース回復処理を実装。
- テスト容易性のため、OpenAI 呼び出し部分（内部関数）をパッチして挙動を模擬可能。

---

開発チームへ:
- 次バージョンでは API ドキュメント（公開関数の引数・返り値・期待スキーマ）を拡充することを推奨します。
- テストカバレッジ（特に OpenAI エラー/リトライパス、DuckDB の挙動、.env パースの境界ケース）を強化してください。