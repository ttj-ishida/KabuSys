# Changelog

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-03-20

### Added
- 初版リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージエントリポイント:
    - kabusys.__version__ = 0.1.0
    - パブリックAPI: build_features, generate_signals などをエクスポート
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を提供（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env 行パーサ実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得用 Settings クラスを提供（必須キーの検証を含む）。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
  - 設定上のバリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）の検証。
- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント (data.jquants_client)
    - 固定間隔のレート制御（120 req/min）を行う RateLimiter を実装。
    - 冪等性を考慮した DuckDB への保存関数（ON CONFLICT DO UPDATE）を実装。
    - リトライ（指数バックオフ、最大3回）、401 の自動トークンリフレッシュ、429 の Retry-After 尊重等を実装。
    - fetch / save の操作: 株価日足、財務データ、マーケットカレンダーの取得・保存機能を提供。
    - 取得時の fetched_at を UTC (ISO8601) で記録し、Look-ahead bias のトレースを可能に。
  - ニュース収集モジュール (data.news_collector)
    - RSS からニュースを取得して raw_news などへ保存する処理骨格を実装。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）、記事ID を SHA-256 のハッシュで生成する方針を採用。
    - セキュリティ対策: defusedxml を使用、受信サイズ制限（10MB）、SSR Fリスク軽減のためスキームチェック等の方針。
- リサーチ用モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 営業日ベースのホライズン・ウィンドウ設計、欠損時の None 扱い。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（fwd 1/5/21 日）および IC（Spearman の ρ）計算、ファクター統計サマリー、rank ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - 共通ユーティリティ: zscore_normalize を再エクスポート。
- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (strategy.feature_engineering)
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムの Z スコア正規化、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保持）。
  - シグナル生成 (strategy.signal_generator)
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
    - コンポーネントの欠損は中立 0.5 で補完、最終スコアは加重和で計算（デフォルトの重みを持つ）。
    - Bear レジーム検知による BUY 抑制、STOP-LOSS（-8%）およびスコア低下による SELL 判定を実装。
    - weights の入力検証と正規化（合計が1に再スケール）、signals テーブルへの日付単位置換で冪等性保証。
- DuckDB とのトランザクション運用を多くの箇所で採用（features / signals の日付単位置換など）。
- ロギングと詳細な警告メッセージを各モジュールで導入（欠損データや不正入力の検出・通知）。

### Changed
- （初版のため過去からの変更なし）

### Fixed
- （初版のため無し）

### Security
- news_collector で defusedxml を使用、受信サイズ制限、トラッキングパラメータ削除、HTTP スキームチェック等の対策を導入。
- J-Quants クライアントで 401 自動リフレッシュ回数を制限し、無限再帰を防止。

### Notes / Implementation Decisions
- 多くの設計はルックアヘッドバイアス対策（取得時刻の明記、target_date 時点のデータのみ参照）を重視しています。
- research モジュールは本番／発注層へのアクセスを行わず、DuckDB の price/financial テーブルのみを参照する方針です。
- 依存を最小化する設計（研究モジュールは pandas 等に依存しない）を採用。
- 一部の未実装・今後検討項目（signal_generator のトレーリングストップや時間決済など）をコード中にコメントで明示。

---

今後のリリースでは、以下を想定しています:
- News パーシングの完全実装（記事ID生成・news_symbols 結合・DB保存処理の完成）
- execution（発注）層の実装と統合テスト
- 単体テスト、型チェック、CI 設定の追加
- パフォーマンス改善（DuckDB クエリ最適化、バルク処理の改善）

問題・要望・誤植・補足説明があればお知らせください。