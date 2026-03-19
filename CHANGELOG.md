# Changelog

すべての注目すべき変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを導入。公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - バージョン番号を `__version__ = "0.1.0"` で管理。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ の親ディレクトリを辿り .git または pyproject.toml を基準に検出（CWD に依存しない）。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（コメント行・export プレフィックス・クォートとエスケープ・インラインコメント処理などに対応）。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等をプロパティとして提供。
  - 必須環境変数が未設定の場合は _require が ValueError を送出することで早期検出。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 発生時は ID トークンを自動リフレッシュして 1 回リトライ（再帰を防ぐフラグ付）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT / DO UPDATE を利用して重複を排除。
    - 数値変換ユーティリティ (_to_float, _to_int) を追加して不正データに耐性を持たせる。
    - 取得時刻を UTC ISO8601（Z）で記録し、Look-ahead バイアスの追跡を容易に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存するモジュールを実装。
    - デフォルト RSS ソース（Yahoo Finance Business）。
    - 受信サイズ上限（10MB）、XML パースに defusedxml を使用して安全性を確保。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を用いることで冪等性を担保。
    - URL 正規化処理を実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - SSRF/不正スキーム対策やトラッキングパラメータ除去、バルク INSERT のチャンク処理などパフォーマンスと安全性の配慮。

- 研究用ファクター計算 (src/kabusys/research/factor_research.py)
  - モメンタム・ボラティリティ・バリュー系ファクター計算を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日ウィンドウ存在チェック）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（true_range の NULL 伝播を制御して正確に集計）。
    - calc_value: 最新財務データ（raw_financials）と当日株価を結合して per / roe を算出（EPS が 0 の場合は None）。
  - DuckDB のウィンドウ関数 / SQL を活用した実装で、prices_daily / raw_financials のみを参照。

- 研究用探索ツール (src/kabusys/research/feature_exploration.py)
  - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズン検証、1 クエリ取得）実装。
  - calc_ic: スピアマンランク相関（IC）を実装。欠損やサンプル不足（<3）を考慮して None を返す。
  - rank / factor_summary: ランク変換（同順位は平均ランク）と各ファクターの基本統計量（count/mean/std/min/max/median）を実装。
  - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装。
    - research の calc_* 関数から生ファクターを取得、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - 指定数カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへの日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクション利用）。
    - 価格欠損・非有限値を適切にハンドル。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features と ai_scores を統合し、component スコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントにシグモイド変換・補完ロジック（欠損は中立 0.5）を適用して final_score を算出。既定重みは (momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10)。
    - ユーザ提供の weights を検証・補完・正規化（負値/NaN/Inf/不正キーは無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）では BUY シグナルを抑制。
    - BUY は final_score >= threshold の銘柄、SELL はストップロス（-8%）やスコア低下（final_score < threshold）で生成。
    - SELL 優先ポリシーにより SELL 対象は BUY から除外。signals テーブルへ日付単位置換で冪等保存（トランザクション利用）。
    - positions / prices_daily の結合でエグジット判定を行い、価格欠損時は SELL 判定をスキップして誤クローズを防止。

- 研究パッケージ公開 (src/kabusys/research/__init__.py)
  - 主要な関数群（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）をエクスポート。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限 / TODO
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で現状未実装として明記。
- news_collector の RSS フェッチ処理本体（HTTP GET / XML ループや DB への具体的挿入処理の続き）はファイル末尾で途中（正規化関数の実装）となっているため、実装の継続が必要な箇所がある可能性がある（コードベース全体の完成度はこのリリース時点の実装状況に依存）。

---

（注）上記はソースコードの内容から推測して作成した変更履歴です。実際のリリースノート作成時はコミット履歴・PR 説明・担当者の意図を確認して最終調整してください。