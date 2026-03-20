# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。セマンティック バージョニングを使用します。

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点をモジュールごとにまとめます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ識別子とバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサー実装（コメント、export プレフィックス、クォート／エスケープ処理、インラインコメント処理など）。
  - Settings クラスを提供し、以下の設定プロパティを安全に取得できるようにした:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - 重要な未設定時は ValueError を投げ、利用者に .env.example を参照させる設計。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 冪等性を考慮したページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - HTTP レスポンスに対するリトライ処理（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 時の自動トークンリフレッシュ（1 回のみ）と ID トークン取得ロジック。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスのトレースを可能に。
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes: raw_prices への upsert（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials への upsert。
    - save_market_calendar: market_calendar への upsert。
    - データ整形ヘルパー (_to_float / _to_int) を実装し、不正な値を安全に扱う。
    - PK 欠損行はログで警告しスキップする挙動。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存する処理設計とユーティリティを追加。
  - セキュリティ・堅牢性対策:
    - defusedxml を使った XML 解析（XML Bomb 対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を防止。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント削除）。
    - 記事IDは正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - HTTP/HTTPS スキームの検査、SSRF 対策に関する設計上の留意点。
  - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）とトランザクションまとめでパフォーマンスを最適化。
  - デフォルト RSS ソースに Yahoo Finance（business カテゴリ）を登録。

- リサーチ（kabusys.research）
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA による乖離）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（20 日ウィンドウ）
    - calc_value: per, roe（raw_financials の最新財務データを用いる）
  - 解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターン間の Spearman ランク相関（IC）計算（サンプル不足時は None）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 平均ランク処理（同順位は平均ランク）を実装
  - 外部ライブラリ（pandas など）に依存せず、標準ライブラリ＋DuckDB SQL で実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールの生ファクターを取得してマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ
    - features テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を確保
    - 欠損値 / 非有限値への耐性を確保

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換・欠損補完（None → 中立 0.5）を適用して final_score を算出
    - デフォルト重みを実装（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）
    - ユーザー指定 weights の検証・正規化（未知キーの除外、非数値・負値除外、合計再スケール）
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。サンプル不足時は無視）
    - BUY: threshold を超える銘柄にランク付き BUY シグナル（Bear 時は BUY 抑制）
    - SELL: 保有ポジション（positions テーブル）に対するエグジット判定を実装
      - ストップロス: 現在値 / avg_price - 1 <= -8%
      - スコア低下: final_score < threshold
      - SELL が BUY より優先される（SELL 対象は BUY から除外）
    - signals テーブルへの日付単位置換で冪等性を確保

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector: defusedxml の採用、受信バイト上限、URL 正規化とスキームチェックにより XML Bomb / メモリ DoS / SSRF に対する防御を導入。
- jquants_client: 重要な認証フローでのトークン自動更新処理は allow_refresh フラグで再帰を制御し、安全なリトライを保証。

### 既知の制限・未実装（Notes）
- signal_generator のトレーリングストップ・時間決済など一部のエグジットロジックは positions テーブルの追加フィールド（peak_price / entry_date 等）に依存しており現時点では未実装としてコメント記載あり。
- calc_value: PBR や配当利回りなど一部バリューメトリクスは未実装。
- news_collector の実際の RSS フェッチ処理（HTTP の受信・パースの上流ロジック）は設計方針が示されているが、実運用で追加のフェールセーフ（タイムアウト、リダイレクト制御など）を検討する余地あり。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は外部で準備する必要があります（スキーマ定義はこのリリースに含まれていない）。

---

今後の予定:
- 取り扱い易さ向上のため CLI / サービス化、モニタリング（monitoring モジュール）との連携強化、テストカバレッジの追加を予定しています。必要な追加機能や優先度の高い改善点があればご連絡ください。