# Changelog

すべての注目すべき変更はここに記載します。  
このプロジェクトは Keep a Changelog の慣例に従い、後方互換性のある変更、機能追加、修正等を整理しています。

現在のバージョンはパッケージ内の設定に従い 0.1.0 です。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-09

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加。__version__ = "0.1.0"、トップレベルで data/strategy/execution/monitoring を公開予定のモジュールとして列挙。
- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env のパース機能を実装（export 形式対応、シングル/ダブルクォート内のエスケープ対応、コメントルール等）。
  - 環境変数取得ヘルパー _require と Settings クラスを提供。設定項目（J-Quants、kabu API、LINE、DB パス、Paper Trading 関連、監視閾値、システム設定 等）をプロパティで公開。
  - 各種バリデーション：
    - PAPER_FILL_MODE の有効値チェック（instant / partial / never / reject）。
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）。
    - LOG_LEVEL の有効値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - デフォルト値を設定（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID/KILL フラグパス など）。
- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュールを実装（score_news）。
    - raw_news / news_symbols テーブルを集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - バッチサイズ、記事数上限、文字数トリム、429/ネットワーク/タイムアウト/5xx のリトライ（指数バックオフ）などの堅牢化を実装。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時でも他銘柄の既存スコアを保護する（対象コードのみ DELETE → INSERT）設計。
    - テストで差し替え可能な _call_openai_api フックを用意。
  - regime_detector モジュールを実装（score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込み。
    - マクロセンチメントは OpenAI（gpt-4o-mini）により JSON 出力で取得。API 失敗時はフェイルセーフで macro_sentiment = 0.0。
    - MA 計算はルックアヘッドバイアスを防ぐため target_date 未満のデータのみを使用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK）を実装。
- データ処理・ETL（kabusys.data）
  - calendar_management モジュールを追加（JPX カレンダー管理）。
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データがない場合の曜日ベースフォールバック、最大探索範囲の保護、夜間バッチ更新 job（calendar_update_job）を実装。
    - J-Quants クライアント経由で差分取得・バックフィル・保存を行う仕組み。
  - ETL パイプライン（kabusys.data.pipeline）と ETLResult データクラスを追加。
    - 差分更新・保存・品質チェック（quality モジュール）を想定した ETLResult を定義（target_date、取得/保存件数、quality_issues、errors 等）。
    - ETLResult.to_dict により品質問題を辞書化可能。
  - etl モジュールで pipeline.ETLResult を再エクスポート。
  - pipeline モジュールは J-Quants からの差分取得、バックフィル、品質チェック方針を明記。
- 研究（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、当日出来高比率。
    - Value: raw_financials から EPS/ROE を参照して PER/ROE を算出（PBR/配当利回りは未実装）。
    - すべて DuckDB の SQL を主体に実装し、外部 API に依存しない設計。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary を実装。
    - 将来リターンの一括取得、Spearman（ランク）による IC 計算、統計サマリーやランク化ユーティリティを提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から利用）。
- ロギング・堅牢性
  - 各モジュールで詳細なログ出力を追加（info/debug/warning/exception）。
  - API 呼び出しでのリトライ戦略やフェイルセーフ（例: macro_sentiment=0、スコア取得失敗時はスキップ）を採用。
  - DuckDB の executemany に関する互換性考慮（空パラメータの回避）を実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Breaking Changes)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能（api_key 引数）で、環境変数 OPENAI_API_KEY に依存しないテスト容易性を確保。

### 注意事項 / 設計上の重要点
- ルックアヘッドバイアス防止のため、どの AI/研究処理も内部で datetime.today() / date.today() を参照せず、必ず引数 target_date を基準に処理を行います。
- OpenAI 呼び出しは JSON Mode を期待し、レスポンスパースやバリデーションに注意を払っています。レスポンス形式の変化や API 仕様変更に対しては警告ログを出し、安全にフォールバックします。
- .env パーサは一般的な shell 形式に合わせて頑健に実装していますが、複雑なシェル式（コマンド置換など）はサポートしていません。
- 一部モジュール（strategy, execution, monitoring）は __all__ に記載されていますが、今回のリリースでは実装が含まれていない箇所があるため注意してください（将来的な追加予定）。

---

今後のリリースでは、strategy（売買ロジック）、execution（発注ロジック）、monitoring（運用監視）モジュールの追加や、既存機能のテストケース拡充、外部 API クライアントの抽象化などを予定しています。質問や追加で CHANGELOG に盛り込みたい項目があれば教えてください。