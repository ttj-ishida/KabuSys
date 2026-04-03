CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。  
セマンティックバージョニングを採用しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース。日本株自動売買・データ基盤・リサーチ用の共通ライブラリを提供。
  - パッケージのエントリポイントとして kabusys を定義（__version__ = 0.1.0）。
  - 公開モジュール: data, research, ai, config などの基盤機能を含むモジュール構成。

- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local ファイルおよびOS環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 読み込みは既存 OS 環境変数を保護する仕組み（protected set）と override オプションを実装。
  - .env のパースは export 形式・クォート・エスケープ・インラインコメントを考慮。
  - 必須設定取得のヘルパー (_require) と Settings クラスを提供。
  - Settings による多数の設定プロパティ（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境判定等）。
  - 設定値検証: KABUSYS_ENV（development, paper_trading, live）、LOG_LEVEL（DEBUG〜CRITICAL）を検証して不正値は ValueError を送出。

- データ基盤（kabusys.data）
  - ETL パイプラインの結果を表す ETLResult 型（pipeline.ETLResult を公開）。
  - pipeline モジュール（差分取得・保存・品質チェックのためのユーティリティ）を実装。
    - 差分更新・バックフィル・品質チェックを考慮した設計。
    - ETL 実行結果のシリアライズ（to_dict）で品質問題を分かりやすく出力。
  - calendar_management：
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）。
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日）でフォールバックする堅牢な設計。
    - 最大探索日数、先読み・バックフィル日数、健全性チェックなどの制御定数を提供。

- AI（kabusys.ai）
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を取得。
    - バッチ（最大 _BATCH_SIZE=20 銘柄）単位で API 呼び出し、トークン膨張対策（記事数・文字数制限）を実装。
    - レート制限・ネットワーク断・5xx へのエクスポネンシャルバックオフとリトライロジック。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー/要素検証、数値変換、既知銘柄のみ採用）。
    - 成功したスコアのみ ai_scores テーブルへ置換的に保存（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - タイムウィンドウの計算は calc_news_window で行い、ルックアヘッドバイアスを防止（datetime.today/date.today を直接参照しない）。
  - regime_detector モジュール（score_regime）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事をキーワードフィルタで抽出し、OpenAI（gpt-4o-mini）に JSON 出力を要求して macro_sentiment を取得。
    - API 障害時はフェイルセーフとして macro_sentiment = 0.0 を使用、また冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 内部での DuckDB クエリはルックアヘッドを防ぐように設計。

- リサーチ機能（kabusys.research）
  - factor_research：
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（行数不足で None を返す等）や、営業日スキャン幅の設計が含まれる。
  - feature_exploration：
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度に取得、ホライズン検証（1〜252）やスキャン範囲の最適化を実装。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関を実装し、データ不足（有効レコード < 3）時は None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず、標準ライブラリのみで実装。

- 汎用設計・運用面の留意点
  - DuckDB を一次データベースとして想定（多くの関数は DuckDB 接続を受け取る設計）。
  - OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を利用することでパースの堅牢化を図る。
  - API 呼び出しには共通のリトライ・バックオフ・障害時のフォールバックを導入（LLM の不安定性に耐える設計）。
  - DB 書き込みは冪等性・部分失敗時のデータ保護を考慮（DELETE→INSERT の限定実行、executemany の空リスト回避など DuckDB 特性に適合）。
  - テスト可能性のため一部内部関数（例: _call_openai_api）を patch 可能にしている。
  - ルックアヘッドバイアス防止のため、すべての「日付基準」は明示的な target_date を使用し、date.today()/datetime.today() を直接参照しない実装方針を徹底。

Security
- .env の自動ロードは環境変数の保護（既存 OS 環境変数を protected set として扱う）を行い、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / 必須設定
- OpenAI API: OPENAI_API_KEY（または score_* 関数の api_key 引数）。
- J-Quants: JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token を使用）。
- kabu ステーション: KABU_API_PASSWORD（Settings.kabu_api_password を使用）。
- その他オプション設定（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値）は Settings でデフォルトを提供。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定すること（不正値は例外）。

Breaking Changes
- （初回リリースのため、過去バージョンとの互換性問題はなし）

Acknowledgements / Implementation remarks
- J-Quants や kabu ステーション向けクライアント（kabusys.data.jquants_client など）への依存を想定しており、実際の API 呼び出し部分は別モジュールで実装される想定。
- DuckDB のバージョン差異（executemany の空リストバインド挙動など）を考慮した互換性対策が施されている。

-- End of CHANGELOG --