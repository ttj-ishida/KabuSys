# Changelog

全ての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベースから推測して記載しています。

※ この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。

- [Unreleased]
- [0.1.0] - 2026-03-31

## [Unreleased]
（次版の変更点をここに記載）

---

## [0.1.0] - 2026-03-31

初期公開リリース。本バージョンでは日本株自動売買およびデータ基盤・研究機能に必要な基礎モジュール群を実装しています。設計上の考慮（ルックアヘッドバイアス回避、冪等性、フェイルセーフな外部API呼び出し、DuckDBベースの処理など）が各所で取り入れられています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは `0.1.0` に設定。
  - パッケージ公開用の __all__（data, strategy, execution, monitoring）を定義。

- 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により、CWD に依存しない自動 .env 読み込みを実現。
  - .env パーサーの細かい仕様対応：
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用途など）。
  - 必須変数取得ヘルパー `_require()` と Settings クラスを実装。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AIモジュールで使用）
  - デフォルト値:
    - KABUSYS_ENV デフォルト `development`（検証済み値: development, paper_trading, live）
    - LOG_LEVEL デフォルト `INFO`
    - DUCKDB_PATH デフォルト `data/kabusys.duckdb`
    - SQLITE_PATH デフォルト `data/monitoring.db`

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルを元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いたセンチメント評価を実装。
    - バッチ（最大 20 銘柄）での JSON Mode 呼び出し、スコア検証、スコア ±1.0 クリップ、DuckDB への冪等的な書き込み（DELETE→INSERT）を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリを実行）。
    - リトライ/バックオフ: 429, 接続断, タイムアウト, 5xx に対して指数バックオフで再試行。
    - レスポンスバリデーション、JSON パース耐性（前後余計テキストの抽出）を実装。
    - 失敗時は該当チャンクをスキップするフェイルセーフ設計。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）を用いてマクロセンチメントを算出。
    - ルックアヘッドバイアスの防止を明確に設計（target_date 未満のみを参照、datetime.today() を直接参照しない）。
    - API 呼び出しのリトライ（429/接続断/タイムアウト/5xx）および失敗時のフォールバック（macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェック統合を目的とした ETLResult データクラスを提供。
    - DuckDB の最終日取得ユーティリティ、テーブル存在確認等のユーティリティを実装。
    - エラーと品質問題を収集して呼び出し元で扱える設計。
    - ETLResult.to_dict() で品質問題をシリアライズ可能。
    - ETLResult は kabusys.data.etl に再エクスポート。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX 市場カレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データがない/未登録時には曜日ベース（土日非営業日）でフォールバック。DB 登録がある場合はそれを優先。
    - 最大探索範囲を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - カレンダーのバックフィルと健全性チェック（将来日付の異常検出）。
  - jquants_client を用いたデータ取得/保存の想定（モジュール参照あり）。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の取り扱い（None 戻し）やスキャン範囲バッファ等を考慮。
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
    - 入力検証（horizons の範囲チェック等）や欠損処理を行う。

- ロギング/運用
  - 各モジュールで詳細なログメッセージを出力するよう設計（INFO/DEBUG/WARNING）。
  - DB 書き込み前の BEGIN/COMMIT/ROLLBACK といったトランザクション制御を統一的に実装し、失敗時の ROLLBACK と警告ロギングを行う。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。キーをハードコーディングしない設計。

### Notes / 実装上の重要なポイント
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定は target_date を明示して過去データのみ参照する設計。datetime.today()/date.today() を直接用いない。
- 外部 API のフェイルセーフ:
  - OpenAI 呼び出しは 429/接続断/タイムアウト/5xx に対する再試行と、全失敗時の安全なデフォルト（ニューススコア 0.0 やチャンクスキップ）を提供。
- DuckDB 互換性:
  - executemany に空リストを渡せない制約に配慮した実装（空チェックを行う）。
- .env パーサーは一般的なシェル形式（export, クォート、エスケープ、インラインコメント）をサポート。ただし特殊ケースは要確認。
- OpenAI モデル:
  - gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で使用する想定。JSON パースエラーに対する耐性を持つ。

### Breaking Changes
- 初期リリースのため該当なし。

---

以上。必要であれば各ファイルごとの簡易 API 参照（公開関数一覧）や環境変数一覧、例 .env.example を基にした設定テンプレートを作成します。希望があれば追記してください。