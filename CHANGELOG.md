# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### Added
- パッケージ基盤
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - public API のエクスポート: data, strategy, execution, monitoring

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメント処理。
  - .env の読み込みで OS 環境変数を保護するための protected 上書き制御を実装。
  - 設定ラッパー Settings を追加。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ保存。
    - タイムウィンドウ: JST 前日15:00〜当日08:30 を UTC に変換して利用。
    - バッチ処理、トークン肥大化対策（1銘柄あたり最大記事数・文字数トリム）。
    - JSON Mode を期待したレスポンスのバリデーションと復元処理（余計な前後テキストから最外の {} を抽出）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施、フェイルセーフ動作（失敗時は当該チャンクをスキップして継続）。
    - スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗を考慮して、対象コードのみ DELETE → INSERT（冪等処理）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
    - prices_daily と raw_news を用いたデータ取得（ルックアヘッドバイアス回避のため target_date 未満のデータのみ使用）。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
    - API エラー時のフォールバック（macro_sentiment = 0.0）や再試行ロジックを実装。
    - 結果保存はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを使った営業日判定ユーティリティ群を追加:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダー情報がない・未登録時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 最大探索日数で無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。

  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加（各処理の取得/保存件数、品質問題、エラーの収集）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映。
    - jquants_client と quality モジュールを組み合わせた ETL の基礎を提供。

  - etl モジュールに ETLResult を再エクスポート（kabusys.data.etl）

- リサーチツール (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - Value（PER・ROE）
    - DuckDB ベースで SQL とウィンドウ関数を用いた実装。データ不足時は None を返す。
  - feature_exploration:
    - calc_forward_returns（複数ホライズン対応）
    - calc_ic（Spearman ランク相関）
    - rank（同順位は平均ランク）
    - factor_summary（count/mean/std/min/max/median を計算）
  - zscore_normalize を data.stats からインポートして公開

### Changed
- 一貫した安全設計
  - 主要な解析/スコアリング関数（news_nlp.score_news / regime_detector.score_regime 等）は内部で datetime.today() / date.today() を参照せず、引数の target_date を明示的に使う設計（ルックアヘッドバイアス防止）。
  - DuckDB への一括書き込み前にパラメータが空でないことをチェック（DuckDB 0.10 の制約対応）。

- ロギングとエラーハンドリング
  - API 呼び出し失敗時に詳細な警告ログを出力し、フェイルセーフで継続する挙動を各所に採用。
  - ROLLBACK が失敗した際の警告ログを追加。

### Fixed
- 入力/出力の堅牢性向上
  - .env パーサのエスケープ/クォート/コメント処理を改善し、より現実的な .env ファイルに対応。
  - OpenAI レスポンスの JSON パースで、前後に余計なテキストが混ざった場合でも最外の JSON オブジェクトを復元して処理するロジックを追加（score_news / _validate_and_extract）。
  - APIError の status_code 存在性に依存しない扱い（getattr で安全に扱う、5xx 判定の互換性確保）。

### Security
- 環境変数の取り扱いに注意
  - 自動 .env ロード時に既存 OS 環境変数を保護する仕組みを導入（.env が意図せず OS 環境を上書きしない）。

注意:
- 本リリースはデータ取得・AI 呼び出しを含むため、実行には OpenAI API キーや J-Quants / kabu ステーション等の外部設定が必要です（Settings クラスを参照）。
- 本 CHANGELOG はコードベースからの推測に基づく初期リリースノートです。機能詳細や API の使用方法はソースコード内の docstring やドキュメントを参照してください。