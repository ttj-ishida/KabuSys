# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

現在のバージョン: 0.1.0 — 2026-03-20

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下に主要な追加点・設計上の注意点をまとめます。

### 追加 (Added)
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を探索）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト用途）。
  - .env 行パーサーを実装:
    - コメント、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理をサポート。
  - 環境変数保護（protected keys）を導入し OS 環境変数を .env で上書きしないように制御。
  - `Settings` クラスを提供し、J-Quants/J-Quants リフレッシュトークン、kabu API、Slack、データベースパス（DuckDB/SQLite）、ログレベル・環境種別の取得とバリデーションを行う。

- データ取得・保存 (`kabusys.data`)
  - J-Quants API クライアントを実装（`kabusys.data.jquants_client`）:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ（1 回のみ）。
    - ページネーション対応のフェッチ関数 (`fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`)。
    - DuckDB への冪等保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装。ON CONFLICT を用いて重複を回避。
    - 型変換ユーティリティ `_to_float`, `_to_int` を提供（不正な値は None）。
  - ニュース収集モジュール (`kabusys.data.news_collector`) を実装:
    - RSS フィードから記事を収集し raw_news に保存する処理を実装（デフォルトソース: Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、断片削除、クエリソート）と記事 ID を SHA-256 で生成して冪等性を確保。
    - defusedxml を用いた XML の安全パース、受信サイズ上限（10 MB）、SSRF 回避の考慮、チャンク化インサートを実装。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算群を実装（`factor_research`）:
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離）、Volatility（20 日 ATR、相対 ATR、出来高比率、20 日平均売買代金）、Value（PER、ROE）を DuckDB 上の prices_daily / raw_financials から計算。
  - 特徴量探索・統計 (`feature_exploration`) を実装:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21] 営業日）。
    - Spearman ランク相関（IC）計算（ties は平均ランクで処理）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）。
    - ランク付けユーティリティ `rank` を提供（丸めにより浮動小数誤差の ties 検出漏れを防止）。
  - `kabusys.research.__init__` で主要 API を再エクスポート。

- 戦略モジュール (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`) を実装:
    - research 側で算出された生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE + bulk INSERT）により冪等性・原子性を保証。
  - シグナル生成 (`signal_generator.generate_signals`) を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き合算（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、ユーザー重みは検証・正規化後に適用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合）により BUY を抑制。
    - BUY シグナル閾値デフォルト 0.60。SELL（エグジット）条件としてストップロス（-8%）とスコア低下を実装。
    - features が空でも SELL 判定は実行し、保有銘柄の価格欠損・features 欠落に対する安全措置（ログ出力・欠落時スコア 0.0 または中立補完）を導入。
    - signals テーブルへ日付単位での置換（トランザクション + bulk INSERT）で冪等性・原子性を保証。
  - `kabusys.strategy.__init__` で主要 API を再エクスポート。

### 変更 (Changed)
- なし（初回リリースのため既存からの差分なし）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意点 / 設計上の制約
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）が事前に存在することを前提としています。マイグレーション・DDL は本リリースには含まれていません。
- ニュース収集は RSS のパースや外部 HTTP に依存するため、環境に応じたネットワーク制限やタイムアウト設定に注意してください。
- J-Quants クライアントは API レート・認証トークン管理を行いますが、実際の運用では refresh token（JQUANTS_REFRESH_TOKEN）を安全に管理してください。
- `Settings.env` と `Settings.log_level` は限定された値のみを受け入れ、無効な値は ValueError を送出します。
- 一部の戦略ロジック（例: トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price, entry_date 等）が必要であり現時点では未実装です（signal_generator 内に TODO 記載）。

### セキュリティ (Security)
- RSS XML のパースに defusedxml を使用し、XML Bomb 等の攻撃を防止。
- ニュース収集時に URL 正規化・トラッキング除去・スキーム検証を行い、SSRF・トラッキング情報漏洩のリスクを低減。
- J-Quants API 呼び出し時のタイムアウトやリトライポリシーを設定し、過負荷やハングの影響を緩和。

---

今後の予定（例）
- positions に peak_price / entry_date を追加してトレーリングストップ・時間決済を実装
- ユニットテスト・エンドツーエンドテストの充実
- ストラテジー重みの学習・自動最適化機能の追加

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成した初期リリース向けの要約です。実際のリリースノート作成時はリリース日・変更者情報・関連チケット等を追記してください。