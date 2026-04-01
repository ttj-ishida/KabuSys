# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

現行バージョン: 0.1.0

未リリースの変更はありません。

---

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。主な追加点、設計方針、注意点を以下にまとめます。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージ定義とバージョンを追加（__version__ = "0.1.0"）。
  - エクスポート対象: data, strategy, execution, monitoring（モジュール群の骨組みを提供）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順制御（OS 環境変数保護、override フラグ対応）。
    - 複雑な .env 行パーサを実装（export プレフィックス、クォート内エスケープ、インラインコメントの適切な扱い）。
    - 必須設定取得用 _require と Settings クラスを提供（J-Quants / kabuステーション / Slack / DB / 監視設定 / システム設定）。
    - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 設定値バリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）および利便性プロパティ（is_live 等）。

- AI ニュース解析・市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/コール）・記事トリム（最大記事数/最大文字数）・JSON レスポンスバリデーションを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ、失敗時は部分スキップして他銘柄を保護するフェイルセーフ設計。
    - DuckDB の executemany の互換性を考慮した実装（空リストバインド回避）。
    - API キー注入可能（api_key 引数）でテスト容易性を確保。
    - calc_news_window ユーティリティを公開。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次判定して market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出、OpenAI 呼び出し（JSON パース）、リトライ・バックオフ、API 失敗フォールバック（macro_sentiment=0.0）を実装。
    - レジーム計算はルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - OpenAI クライアント呼び出しはモジュール内で独立実装（テストしやすく、モジュール結合を避ける）。

- 研究用ファクター・特徴量探索
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベース処理で prices_daily / raw_financials を参照。
    - データ不足時には None を返す等の堅牢な挙動。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman の ρ）計算、ランク関数、ファクター統計サマリーを実装。
    - 外部依存を持たない純 Python 実装で研究用途に特化。
  - src/kabusys/research/__init__.py で主要 API を公開。

- データ基盤・ETL・カレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）を扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間更新ジョブ（calendar_update_job）を実装。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィルと健全性チェック等の保護ロジックを追加。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプライン骨子（差分取得、保存、品質チェック）を実装。
    - ETLResult dataclass を実装して ETL の監査ログや呼び出し元への結果伝達を容易に。
    - jquants_client（jq モジュール）との連携を想定した差分取得 + 保存処理。
    - 品質チェックモジュール quality との連携用の設計（品質問題は収集して呼び出し元で判断する方式）。
  - DuckDB 関連の互換性・安全対策（テーブル存在チェック、日付変換ユーティリティ、executemany の空リスト回避など）を多数実装。

### 改善・設計上の決定
- ルックアヘッドバイアス回避
  - AI スコアリング / レジーム判定 / ファクター計算 いずれも internal 時刻参照（datetime.today() / date.today()）に依存しない実装。全て target_date を明示的に受け取り、データ選択で未来データを排除。
- フォールバックとフェイルセーフ
  - OpenAI API 呼び出し失敗や不正レスポンス時は例外を上位に投げるのではなく、ログ記録および安全なデフォルト値（0.0 等）へフォールバックして処理継続する設計を採用。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）かつ例外時はROLLBACK を試行。
- テスト容易性
  - OpenAI 呼び出し箇所は内部関数 _call_openai_api を用い、unittest.mock.patch による差し替えが可能。
  - API キーは api_key 引数で注入可能（テストやキー管理に柔軟性）。
- 外部依存の最小化
  - 研究モジュールは pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

### 既知の注意点（Breaking changes 相当ではないが使用時の重要事項）
- 必須の環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須扱い（未設定時は ValueError）。
  - OpenAI 機能を利用するには OPENAI_API_KEY（あるいは各関数の api_key 引数）の設定が必要。
- 自動 .env ロード
  - パッケージインポート時にプロジェクトルートを探索して .env / .env.local を自動ロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB バインドの互換性
  - 一部実装で executemany の空パラメータを避ける処理を入れています（DuckDB 0.10 等との互換性を考慮）。
- JSON レスポンス処理
  - OpenAI の JSON Mode を前提にしていますが、余分な前後テキストが混入する場合に備えた復元ロジックを入れてあります（最外側の {} を抽出してパースする等）。

### 修正（実装上のバグ対応・保護）
- 各所でのエラー処理強化（API エラー、JSON パースエラー、DB 書き込み失敗時の ROLLBACK の試行、ログ出力による原因追跡の容易化）。
- .env パーサの堅牢化（export キーワード、クォート内のバックスラッシュエスケープ、コメント処理）により実運用での誤読を低減。

### セキュリティ
- 環境変数で扱うシークレットを os.environ に保護（既存 OS 環境変数はデフォルトで上書き防止、.env.local による上書きは明示的）。

---

今後の予定（ロードマップ、例）
- strategy / execution / monitoring モジュールの詳細実装（発注ロジック、監視・アラート）。
- ETL の詳細品質チェック実装と監査ログ強化。
- モデル評価・バックテスト用ユーティリティの追加。
- ユニット / 統合テストの拡充（CI ワークフロー）。

ご要望や不明点があれば、どの部分を CHANGELOG に詳述するか指定してください。