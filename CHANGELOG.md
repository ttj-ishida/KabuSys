# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本リリースはソースコードから推測して作成した初期リリースの変更ログです。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys - 日本株自動売買システムの基本モジュール群を追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開（モジュール群のエントリポイント）。

- 環境設定・読み込み機能を追加（src/kabusys/config.py）。
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装。
  - 自動ロードの優先順位: OS環境 > .env.local > .env。
  - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能:
    - 空行・コメント行（#）や `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなしでのインラインコメント扱いのルールを実装。
  - 環境変数検証ユーティリティ `_require` と Settings クラスを提供。以下のプロパティを定義:
    - J-Quants: jquants_refresh_token
    - kabuステーション: kabu_api_password, kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
    - Slack: slack_bot_token, slack_channel_id
    - DB パス: duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env（development/paper_trading/live の検証）, log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ライブ/ペーパー/開発モード判定ヘルパー is_live / is_paper / is_dev

- AI ニュースセンチメント・機能を追加（src/kabusys/ai/*）。
  - ニュース NLP スコアリング: score_news（src/kabusys/ai/news_nlp.py）
    - タイムウィンドウ計算（JST基準 → UTC naive datetime で DB クエリ）。
    - raw_news と news_symbols を結合して銘柄別に記事を集約（記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）に対するバッチ送信（デフォルトで最大20銘柄/チャンク）。
    - レスポンスの堅牢なバリデーション: JSON 抽出、results 配列、code と score の検証、スコアの ±1.0 クリッピング。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（最大リトライ回数等は定数で制御）。
    - スコア結果は ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT を実行、部分失敗時に他銘柄を保護）。
    - テスト容易性: API 呼び出しは _call_openai_api をラップしており unittest.mock.patch による差し替えが容易。
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードによる raw_news タイトル抽出、OpenAI（gpt-4o-mini）への JSON 出力プロンプト、堅牢なエラーハンドリングと再試行を実装。
    - DB への冪等書き込み（market_regime テーブル）を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - AI モジュール初期公開（src/kabusys/ai/__init__.py）:
    - news_nlp の score_news を公開。

- データプラットフォーム関連モジュール（src/kabusys/data/*）を追加。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - market_calendar テーブルの有無や値の NULL を考慮したフォールバックロジック（登録データ優先、未登録日は曜日ベースで判定）。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等更新するバッチ処理を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスによる ETL 実行結果の構造化（取得/保存件数、品質問題、エラー一覧など）。
    - テーブル存在確認・最大日付取得などのユーティリティを提供。
    - etl モジュールから ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - 既存データクライアントとの連携想定（jquants_client, quality モジュール参照）。

- リサーチ・ファクター解析モジュールを追加（src/kabusys/research/*）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数群を実装。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials のみ参照。
    - 計算結果は (date, code) キーの dict リストで返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）。
    - rank ユーティリティ（同順位は平均ランクで処理）。
    - factor_summary による各ファクターの統計サマリー（count/mean/std/min/max/median）。
  - research パッケージの公開（src/kabusys/research/__init__.py）:
    - calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を公開。

- 実装全体の設計方針として以下を明示（モジュールドキュメンテーションより抽出）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照せず、対象日（target_date）ベースで処理。
  - OpenAI API 呼び出しは堅牢にエラーハンドリング（429/タイムアウト/5xx に対する指数バックオフ等）してフォールバック動作を定義（失敗時はスコア 0.0 やスキップで継続）。
  - DB への書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 等）、部分失敗時の既存データ保護を優先。
  - DuckDB の executemany における空リスト制約や日付型扱いなどの互換性対策を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは Settings で必須チェックを行うが、.env 自動ロード時に OS 環境変数の保護（protected set）を尊重する実装を追加。環境からの誤上書きを防止。

---

参照:
- 各モジュール内の docstring と関数定義をもとに CHANGELOG を作成しました。実際のリリースノート作成時には、テスト結果・既知の制限・互換性情報などを追記してください。