# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

注記:
- 本リリースノートはソースコードから推測して作成しています。実際のリリースノート作成時には実稼働情報・コミット履歴を参照してください。

## [Unreleased]

## [0.1.0] - 2026-04-09

初回公開リリース。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）または環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準に探索）。
  - .env 解析器を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
    - DUCKDB_PATH, SQLITE_PATH（データベースパス）
    - PAPER_FILL_MODE（paper trading の挙動を制御: instant/partial/never/reject のバリデーション含む）
    - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 SQLite パス）
    - プロセス監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - リソース閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 実行環境判定: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（バリデーション有）
    - Settings.is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを計算し、ai_scores テーブルへ保存する score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（最大記事数・最大文字数）を実装してトークン肥大を抑制。
    - API 呼び出しでのリトライ / エクスポネンシャルバックオフ、およびレスポンスバリデーション実装（JSON 抽出、results 検証、コード照合、スコア数値化、±1 クリップ）。
    - テスト容易性のため OpenAI 呼び出し関数に差し替えポイント（_call_openai_api）を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロキーワードによる raw_news フィルタリング、OpenAI（gpt-4o-mini）呼び出し、API エラー時のフェイルセーフ（macro_sentiment=0.0）をサポート。
    - レジーム計算結果を market_regime テーブルへ冪等に保存（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しのリトライおよび 5xx とそれ以外の扱いを区別して実装。テスト用差し替えポイントあり。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を参照した営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダーが存在しない場合の曜日ベースのフォールバックを採用し、DB と一貫した挙動を確保。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間ジョブ calendar_update_job を実装（バックフィル、健全性チェック含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開し、ETL の取得件数・保存件数・品質問題・エラーを集約できるように実装。
    - ETL の設計方針に基づく差分取得、バックフィル、品質チェック統合を想定（jquants_client / quality と連携する設計）。
    - パイプライン向けの定数（初回ロード開始日、カレンダー先読み、バックフィル日数等）を定義。
  - jquants_client・quality などの外部連携モジュールを利用する設計。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離の計算を実装（DuckDB SQL ベース、データ不足時の None ハンドリング）。
    - ボラティリティ/流動性（calc_volatility）: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）: raw_financials の最新財務データと価格を組合せて PER / ROE を算出。
    - 設計上、DuckDB のみを参照し外部 API にはアクセスしない安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（営業日）先までのリターンを一括クエリで計算。
    - IC 計算（calc_ic）: スピアマンのランク相関（ランクは平均ランク処理）を実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - ユーティリティ rank 関数を含む。外部ライブラリに依存せず純粋 Python + DuckDB 実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。
- 各モジュールで API 失敗時のフォールバック（例: macro_sentiment=0.0、スコア取得失敗時は該当銘柄をスキップ）や ROLLBACK の試行といった堅牢性向上の実装を含む。

### セキュリティ (Security)
- OpenAI や J-Quants、kabu API のキー・トークンは環境変数で管理する設計。必須変数未設定時は明示的に ValueError を発生させる（API キーが必要な処理での安全性担保）。

### 既知の設計注意点 / 動作仕様
- 全ての「日付に依存する」処理は datetime.today()/date.today() を直接参照せず、明示的な target_date 引数を受け取る設計（ルックアヘッドバイアス防止）。
- DuckDB を主要なローカルデータストアとして利用。executemany に空リストを与えると失敗するバージョンへの互換性考慮がある（空チェックを実施）。
- OpenAI 呼び出しは JSON Mode を利用。応答パースや不正 JSON に対する回復処理あり。
- market_calendar が未取得時は曜日ベースのフォールバックを使用するため、カレンダー更新ジョブで DB を保全することが推奨される。

---

今後のリリースでは、テストカバレッジ、ベンチマーク、運用向けのモニタリング・アラート機能、strategy/execution/monitoring の実装詳細についての変更を記録していく予定です。