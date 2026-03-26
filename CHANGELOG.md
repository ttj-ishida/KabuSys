# CHANGELOG

すべての注目すべき変更履歴をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」形式に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__、__version__ = "0.1.0"）。
  - パブリック API の __all__ に data, strategy, execution, monitoring を公開。

- 設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込み。  
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - 高機能な .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 必須環境変数未設定時に ValueError を投げる _require ヘルパー。
  - 主要設定項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）をプロパティで提供。
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）とログレベルの検証。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルを集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄毎のセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、トークン肥大化対策（記事数と文字数上限）、レスポンス検証、スコア ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時はログ出力してスキップ（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch）。
    - DuckDB の executemany に関する互換性考慮（空リスト不可への対応）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタして LLM へ入力。記事なしの場合は LLM 呼出しをスキップして macro_sentiment=0.0。
    - API 呼び出しのリトライ、API エラー/パース失敗時は 0.0 にフォールバック（例外は投げない）。
    - レジーム判定処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。
    - OpenAI クライアント生成は引数の api_key または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError。

- データ（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB が未取得のときは曜日（平日）ベースのフォールバック。
    - calendar_update_job を実装（J-Quants API から差分取得→保存、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル期間、将来日付の健全性チェックなどの安全策を導入。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult dataclass を提供（ETL 実行メトリクス、品質問題、エラー収集）。
    - 差分取得・保存・品質チェック（quality モジュール）を想定した設計。J-Quants クライアント（jquants_client）との連携を想定。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデイ調整など。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials テーブルから計算。
    - データ不足時の None 戻し、結果は (date, code) ベースの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank ユーティリティ、ファクター統計サマリーを実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。
  - 研究ユーティリティの再エクスポート（zscore_normalize など）。

### Changed
- 初回リリースのため変更履歴はありません。

### Fixed
- 初回リリースのため修正履歴はありません。

### Security
- 初回リリースのため特記事項なし。

### Notes / ユーザー向け注意点
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティから要求される（未設定時は ValueError）。
  - OpenAI を使う関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY が必要（未設定時に ValueError）。
- .env 自動読み込みはパッケージ内からプロジェクトルートを探索して行われるため、配布後の動作やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効にできます。
- DuckDB 互換性: executemany に空リストを渡すとエラーになる既知の制約に対応する実装（空チェック）を行っています。
- LLM 呼び出しは外部 API に依存するため、運用時は API レート制限や課金に注意してください。API エラー時はフェイルセーフ（スコア 0.0 またはスキップ）で処理継続する設計です。
- すべての時刻/日付操作はルックアヘッドバイアスを避けるため直接の現在時刻参照を避け、引数の target_date に基づいて決定されます。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring 実装の追加
- テストカバレッジと CI の整備
- jquants_client の具体的実装とテスト用モックの提供

（このCHANGELOGはコードベースから推測して作成しています。実際のリリースノートに反映する際は必要に応じて調整してください。）