# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0 — 2026-03-21

## [0.1.0] - 2026-03-21

### 追加 (Added)
- パッケージ初期リリース: kabusys (src/kabusys)
  - __version__ = 0.1.0 を設定し、パッケージ公開の基礎を実装。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装（単一行パース、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供。
    - 必須設定が未設定の場合は ValueError を発生させる _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - duckdb/sqlite のデフォルトパス設定（expanduser 対応）。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API レート制御（120 req/min を固定間隔スロットリングで遵守）を実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大試行回数、HTTP 429/408/5xx の再試行）を実装。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュを実装（ページネーション間で共有）。
  - JSON リクエスト/レスポンスの統一処理、ページネーション対応の fetch_... 関数（daily_quotes / financial_statements / market_calendar）。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes: raw_prices への ON CONFLICT DO UPDATE（fetched_at を記録）。
    - save_financial_statements: raw_financials への冪等保存（PK チェック・fetched_at 記録）。
    - save_market_calendar: market_calendar への冪等保存（取引日 / 半日 / SQ 判定を boolean で格納）。
  - データ型変換ユーティリティ (_to_float / _to_int) を実装し不正な値を安全に処理。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集フローを実装（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルト追加）。
  - XML パースに defusedxml を使用して XML-related 攻撃を防止。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
  - URL 正規化ロジックを実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリキーソート）。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭で生成し冪等性確保。
  - SSRF 対策（HTTP/HTTPS 以外拒否など）を想定した実装方針（注記）。
  - DB 保存はバルクとトランザクションで行う設計（INSERT RETURNING 想定、チャンク処理のため _INSERT_CHUNK_SIZE を使用）。

- 研究・ファクター計算 (src/kabusys/research/*.py, src/kabusys/research/__init__.py)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（DuckDB SQL ベース）。200 日移動平均に必要な行数チェックを実施。
    - calc_volatility: 20 日 ATR（true range の NULL 伝播制御）、atr_pct、avg_turnover、volume_ratio を計算。窓不足時は None を返す。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - 全関数とも prices_daily / raw_financials のみ参照し、本番 API へはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons のバリデーション（1..252）と範囲最適化を行う。
    - calc_ic: Spearman ランク相関（IC）を実装。欠損や ties の扱いを考慮し、有効サンプル数が 3 未満なら None を返す。
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE -> INSERT をトランザクションで行い原子性を保証）。
    - ユニバースフィルタのために target_date 以前の最新終値を参照（休場日対応）。
    - 処理は発注層に依存しない純粋な特徴量処理。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - _sigmoid, _avg_scores 等のユーティリティを実装し、NaN/Inf/None の扱いを安全に処理。
    - デフォルト重みを定義し、ユーザ指定重みは検証（不正値除外）して正規化（合計 1.0 に再スケール）。
    - AI の regime_score を集計して Bear レジーム判定（サンプル閾値あり）。Bear 時は BUY シグナルを抑制。
    - BUY シグナルは閾値（デフォルト 0.60）で決定。SELL シグナルはポジション情報と現在価格をもとにストップロス（-8%）とスコア低下で判定。
    - SELL が BUY より優先されるポリシー（SELL 対象は BUY から除外）。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - ログ出力で各ステップの状態を通知。

- パッケージ公開 API (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py)
  - build_features / generate_signals / calc_* 等の主要関数をトップレベルに公開。

### 変更 (Changed)
- 初回リリースのため、既存変更はなし。

### 修正 (Fixed)
- 初回リリースのため、既存修正はなし。

### セキュリティ (Security)
- RSS パーサで defusedxml を採用し XML 関連攻撃を軽減。
- news_collector の URL 正規化でトラッキングパラメータを除去し、記事 ID の一意性・冪等性を確保。
- J-Quants クライアントでリトライ/バックオフや 401 自動リフレッシュを実装し、冪等かつ安定した API 呼び出しを実現。
- .env 自動ロード時に OS 環境を保護する protected 機構を導入（override 時も OS 環境変数上書きを防止可能）。

### 既知の制限・今後の TODO
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の具体的な外部フェッチ（HTTP 実装の細部）や SSRF チェックの厳密化は今後追加予定。
- execution / monitoring パッケージは初期構成のみで、実際の発注/監視機能は別途実装予定。

---

注: 上記はコードベースから推測してまとめた CHANGELOG です。実際のリリースノート作成時は、変更履歴やコミットメッセージを参照して補完してください。