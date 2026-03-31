# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマットの仕様: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。本バージョンで導入された主要機能・設計方針・注意点を以下にまとめます。

### 追加（Added）
- パッケージ骨格
  - kabusys パッケージの初期実装。トップレベル __version__ = 0.1.0。

- 環境設定管理（kabusys.config）
  - .env / .env.local または環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロードの挙動:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env を探索して読み込む。
    - 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数の上書きを防ぐため protected キー群を利用。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの判定はクォート無し且つ '#' の直前が空白或いはタブのときにのみ扱う。
  - 必須設定を取得する _require() を経由するプロパティ（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。
  - DB パス設定（duckdb/sqlite）のデフォルトと Path 展開処理を提供。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値の検証）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI (自然言語処理) モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集計し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄単位のセンチメント ai_score を生成して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を対象。
    - バッチサイズ、記事数・文字数トリム、JSON Mode + レスポンスバリデーション、リトライ（429/ネットワーク/タイムアウト/5xx）などを実装。
    - DuckDB への書込みは「取得済みコードのみを置換（DELETE → INSERT）」し、部分失敗時に他コードの既存データを保護。
    - API キーは引数で注入可能（テスト容易性）。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等的に書き込み。
    - マクロニュースは新聞タイトルからマクロキーワードでフィルタ（キーワードリストを実装）。
    - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計（呼び出し側で target_date を与える）。

- Data（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB に登録がある場合は DB の値を優先、未登録日は曜日ベースのフォールバック（週末非営業）で整合性を保つ。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得・バックフィルを行い market_calendar を冪等更新するジョブを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュールで差分更新、保存、品質チェックの設計に対応するユーティリティを実装（ETLResult に品質問題・エラー列挙を保持）。
    - テーブルの最大日付取得等のヘルパー関数を提供。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。返り値は (date, code) をキーとする dict のリスト。
    - 各指標の計算に関する SQL 実装（MA200 / ATR / 平均売買代金 / 出来高比など）を追加。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（Spearman のランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポートし、主要ファンクション群を __all__ で公開。

### 変更（Changed）
- （初版のため該当なし）本リリースは新規機能の導入が主体。

### 修正（Fixed）
- （初版のため該当なし）

### セキュリティ / フォールトトレランス上の実装ノート
- OpenAI API 呼び出しはリトライ・指数バックオフを実装。RateLimitError / APIConnectionError / APITimeoutError / 5xx はリトライ対象とするが、最終的に失敗した場合は例外を投げずフェイルセーフ値（例: 0.0）で継続する設計。
- OpenAI レスポンスの JSON パースは堅牢化（JSON Mode でも前後に余計なテキストが混ざる場合に最外側の {} を抽出して復元）。
- DB 書き込みは冪等性を考慮（DELETE→INSERT のパターン、トランザクション BEGIN/COMMIT/ROLLBACK）。
- DuckDB 特有の制約（executemany に空リストを渡せない等）に対するガードを実装。
- API キーは関数引数で注入可能にしてテストしやすくしている（テスト中に環境変数に依存しない）。

### 設計・実装ポリシー（ドキュメント化された重要事項）
- ルックアヘッドバイアス回避: 各スコアリング/ETL/調査関数は date.today()/datetime.today() を内部参照せず、必ず呼び出し側から target_date を受け取る。
- 部分失敗耐性: 外部 API 呼び出しの失敗や部分的な処理失敗時に他データを不必要に消さない（書込対象を限定する等）方針。
- テスト容易性: OpenAI 呼び出し箇所はモック差し替えを想定した実装（private 関数を直接パッチ可能）。

### 既知の注意点・移行メモ
- 環境変数名や必須キー:
  - OpenAI: OPENAI_API_KEY（score_news / score_regime で必須）
  - J-Quants: JQUANTS_REFRESH_TOKEN
  - kabuステーション: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
  - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB のバージョン差異により一部 SQL バインドの挙動（リストのバインド等）が異なるため、空パラメータ配列を渡さないようにガードしている。
- OpenAI モデルは現状 gpt-4o-mini を使う設定。将来的にモデル名を変更したい場合は該当モジュール内の定数を更新してください。

---

もしリリースノートに追加してほしい項目（例: 変更理由、より詳細な実装図、マイグレーション手順など）があれば教えてください。必要に応じてセクションを分割・展開して追記します。