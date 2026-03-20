# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルではパッケージ kabusys の初期リリース（v0.1.0）で導入された主要な機能・設計方針・重要な実装をコードベースから推測して記載しています。

注: 日付は本ドキュメント作成日です。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを実装。

### Added
- パッケージ基礎
  - kabusys パッケージ（__version__ = 0.1.0）を導入。公開 API として data, strategy, execution, monitoring をエクスポート。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - OS 環境変数を保護する protected ロジック、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パース実装: export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱い等を考慮した堅牢なパーサ。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス等のプロパティと基本検証（必須チェック、env 値検証、デフォルト値）を追加。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装（不正値は ValueError を送出）。
- データ層 — J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。ページネーション対応の fetch_* 系関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レート制限用固定間隔スロットリング (_RateLimiter, デフォルト 120 req/min) を実装。
  - 再試行ロジック（指数バックオフ、最大リトライ回数、特定ステータスでのリトライ）を実装。429 時は Retry-After を尊重。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュを導入。
  - DuckDB への保存ヘルパー:
    - save_daily_quotes, save_financial_statements, save_market_calendar — 冪等性のため ON CONFLICT（UPDATE）を使用。
    - raw レコードのスキップ報告（PK 欠損など）と挿入件数のログ出力を実装。
  - データ変換ユーティリティ _to_float / _to_int を追加。
  - データ取得時に fetched_at を UTC ISO8601 で付与（Look-ahead バイアス回避のためのトレース性保持）。
- データ層 — ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基礎実装（デフォルトソースに Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去・スキーム/ホスト小文字化）と記事 ID のハッシュ化による冪等性。
  - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）、SSRF 対策（スキームの制限等を想定）を考慮。
  - DB バルク挿入（チャンク処理）と INSERT RETURNING による実際の挿入件数取得の方針（実装の一部は設計に明記）。
- リサーチ機能 (kabusys.research)
  - ファクター計算群を提供（research パッケージ経由でエクスポート）:
    - calc_momentum: モメンタム（1/3/6ヶ月相当）と MA200 乖離率（200行未満は None）
    - calc_volatility: ATR（20日）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials から最新の財務データを取得）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得する効率的実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算、サンプル不足時は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を返すユーティリティ。
    - rank: 同順位は平均ランクを採るランク化処理（浮動小数点丸め対策あり）。
  - DuckDB を前提に外部ライブラリに依存しない実装設計（pandas 等を使用しない）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research の生ファクターを統合・正規化して features テーブルへ upsert する一連処理を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）および ±3 でのクリップを実装。
  - DuckDB トランザクションを使った日付単位の置換（DELETE→INSERT）により冪等性・原子性を確保。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成して signals テーブルへ書き込む。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算およびデフォルト重みを実装。ユーザ指定 weights を検証・正規化・再スケール。
  - スコア変換ユーティリティ（シグモイド変換、欠損値補完は中立 0.5）を実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制、最小サンプル閾値あり）。
  - SELL 条件: ストップロス（終値比率 <= -8%）とスコア閾値未満のエグジットを実装。保有ポジションが features に無い場合の扱い（score=0 と見なす）や価格欠損時の判定スキップ等の安全策を導入。
  - signals テーブルへの日付単位置換（トランザクション）で冪等性を確保。
- ドキュメント的記述 / 設計ノート
  - 各モジュールに詳細な docstring と処理フロー・設計方針を明記（Look-ahead バイアス回避、発注層への非依存、堅牢性・冪等性の確保等）。

### Changed
- 初回リリースのため該当なし（設計/実装段階で示された方針・要件をそのまま実装）。

### Fixed
- 初回リリースのため該当なし（実装時に扱われている想定的なエッジケース: PK 欠損のスキップ、価格欠損時の SELL 判定スキップ、トランザクションのロールバック管理などを実装している）。

### Security
- ニュース収集で defusedxml を利用して XML パースの安全性を強化（XML Bomb 等の攻撃防止）。
- ニュース収集における URL 正規化とトラッキングパラメータ除去により、ID 生成の冪等性と不要なトラッキング除去を実現。
- ニュース受信サイズ上限（10MB）を設定してメモリ DoS を緩和する設計。
- J-Quants クライアントのトークン取り扱い（キャッシュ・自動リフレッシュ）とレート制限により、認証漏洩や API レート違反のリスクを低減。

### Internal / Performance
- 多くの計算が DuckDB 上でウィンドウ関数を活用した単一クエリで処理される設計（calc_momentum / calc_volatility / calc_forward_returns 等）。これにより I/O とメモリの効率化を図る。
- build_features / generate_signals は日付単位で削除→バルク挿入を行いトランザクションで原子性を担保。
- J-Quants API は固定間隔スロットリングとページネーションで安定した大量データ取得を想定。
- ニュース収集はバルクINSERTチャンク化で SQL への負荷を軽減。

### Removed
- 初回リリースのため該当なし。

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。追加の機能や修正が行われた場合は本ファイルを更新してください。