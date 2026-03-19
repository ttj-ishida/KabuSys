# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

現在のバージョンはパッケージ内の __version__ に合わせて v0.1.0 として初回公開相当の変更点をまとめています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

### Added
- パッケージ基本構成
  - パッケージ名: kabusys、トップレベルで data / strategy / execution / monitoring を公開。
  - バージョン定義: __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルート探索: .git または pyproject.toml を基準に探索する実装により、カレントワーキングディレクトリに依存しない読み込みを実現。
  - .env パーサ実装:
    - コメント行/空行の無視、`export KEY=val` 形式の対応。
    - シングルクォート／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの無視、クォート無しの '#' を条件付きでコメントとして扱う等の堅牢なパース処理を実装。
  - 設定取得用クラス Settings を提供。必須設定に対する _require() によるエラー通知を実装。
  - Settings での便利プロパティ:
    - J-Quants / kabu API / Slack の必須トークン/設定取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 型返却。
    - 環境（KABUSYS_ENV: development / paper_trading / live）とログレベル（LOG_LEVEL: DEBUG/INFO/...）の検証・補正。
    - is_live / is_paper / is_dev のブール判定プロパティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 408/429/5xx の再試行対応、429 の Retry-After ヘッダ優先。
    - 401 を受け取った場合の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュの実装（ページネーション間で共有）。
    - JSON レスポンスの堅牢な扱い（デコードエラー時は明確な例外）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性確保）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使用した保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - PK 欠損行のスキップとログ警告、保存件数のログ出力。
  - ユーティリティ: _to_float / _to_int（安全な変換）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集・前処理・保存を行うモジュールを追加。
    - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネス RSS）。
    - XML パースは defusedxml を使用して XML Bomb 等の攻撃を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和。
    - URL 正規化: スキーム/ホストの小文字化、既知トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリキー順ソートを実装。
    - 記事 ID は（文書内コメントに示す通り）URL 正規化後の SHA-256 等で生成する設計（冪等性確保）。
    - HTTP スキーム以外拒否や SSRF に対する注意設計、DB へはトランザクションでまとめて挿入、チャンク化して SQL 長制限に対応。

- 研究系（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: ATR 20 日（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損 の場合は None）。
    - DuckDB SQL を活用した効率的な窓関数処理、スキャン範囲のバッファ設計（カレンダー日でのバッファ）を採用。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証（正の整数かつ <= 252）を行う。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル数が 3 未満の場合は None を返す。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ機能（None 値除外）。
    - rank: 同順位は平均ランクを採る実装（floating rounding による ties の扱いに配慮）。
  - 研究用 API を __all__ で公開（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールから取得した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化: 指定カラム群を zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位での置換（DELETE + INSERT をトランザクションで実行して原子性を保証）。
    - 欠損や非有限値に対する扱いを明確化。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントに対する変換関数を実装（シグモイド・逆 PER 変換・ボラティリティ反転など）。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。外部から渡された weights は検証・補完・再スケールされる。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値 _BEAR_MIN_SAMPLES を満たす場合）により BUY シグナルを抑制するロジック。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY、保有ポジションに対して STOP LOSS（-8%）やスコア低下で SELL を生成。
    - SELL は BUY より優先して除外、signals テーブルへ日付単位置換で保存（トランザクション）。
    - weights の不正値はスキップしてデフォルトにフォールバックする防御的設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- XML パースに defusedxml を使用（XML Entity Expansion 等の攻撃を軽減）。
- news_collector の設計に SSRF / トラッキングパラメータ除去 / レスポンスサイズ制限などセキュリティ・安定性を考慮した対策を導入。
- API クライアントでトークンを安全に取り扱い、401 発生時に自動リフレッシュを行うが、無限ループを避けるためリフレッシュの呼び出しには保護（allow_refresh フラグ）を実装。

### Known limitations / TODO
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超）など一部のエグジット条件は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- news_collector の記事 ID 生成やニュースと銘柄の紐付け処理はコメントで設計が示されているが、実装の詳細（ハッシュ生成部分など）はドキュメントベースの設計に依存。
- 一部の SQL は DuckDB に依存した実装（WINDOW 関数等）。他の DB への移植には変更が必要。

---

参照:
- 各モジュールのコード内に設計方針・処理フロー・注意点をコメントとして記載しています。必要であれば各関数ごとの変更履歴や詳細設計ドキュメントを展開して作成します。