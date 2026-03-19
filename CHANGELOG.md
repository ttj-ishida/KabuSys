CHANGELOG
=========
すべての注目すべき変更を時系列で記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]
------------

- （現在のリリースノートは初回リリース 0.1.0 にまとめられています。将来的な変更はこのセクションに記載します。）

[0.1.0] - 2026-03-19
--------------------

概要
  - 日本株自動売買システム「KabuSys」の初回公開リリース。
  - データ収集（J-Quants, RSS）、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、設定管理などのコア機能を実装。
  - DuckDB をデータストアとして想定した冪等なデータ保存／バルク処理の設計。

追加 (Added)
  - パッケージ基盤
    - kabusys パッケージの初期構成を追加。__version__ = "0.1.0"。
    - サブモジュール公開: data, strategy, execution, monitoring（execution は初期空ファイルを含む）。

  - 設定 / 環境変数管理 (kabusys.config)
    - .env / .env.local の自動読み込み機能を提供（プロジェクトルートを .git または pyproject.toml から検出）。
    - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 強化された .env パーサ:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
      - インラインコメント判定の改善（クォート有無での扱い分離）。
    - Settings クラスを実装し型付けされたプロパティで設定値を公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - env / log_level の値検証（許容値の列挙）と is_live / is_paper / is_dev ヘルパー。

  - データ収集クライアント (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
      - 再試行（最大 3 回）＋指数バックオフ、HTTP 408/429/5xx を対象とするリトライロジック。
      - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ。
      - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を意識し ON CONFLICT 文で upsert を実施。
      - 取得時刻は UTC で記録（fetched_at）し、ルックアヘッドバイアスに配慮。

  - ニュース収集 (kabusys.data.news_collector)
    - RSS からの記事収集と raw_news への冪等保存の骨格を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成する方針（冪等性）。
    - defusedxml を用いて XML 攻撃を防御。
    - URL のトラッキングパラメータ除去、スキーム検証、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）などセキュリティ対策。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE=1000）による性能配慮。

  - 研究モジュール (kabusys.research)
    - ファクター計算 (kabusys.research.factor_research)
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER, ROE）などの定量ファクターを実装。
      - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ／移動平均を算出。
      - 入力データ不足時に None を返すなど堅牢な欠損処理。
    - 特徴量探索 (kabusys.research.feature_exploration)
      - 将来リターン算出（calc_forward_returns: 任意ホライズンの fwd_xd を一度のクエリで取得）。
      - IC（Spearman の ρ）計算（calc_ic）およびランク関数（rank）。
      - factor_summary による基礎統計量（count/mean/std/min/max/median）。
      - 外部依存を使わず標準ライブラリ／DuckDB のみで実装する設計方針。

  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research 層の生ファクターを統合・正規化し features テーブルへ UPSERT する build_features を実装。
    - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
    - Z スコア正規化後 ±3 でクリップ（外れ値対策）。
    - 日付単位の置換（DELETE→INSERT）をトランザクションで行い原子性を確保。

  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を個別に計算するユーティリティを実装（シグモイド変換、平均補完ルール等）。
    - AI レジームスコアの集計により Bear 相場を判定し、Bear 時は BUY シグナルを抑制する挙動を実装。
    - エグジット判定（ストップロス、スコア低下）を実装。保有ポジションに対する SELL シグナル生成は positions / prices_daily を参照。
    - 重み（weights）の入力バリデーション・合計リスケーリング、ランク付け、SELL 優先ポリシー、日付単位置換をトランザクションで実施。

変更 (Changed)
  - 実装責務の分離:
    - strategy 層は発注 / execution 層への依存を持たない設計（シグナルを signals テーブルに書き出すのみ）。
    - research / data 層は本番発注系へアクセスしないことを明示。

修正 (Fixed)
  - .env パーサの堅牢化:
    - 引用符内のバックスラッシュエスケープ処理と閉じクォート検出を追加し、複雑な .env 行の誤パースを防止。
    - コメント認識の条件を改善（クォート内は無視、非クォート時は '#' の前に空白がある場合のみコメントとして扱う等）。

セキュリティ (Security)
  - RSS パースに defusedxml を使用して XML Bomb 等の攻撃を軽減。
  - ニュース URL のスキーム検査とトラッキング除去で SSRF や追跡パラメータの混入を抑止。
  - J-Quants クライアントは認証トークンの自動更新機構を実装し、無限再帰を防ぐため allow_refresh フラグを導入。

パフォーマンス (Performance)
  - API 呼び出しのスロットリング（_RateLimiter）とページネーション対応により API レート制限を遵守。
  - DuckDB へは executemany によるバルク挿入とトランザクション、チャンク分割を使用し I/O オーバーヘッドを低減。

既知の制限 / TODO
  - シグナル生成の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
  - data.stats の zscore_normalize 実装は別モジュール（kabusys.data.stats）に依存しているため、それが適切に提供されることが前提。
  - monitoring / execution 層の実装は今後追加予定（現状は signals へ出力するのみ）。
  - DuckDB のスキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals 等）は事前に用意する必要あり。スキーマ移行スクリプトは含まれていない。

互換性に関する注意 (Breaking Changes)
  - 初回リリースのため過去バージョンとの互換性問題はありません。ただし将来的に settings の環境変数名や DB スキーマを変更する際は注意が必要です。

移行/導入メモ (Migration / Setup)
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意・デフォルト:
    - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを持つ）
  - .env ファイルはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）で自動読み込みされます。.env.local は .env を上書き可能。

謝辞 / 表記
  - 本リリースでは主要なデータ収集・研究・シグナル生成パイプラインの基盤を提供しています。実運用にあたっては DB スキーマ・テスト・監視・execution 層の実装を追加してください。