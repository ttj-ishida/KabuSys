KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ (日本語) の慣例に従って記載しています。

Unreleased
- Added
  - ドキュメント化されている未実装 / TODO を追記（今後の実装予定を明確化）
    - strategy のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date が必要で未実装のため今後対応予定。
  - 小さな改善点 / 安全対策の備忘（将来の改善対象）
    - .env パーサや HTTP リクエストの堅牢化（既に多くを実装済み）があるため、テストシナリオ追加や外部障害時の監視を強化予定。

0.1.0 - 2026-03-20
- Added
  - パッケージ初期リリース: kabusys v0.1.0
  - パッケージ構成（公開 API）
    - kabusys.__init__ による主要サブパッケージの公開: data, strategy, execution, monitoring
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装
      - プロジェクトルート検出: `.git` または `pyproject.toml` を親ディレクトリ探索で特定（CWD 依存しない）
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - .env パーサは export KEY=val 形式、クォート内のバックスラッシュエスケープ、行内コメントの扱い（クォートあり/なしの差）に対応
      - ファイル読み込み時のエンコーディング utf-8、読み込み失敗時に警告を出力
    - Settings クラス（settings インスタンス）を提供
      - J-Quants / kabu / Slack / DB パスなどのプロパティ取得を型安全にラップ
      - 必須変数未設定時に ValueError を送出する _require 実装
      - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - duckdb/sqlite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）
  - データ取得・保存 (src/kabusys/data/jquants_client.py)
    - J-Quants API クライアントを実装
      - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装
      - リトライロジック（指数バックオフ、最大 3 回）
        - リトライ対象ステータス: 408 / 429 / 5xx
        - 429 の場合は Retry-After ヘッダを優先
      - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰回避の allow_refresh フラグ）
      - ページネーション対応（pagination_key）を実装
      - fetch_* 系関数:
        - fetch_daily_quotes (日足 OHLCV)
        - fetch_financial_statements (四半期財務データ)
        - fetch_market_calendar (JPX カレンダー)
      - DuckDB への保存関数（冪等）
        - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE
        - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE
        - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE
      - データ型変換ユーティリティ: _to_float / _to_int（厳密な整数変換ルールを含む）
      - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスのトレーサビリティ確保
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィードから記事収集し raw_news へ冪等保存する機能を追加
      - デフォルトRSSソース: Yahoo Finance のビジネスカテゴリ
      - 記事ID は正規化後の URL の先頭 SHA-256（32 文字）で生成し冪等性を保証
      - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ削除（utm_ 等）、フラグメント除去、クエリパラメータソート
      - defusedxml による XML パース（XML Bomb 等への防御）
      - HTTP 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減
      - SSRF 対策のため非 http/https スキーム拒否等（コード内に記載の方針）
      - raw_news へのバルク INSERT をチャンク化して効率化
  - 研究用ファクター計算・探索 (src/kabusys/research/)
    - factor_research.py:
      - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率 (ma200_dev) の計算
      - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金（avg_turnover）、出来高比率(volume_ratio) の計算
      - calc_value: raw_financials と当日株価から PER / ROE を算出（EPS が 0/欠損時は None）
      - 各関数は prices_daily / raw_financials のみに依存し、本番 API にはアクセスしない設計
    - feature_exploration.py:
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得
      - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装（有効レコード 3 件未満は None）
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
      - rank ユーティリティ: 同順位は平均ランクで処理（丸めによる ties 対策あり）
    - research パッケージの __all__ に主要関数を公開
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features 実装:
      - research の calc_momentum / calc_volatility / calc_value から raw factor を取得
      - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円を適用
      - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ
      - features テーブルへ日付単位の置換（トランザクションとバルク挿入で原子性確保）
      - 休場日や欠損を考慮して target_date 以前の最新価格を参照
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals 実装:
      - features と ai_scores を組み合わせて各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - 各コンポーネントはシグモイド変換や平均化で 0–1 に正規化
      - デフォルト重み (_DEFAULT_WEIGHTS) を持ち、ユーザープロバイダ重みを検証して合成。合計が 1.0 でない場合は正規化
      - AI レジームスコアの平均が負でサンプル数が閾値以上であれば Bear レジームと判定し BUY を抑制
      - BUY: final_score >= デフォルト閾値 0.60（引数で変更可）。SELL: ストップロス（-8%）またはスコア低下
      - positions / prices_daily を参照してエグジット判定を行う（価格欠損時は判定スキップ）
      - signals テーブルへ日付単位の置換（トランザクションで原子性）
  - strategy パッケージの __all__ に build_features / generate_signals を公開
- Changed
  - なし（初回リリース）
- Fixed
  - なし（初回リリース）
- Deprecated
  - なし（初回リリース）
- Removed
  - なし（初回リリース）
- Security
  - defusedxml の利用による RSS/XM L パースの安全化
  - ニュース収集での受信サイズ制限と URL 正規化により SSRF・トラッキングパラメータ影響を低減
  - J-Quants クライアントの認証トークン処理はトークンリフレッシュを安全に行い、無限ループを防止

Notes / 設計上の重要な注意点（CHANGELOG に併記）
- ルックアヘッドバイアス対策:
  - すべての研究・戦略ロジックは target_date 時点までの情報のみを使用するよう設計されています。API からのデータ取得では fetched_at を UTC で記録し、いつデータを知り得たかを追跡可能にしています。
- 冪等性:
  - データ保存（raw_prices, raw_financials, market_calendar, features, signals, raw_news 等）は冪等操作を意識して ON CONFLICT / INSERT DO UPDATE / DO NOTHING を使う設計です。
- 未実装 / 今後の拡張:
  - strategy のトレーリングストップ（peak_price に依存）や時間決済（保有日数）などはコメントで未実装と明記されています。positions テーブルの拡張と合わせて実装予定です。
  - NewsCollector の RSS フィード一覧拡張、クローリングのスケジューリング、記事と銘柄の自動紐付け強化等は今後のタスクです。

開発上の参考
- バージョン番号は src/kabusys/__init__.py の __version__ = "0.1.0" に一致します。
- 主要な DB テーブル（コード中で参照される想定）
  - raw_prices, raw_financials, market_calendar, raw_news, features, ai_scores, positions, signals, prices_daily, etc.

もし望まれるなら:
- 各機能ごとに CHANGELOG のセクションを分割（例: data:, research:, strategy:）してより詳細に記載できます。
- RELEASE NOTES（英語版）やリリース手順・環境変数テンプレート（.env.example）も生成可能です。どちらか必要でしたら教えてください。