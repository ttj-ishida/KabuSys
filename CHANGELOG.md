# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

履歴は逆順（最新が上）で記載します。

## [0.1.0] - 2026-04-09

### 追加 (Added)
- 初回公開リリース。日本株自動売買システム "KabuSys" の基本モジュール群を実装。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートの検出は .git または pyproject.toml を起点に行うため、CWD に依存しない。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local の読み込み順序（OS env > .env.local > .env）と上書き保護（protected keys）をサポート。
  - .env のパース処理を堅牢化：
    - export 形式のサポート、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスで主要設定をプロパティとして提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE チャネル（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID、任意）
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - Paper Trading の挙動（PAPER_FILL_MODE）を検証（有効値: instant|partial|never|reject）
    - 監視用設定（PID ファイル、kill flag、CPU/メモリ/ディスク閾値 等）
    - システム env/log_level の検証（KABUSYS_ENV: development|paper_trading|live、LOG_LEVEL: DEBUG/INFO/...）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) にバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたりの記事数上限・文字数トリム、レスポンス検証、スコアの ±1 クリッピングを実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）は指数バックオフで処理。致命的でない失敗時はスキップして継続するフェイルセーフ設計。
    - テスト容易性のため内部の OpenAI 呼び出しを差し替え可能（unittest.mock.patch を想定）。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ計算: calc_news_window(target_date)（JST ベースの仕様を明記）

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う。
    - OpenAI 呼び出しのリトライ、API エラー時のフォールバック（macro_sentiment = 0.0）を実装。
    - データベースに対する冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値を優先し、未登録日は曜日ベース（週末）でフォールバックする一貫した挙動。
    - 夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装。J-Quants クライアント経由で差分取得し冪等保存する（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー一覧 等を含む）。
    - ETLResult は辞書化メソッド to_dict を持つ（品質問題を dict 化して返す）。

- 研究用（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - ボラティリティ・流動性（calc_volatility）: 20 日 ATR / ATR 比 / 平均売買代金 / 出来高比を計算。
    - バリュー（calc_value）: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS=0 は None）。
    - すべて DuckDB クエリ中心で外部 API 呼び出しなし。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応（デフォルト [1,5,21]）、入力検証あり。
    - IC（calc_ic）: Spearman ランク相関（同順位は平均ランクを採用）を計算。
    - rank, factor_summary（統計サマリー: count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- パッケージ構成
  - 主要サブパッケージ: data, ai, research, 設定・共通ユーティリティを含む __all__ をパッケージ初期化で公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制限 / 設計上の注意事項
- AI モジュールは OpenAI API（gpt-4o-mini）に依存し、API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- LLM 呼び出し失敗時はフェイルセーフでスコアを 0.0 として継続する設計。完全な成功保証はしない（可用性優先）。
- research モジュールは DuckDB のデータ（prices_daily, raw_financials など）を前提とする。データ不足時は None を返す設計。
- calendar_management の最大探索範囲は _MAX_SEARCH_DAYS（60 日）で制限。特殊ケースではエラーになる可能性あり。
- DuckDB バージョン依存の挙動（executemany の空リスト等）に対する互換性配慮あり（空リストは実行しないガードを導入）。
- time.now / date.today の直接参照を避ける設計（ルックアヘッドバイアス防止）。すべて target_date を明示的に渡して使用。

### テスト支援
- OpenAI への実際の API 呼び出しを差し替えられるよう、_call_openai_api 等の内部関数を patch してユニットテストを容易にする設計。

### セキュリティ (Security)
- 機密情報（API トークンやパスワード）は環境変数から取得する設計。README/.env.example を参照して安全に管理すること。

---

今後の予定（短期）
- ETL の実運用ジョブ（差分スケジュール・監視周り）強化。
- Paper Trading の振る舞い検証と自動テスト追加。
- OpenAI レスポンスのさらに厳密なバリデーションとログ改善。
- ドキュメント（Usage / Deployment / Configuration）整備。

以上。