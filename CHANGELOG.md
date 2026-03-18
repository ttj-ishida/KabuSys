# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-18

初回リリース。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本 (__init__.py) とバージョン管理を導入（バージョン: 0.1.0）。
  - パッケージ公開 API として "data", "strategy", "execution", "monitoring" を公開。

- 環境設定 / 設定読み込み (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env/.env.local の自動ロード（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサー（コメント、export プレフィックス、クォート／エスケープ対応）を実装。
  - 必須設定取得用の _require 関数および各種プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパス、環境/ログレベル判定など）を提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値のチェック）。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限制御（120 req/min）を行う固定間隔スロットリング RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx 対象）を実装。
  - 401 発生時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE を使用）。
  - 値変換ユーティリティ _to_float / _to_int を実装して不正データを適切に扱う。
  - fetched_at（UTC）を記録して Look-ahead Bias を軽減する設計。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存するモジュールを実装。
  - セキュリティ対策：
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - リダイレクト時のスキーム検証とプライベートアドレス検査による SSRF 防止（カスタム RedirectHandler）。
    - レスポンス長の上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL スキーム検証（http/https のみ許可）。
    - トラッキングクエリパラメータ（utm_* 等）の除去と URL 正規化、記事 ID の SHA-256（先頭32文字）による生成で冪等性を確保。
  - テキスト前処理（URL除去・空白正規化）、RSS pubDate の安全なパースを実装。
  - DB 保存はトランザクションとチャンク化を行い、INSERT ... RETURNING で実際に挿入された件数を返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 記事中の銘柄コード抽出ユーティリティ（4桁数字の候補を known_codes でフィルタ）を実装。
  - run_news_collection により複数ソースの取得・保存・銘柄紐付けを一括実行するジョブを提供。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - Raw レイヤーのテーブル DDL 定義を導入（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。（データ層のスキーマ定義と初期化の基礎を提供）

- リサーチ（ファクター計算） (src/kabusys/research/)
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定基準日から複数ホライズンの将来リターンを一括取得（DuckDB の window 関数を利用）。
    - calc_ic: ランク相関（Spearman ρ）による IC 計算を実装（欠損や ties を考慮）。
    - rank / factor_summary: ランク化ロジック（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）。
  - factor_research モジュールを実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播やカウント閾値を考慮）。
    - calc_value: raw_financials から最新の財務指標を取得し PER / ROE を計算（prices_daily と結合）。
  - research パッケージの __init__ で上記ユーティリティ群と zscore_normalize を再公開。

- モジュール構成
  - strategy / execution / research/__init__.py 等の基本的なパッケージ初期化ファイルを追加（strategy と execution は空の __init__ を用意し、将来的拡張に備える）。

### 変更 (Changed)
- （該当なし）初回リリースのため、互換性に関する変更履歴はありません。

### 修正 (Fixed)
- （該当なし）初回リリースのため、バグ修正履歴はありません。

### セキュリティ (Security)
- news_collector において SSRF 対策、XML パースの安全化、レスポンスサイズ上限、gzip 解凍チェックなどを導入し、外部入力に対する堅牢性を強化しました。
- J-Quants クライアントはトークン管理とリトライ制御を組み込み、401 発生時の自動リフレッシュを実装。

### パフォーマンス (Performance)
- J-Quants クライアント: レートリミッタとページネーション対応により API 利用を効率化。
- news_collector: DB 挿入時にチャンク化（_INSERT_CHUNK_SIZE）と単一トランザクションを採用してオーバーヘッドを低減。
- feature_exploration / factor_research: DuckDB の window 関数を活用して一括で集計・計算し、読み取り回数を抑制。

### 既知の制限 (Known limitations)
- 外部依存を最小化する方針だが、一部のユーティリティ（例: zscore_normalize）は別モジュール (kabusys.data.stats) に依存している想定。
- strategy / execution パッケージは現状で具象実装を含まず、今後の実装で発注/ポジション管理ロジックを追加予定。

---

注: 上記はコードベースから推測して作成した CHANGELOG です。実際のコミット単位やリリースノート運用に合わせて追記・修正してください。