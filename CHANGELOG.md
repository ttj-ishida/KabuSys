# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で日本語で記載します。

全般ルール:
- 次の形式に従います: Unreleased → 各リリース
- 日付はパッケージバージョン __version__ に合わせて記載します（このリリース: 0.1.0）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルート判定: .git または pyproject.toml を探索してルートを特定（CWD非依存）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
    - 読み込み順: OS 環境 > .env.local（上書き）> .env（既存を尊重）。
  - .env パーサーの実装:
    - export KEY=val 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い、トラッキング的な空白ルール等をサポート。
    - 上書き禁止キー(protected)を指定して OS 環境を保護。
  - Settings クラスを追加し、アプリケーションで必要な設定項目をプロパティ経由で提供:
    - J-Quants 用: jquants_refresh_token
    - kabuステーション API: kabu_api_password, kabu_api_base_url
    - Slack: slack_bot_token, slack_channel_id
    - DB: duckdb_path, sqlite_path（Path オブジェクトとして取得）
    - システム設定: env, log_level と検証（許容値チェック）、is_live/is_paper/is_dev の補助プロパティ
  - 必須環境変数未設定時は明確な ValueError を投げる（.env.example を参照する旨のメッセージ）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限対応（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）: ネットワークエラー、408/429/5xx 対象。
    - 401 受信時は refresh token で ID トークンを自動更新して1回だけ再試行。
    - ページネーション対応 (pagination_key)。
    - 取得時に fetched_at を UTC ISO 形式で記録し、Look-ahead bias のトレーサビリティを確保。
  - データ保存用ユーティリティ:
    - save_daily_quotes: raw_prices テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - レコード整形／型変換ユーティリティ (_to_float / _to_int) を実装し不正値を None 扱いに。
    - PK 欠損行はスキップし、スキップ数を警告ログに出力。
  - fetch_* 系関数:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供し JSON → レコードリストで返却。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news に冪等保存する基盤を実装。
  - 安全対策:
    - defusedxml による XML 解析（XML Bomb 等の緩和）。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）によりメモリ DoS を軽減。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）の削除、フラグメント除去、クエリキーのソート。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用いて冪等性を保証。
    - HTTP/HTTPS 以外のスキームに対するチェック（SSRF 緩和のためのホスト解決などの実装想定）。
  - バルク INSERT のチャンク化による性能改善（_INSERT_CHUNK_SIZE）。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算群を提供（外部ライブラリに依存せず標準ライブラリのみで実装）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。必要な行数不足時は None を返す設計。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio を計算。true_range の NULL 伝播を意図的に制御。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS が欠損/0 の場合は None）。
  - 解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）を実装。有効サンプルが不足（<3）なら None。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランク（小数丸め対策として round(..., 12) を利用）。

- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research で計算した生ファクターを集約・ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE → INSERT をトランザクションで実行し原子性を確保）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネント値はシグモイド変換や PER の逆スコア等を採用。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.1）を使用。ユーザ指定重みは検証・正規化して受け付ける。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 で BUY を抑制。
    - BUY シグナル閾値 default=0.60。SELL（エグジット）判定にはストップロス（-8%）およびスコア低下を実装。
    - signals テーブルへ日付単位の置換をトランザクションで行い冪等性を担保。
    - positions や price 欠損時の挙動（価格欠損なら SELL 判定をスキップする等）を明示的に扱うログ出力を追加。

- 実行層 / 監視層
  - パッケージ構造に execution、monitoring のエントリを用意（初期ステブ/名前空間公開）。

### 変更 (Changed)
- 初回リリースのため変更履歴はなし。

### 修正 (Fixed)
- 初回リリースのため修正履歴はなし。

### セキュリティ (Security)
- news_collector で defusedxml を採用して XML による攻撃を緩和。
- ニュース取得時に受信バイト数上限、URL 正規化、トラッキングパラメータ削除、HTTP/HTTPS のスキームチェック、及び潜在的な SSRF を考慮した記述を追加。
- J-Quants クライアントは 401 時のトークン自動更新ロジックを実装し、allow_refresh フラグで再帰を防止。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

---

備考:
- 本リリースは設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく実装の初版と想定しています。各機能は DuckDB の既定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）を前提とします。
- 将来的な改善候補:
  - signal_generator のトレーリングストップ / 時間決済の完全実装（positions に peak_price / entry_date が必要）。
  - news_collector の URL ホスト検査強化や外部 HTTP クライアントの抽象化。
  - より詳細なエンドツーエンドの統合テストおよび負荷試験。