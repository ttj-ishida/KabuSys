# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

なお、以下はソースコードから推測して作成した変更履歴（初期リリース向けの要約）です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ = 0.1.0 を設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト向け）。
  - .env 1行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 既存 OS 環境変数を保護する protected オプションを導入。
  - Settings クラスを追加し、環境変数経由でアプリ設定を取得するプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL の検証
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- データプラットフォーム関連 (src/kabusys/data/)
  - ETL 基盤:
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを格納）。
    - pipeline モジュールの公開インターフェースを提供（ETLResult の再エクスポート）。
    - 差分取得、バックフィル、品質チェック方針を実装（jquants_client 経由での保存・検査を想定）。
  - カレンダー管理:
    - JPX カレンダー管理モジュールを実装（market_calendar テーブルの扱い、夜間更新ジョブ）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル、健全性チェックを実装）。
    - market_calendar 未取得時の曜日ベースフォールバックを備え、一貫した振る舞いを担保。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）を計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB による SQL ベース計算で、prices_daily / raw_financials のみ参照する設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン可、デフォルト [1,5,21]）
    - IC（スピアマンランク相関）計算 calc_ic、rank（平均ランク処理）、factor_summary（基本統計量）を追加。
  - データ統合ユーティリティ:
    - zscore_normalize を kabusys.data.stats から公開（__init__ によるエクスポート）。

- AI / NLP モジュール (src/kabusys/ai/)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約して OpenAI チャット（gpt-4o-mini）へバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - time window（前日 15:00 JST ～ 当日 08:30 JST を UTC 換算）計算（calc_news_window）。
    - バッチ（最大 20 銘柄）・記事トリム（最大記事数/文字数）・JSON Mode を用いた応答検証。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで行う実装。
    - レスポンスの堅牢なパースとバリデーション（JSON 抽出、results 配列、code/score チェック、スコアのクリップ）。
    - テスト容易性のため _call_openai_api の差し替えを意識した実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - マクロキーワードフィルタ、LLM 呼び出し（gpt-4o-mini）、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - レジーム判定はスコアをクリップし閾値によりラベル化、DB へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- 監視・実行・その他
  - パッケージのモジュール公開（__all__）を整備（ai/news_nlp の score_news 等をエクスポート）。

### 変更 (Changed)
- 設計方針・品質配慮
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計を徹底（target_date を引数で渡す設計）。
  - DuckDB のバージョン固有の挙動（executemany の空リスト不可、リスト型バインド不安定等）を考慮した実装。
  - API 呼び出し周りを例外や不正レスポンスから守るフェイルセーフ設計（ログ記録して継続、致命的な部分のみ例外伝播）。

### 修正 (Fixed)
- エラー・ロバストネス向上
  - OpenAI / ネットワーク・API エラー時のリトライ戦略（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ）。
  - JSON パース失敗時に前後の余計なテキストを含むケースを復元してパースするロジックを追加（JSON 抽出）。
  - market_calendar の unknown/null 値に対する警告ログと曜日ベースのフォールバック対応を追加。
  - DB 書き込みで例外発生時に ROLLBACK を試行し、ROLLBACK 失敗時は警告を出す安全策を導入。

### セキュリティ (Security)
- シークレット管理に関する注意点を明示
  - OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN などの必須環境変数は Settings で必須扱いとし、未設定時は ValueError を発生させることで早期検出を容易にしている。

### 既知の注意点 / migration notes
- .env の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存するため、パッケージを配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を管理してください。
- DuckDB による executemany の空リストバインドがエラーになる点を考慮しているため、直接 SQL を変更する際は同動作を維持してください。
- OpenAI 呼び出しは gpt-4o-mini（モデル名定義）と JSON Mode を前提にしているため、モデルやレスポンス仕様を切り替える場合は _call_openai_api やレスポンスパース周辺の調整が必要です。
- ETL / calendar の夜間ジョブは J-Quants クライアント（jquants_client）へ依存するため、その API 仕様や認証情報を準備してください。

---

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・実際の変更差分を参照して更新してください。）