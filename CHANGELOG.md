# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴（リリースノート）です。

全般
- 形式: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)
- バージョン: パッケージ本体で定義された __version__ = "0.1.0" を初回リリースとしています。
- 日付: 2026-03-28（コード提示日をリリース日として記載）

Unreleased
- （現在はなし）

[0.1.0] - 2026-03-28
Added
- パッケージの初回リリース "KabuSys"（日本株自動売買システム）の基礎実装を追加。
  - パッケージ公開インターフェース: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]。

- 環境設定 / 設定管理
  - `kabusys.config`:
    - .env / .env.local からの自動読み込み機能（プロジェクトルートを .git / pyproject.toml から判定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサーは以下に対応:
      - `export KEY=val` 形式
      - シングル/ダブルクォート値（バックスラッシュエスケープ対応）
      - インラインコメント（クォート有無に応じた取り扱い）
    - 読み込みルール: OS 環境変数 > .env.local > .env（.env.local は上書き）
    - `Settings` クラスを提供（必須環境変数取得の _require、各種プロパティ、値検証を含む）
    - 必須変数の例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト DB パス: duckdb -> data/kabusys.duckdb、sqlite -> data/monitoring.db
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値セットを明示）

- データ基盤（DuckDB ベース）
  - `kabusys.data.pipeline` / `kabusys.data.etl`:
    - ETL 用の ETLResult 型（dataclass）を公開。ETL の取得数・保存数・品質問題・エラーの記録に対応。
    - 差分更新、backfill、品質チェックの設計方針を実装（jquants_client 経由の保存を想定）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - `kabusys.data.calendar_management`:
    - JPX（マーケット）カレンダーの管理ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存を想定（バックフィル・健全性チェック付き）。
    - DB 登録がない場合は曜日ベースのフォールバック（週末を非営業日とする）を行い、一貫性を保つ設計。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`:
    - ファクター計算: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum（1M/3M/6M リターン・200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR、流動性指標）を計算。
    - DuckDB 上の SQL とウィンドウ関数を活用した実装。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算 (calc_forward_returns)、IC（Information Coefficient）計算 (calc_ic)、ランク変換 (rank)、ファクター統計サマリ (factor_summary) を提供。
    - pandas 等の外部依存を持たず標準ライブラリで実装。
  - `kabusys.research.__init__` で研究関連ユーティリティを再エクスポート（zscore_normalize など）。

- AI/NLP モジュール（OpenAI 統合）
  - `kabusys.ai.news_nlp`:
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数制限（デフォルト: 10 件・3000 文字）。
    - JSON Mode を想定したレスポンス検証・パース（余計な前後テキストから JSON を抽出する補正を含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。非再試行エラーではスキップする安全設計。
    - スコアを ±1.0 にクリップ。部分失敗でも既存データを保護するため、書き込みは該当コードのみ DELETE → INSERT。
    - テスト容易性: OpenAI 呼び出しは内部関数を patch 可能に実装（モック用に差し替え可能）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を算出。
    - calc_news_window と組み合わせ、raw_news からマクロキーワードを抽出して LLM により macro_sentiment を取得（最大 20 記事）。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 として継続するフェイルセーフ設計。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK を試行して上位へ例外を伝播。

- ロギングと耐障害性
  - 各モジュールで詳細な logger 出力を追加（INFO/DEBUG/WARNING/EXCEPTION）。
  - API エラーやパース失敗、DB 書き込み失敗時の明示的なハンドリングとフォールバック（中立値やスキップ）を実装。
  - DuckDB の executemany が空リストを受け付けない挙動への対応（空であれば呼び出さない条件分岐）。

Changed
- 初回リリースのため「Changed」は無し（該当は初期追加事項のみ）。

Fixed
- DuckDB の互換性問題を考慮した実装を行い、以下を回避:
  - executemany に空リストを渡して失敗するケースを防止。
  - API レスポンスの不正 JSON（余計な前後テキスト混入）に対する復元ロジックを実装。

Security
- .env 読み込み時に OS 環境変数を保護するため protected キーセットを導入（override=False 時は既存の OS 環境変数を上書きしない）。
- 必須のシークレット（OpenAI API キー等）は Settings._require により未設定時に明確な ValueError を出す。

Notes / Known limitations
- OpenAI API キー (OPENAI_API_KEY) は環境変数か関数引数で明示的に渡す必要があります。未設定時は ValueError を送出。
- 使用モデルは gpt-4o-mini を前提（news_nlp / regime_detector ともに JSON Mode を利用）。
- DuckDB を内部ストレージとして利用する設計のため、DuckDB のバージョン依存挙動に注意（executemany 等）。
- 本実装はルックアヘッドバイアスを防ぐため、datetime.today() / date.today() を内部ロジックで直接参照しない設計方針を採用（ターゲット日を引数で渡す方式）。
- 外部 API（J-Quants、OpenAI、kabuステーション 等）呼び出しは I/O エラーや API 仕様変更に左右されるため、運用時は該当サービスの認証情報・レート制限を管理してください。
- 単体テストを容易にするため、OpenAI 呼び出し等をモック差し替え可能な実装になっています（内部 _call_openai_api の patch 等）。

Required environment variables（主要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（news_nlp / regime_detector を使用する場合）
- オプション: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD

今後の予定（想定）
- 監視 / 実行 / 戦略モジュールの具現化（strategy, execution, monitoring 以下の具体機能追加）。
- 単体テスト・統合テストの追加と CI パイプライン整備。
- テレメトリ・監査ログの強化、Slack 通知等の運用通知機能拡充。
- モデルの切替やプロンプト改善、レスポンス検証ルールの強化。

補足
- この CHANGELOG は提示されたソースコードから実装意図・設計方針をもとに作成した推測ベースの変更履歴です。実際のリリースノートとして使用する場合は、プロジェクトの公開履歴／コミットログに基づく追補・修正を推奨します。