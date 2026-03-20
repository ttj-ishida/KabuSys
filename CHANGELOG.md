# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

なお、この CHANGELOG はソースコードから推測して生成した初版リリースノートです（実装の意図や注記を元に記載）。

## [Unreleased]


## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン `0.1.0` と公開モジュール一覧を追加。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサを実装（コメント・export プレフィックス・クォート・エスケープ対応）。
  - 必須環境変数チェックユーティリティ `_require` と Settings クラスを提供。
    - 必須変数例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - データベースパスのデフォルト: `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`
    - 環境種別検証（development / paper_trading / live）とログレベル検証（DEBUG/INFO/...）。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx 再試行）、429 の Retry-After 考慮。
    - 401 受信時はリフレッシュトークンから ID トークンを自動更新して1回再試行。
    - フェッチ関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）: ページネーション対応。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - fetched_at を UTC ISO8601 で記録。
      - ON CONFLICT DO UPDATE により冪等保存。
  - 型変換ユーティリティ `_to_float` / `_to_int` を提供（安全な変換・欠損処理）。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news に保存する機能を実装。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - URL 正規化（小文字化・トラッキングパラメータ削除・パラメータソート・フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
    - defusedxml を使用して XML 攻撃を軽減。
    - 受信サイズ制限（デフォルト 10 MB）や HTTP スキームの検証で SSRF/DoS を抑止。
    - バルク INSERT のチャンク/トランザクション処理で効率化。
- 研究用モジュール (kabusys.research)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials ベース）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率。
    - Volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損なら None）、ROE の取得。
  - 特徴量探索: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計）、rank（同順位は平均ランク）。
  - 外部ライブラリに依存せず、DuckDB 接続のみを受け取る設計。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research から得た生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 にクリップ。
    - features テーブルへ日付単位の置換（トランザクション＋バルク挿入で冪等）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントはシグモイド変換・逆変換などにより 0〜1 に正規化。
    - デフォルト重みと閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD）を実装。カスタム weights を受け付け、検証・正規化して合計を 1.0 にリスケール。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）による BUY 抑止。
    - SELL 判定（ストップロス -8%、score 未満 など）を実装。保有ポジションの価格欠損時の警告と判定スキップ。
    - signals テーブルへ日付単位の置換（冪等）。
- strategy パッケージエクスポート
  - build_features と generate_signals を public API として公開。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector で defusedxml を採用し XML ベースの攻撃を軽減。
- URL 正規化・スキーム検証・受信サイズ制限により SSRF / メモリ DoS のリスクを低減。
- J-Quants クライアントでトークンの自動リフレッシュとリトライ制御を実装し、認証失敗や一時的障害からの回復力を向上。

### Notes / 注意事項
- 環境変数が必須な項目を未設定のまま実行すると ValueError を送出します。必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- DuckDB / SQLite のデフォルトパスは Settings で指定されていますが、本番運用では環境変数で明示的に設定することを推奨します。
- generate_signals の売買ロジックは戦略仕様書（StrategyModel.md）の一部を実装しています。トレーリングストップや時間決済（保有 60 営業日超等）は positions テーブルに追加情報（peak_price や entry_date）を保存することで拡張が可能です。
- research モジュールは外部依存を持たないため、分析用途で単体利用できます。
- news_collector の記事 ID は URL ベースで生成するため、同一の記事が URL パラメータの差で複数保存されることを防止します。ただし完全な重複検出には追加のルールが必要な場合があります。

---

今後のリリースでは、実行（execution）層の発注連携、監視（monitoring）機能の実装、さらにテストおよびドキュメントの拡充を予定しています。