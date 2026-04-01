# CHANGELOG

すべての変更は Keep a Changelog 仕様に準拠して記載しています。  
この CHANGELOG はコードベース（初期リリース相当）の内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点と挙動は以下の通りです。

### 追加 (Added)
- パッケージの基本構成
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。公開サブパッケージとして data, research, ai, などを想定した名前空間を用意。

- 環境設定管理 (kabusys.config)
  - .env ファイルと OS 環境変数を統合して読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探して決定するため、CWD に依存しない自動読み込みを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
    - .env の読み込みで保護された OS 環境変数は上書きされない（protected 機能）。
  - .env パースの強化（コメント、export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - Settings クラスを実装し、使用可能な設定値をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（利用時に参照）
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 監視・閾値: PID_FILE_PATH、CPU_THRESHOLD_PCT、MEMORY_THRESHOLD_PCT、DISK_THRESHOLD_PCT
    - 環境モードとログレベル検証: KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は標準レベルに制約
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集計し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - 入力テキスト/トークン膨張対策: 1銘柄あたりの記事数と文字数上限を導入（デフォルト: 最大10記事、最大3000文字）。
    - バッチサイズ: 1回の API コールで最大20銘柄。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスの検証・サニタイズ処理あり（前後の余分なテキストから JSON を抽出する復元処理など）。
    - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対する指数バックオフ。その他のエラーはスキップして継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。処理後に ai_scores テーブルへ冪等的に書き込み（該当コードのみ DELETE→INSERT）。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計。target_date ベースのウィンドウ計算を明示。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）。
    - マクロニュースの抽出用キーワード群を定義し、最大20記事までを LLM に渡す。
    - OpenAI 呼び出しは独立実装で、news_nlp とは内部実装を共有しない（モジュール結合の低減）。
    - API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 計算結果は market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK 実行を試みて例外を伝播。

- データ基盤・ETL (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定・次/前営業日の取得・期間内営業日の列挙・SQ日判定を実装。
    - DB にデータがない場合は曜日ベース（平日を営業日扱い）でフォールバックする堅牢な設計。
    - calendar_update_job を実装し、J-Quants API からの差分フェッチと冪等保存（ON CONFLICT 想定）を行う。直近バックフィル・健全性チェック等を備える。
  - ETL パイプライン (pipeline, ETLResult)
    - ETL 実行結果を表す ETLResult データクラスを追加（品質チェック結果や各種取得・保存件数、エラー集約を含む）。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（jquants_client と quality モジュールを呼び出す想定）。
    - テーブル存在チェックや最大日付取得などのユーティリティを実装。
  - jquants_client を介した外部データ取得の抽象（モジュール参照箇所は存在）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR(20)、出来高/売買代金の流動性指標、PER / ROE の取得と計算を DuckDB 上の SQL + Python ロジックで実装。
    - データ不足時は None を返す等、堅牢性を確保。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（複数ホライズン対応、horizons 引数でカスタマイズ、入力検証あり）
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存しない純粋標準ライブラリ実装。

- DuckDB 利用方針
  - 内部は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL を主体に処理。DB 書き込みは冪等性を考慮（DELETE→INSERT や ON CONFLICT を想定）して行う。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込み時のエラーハンドリングを強化（ファイルオープン失敗時に warnings.warn、解析エラーはスキップ）。
- OpenAI 呼び出しにおける例外分類とリトライ条件を明確化（429/ネットワーク/タイムアウト/5xx をリトライ、それ以外はログ出力してフォールバック）。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- API キーやシークレットは環境変数経由で取得。必須 env（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings プロパティで未設定時に ValueError を投げるため、ランタイム前に適切に設定する必要があります。
- .env 自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

注意事項（マイグレーション / 利用時のヒント）
- OpenAI を使う API 呼び出し機能 (news_nlp, regime_detector) を利用するには OPENAI_API_KEY を環境変数に設定するか、各関数に api_key を明示的に渡してください。未設定時は ValueError が発生します。
- DuckDB のスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等）は本 CHANGELOG のコードに基づく前提です。初回導入時は対応するテーブル作成が必要です。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml が親ディレクトリに存在すること）。環境により意図せず読み込まれる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- news_nlp と regime_detector は外部 OpenAI API のレスポンスに依存するため、API のレート制限やレスポンス仕様変更に対しては運用上の注意が必要です（ロギングとフェイルセーフが組み込まれていますが、動作確認を推奨します）。

（この CHANGELOG はコード内の実装と docstring・コメントを基に自動的に推測して作成しています。実際のリリースや運用ポリシーはプロジェクトの実際の仕様に合わせて調整してください。）