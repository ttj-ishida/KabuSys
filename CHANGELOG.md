# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した初期のリリースノートです。

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期実装 (kabusys)
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョン "0.1.0" を定義。
  - パッケージ構成: data, strategy, execution, monitoring モジュールを公開。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の行パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラスによる設定アクセスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境/ログレベル等）。
  - 設定値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック、is_live / is_paper / is_dev の便宜プロパティ。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API クライアント実装（HTTP 呼び出し、JSON デコード、ページネーション対応）。
  - レート制限制御: 固定間隔スロットリング _RateLimiter（120 req/min 想定）。
  - リトライロジック: 指数バックオフ、最大試行回数、408/429/5xx のリトライ扱い。
  - 401 発生時の自動トークンリフレッシュを 1 回のみ試行（無限ループ防止）。
  - トークンキャッシュ機構（モジュールレベル）。
  - データ取得関数:
    - fetch_daily_quotes: 日足データ取得（ページネーション対応）。
    - fetch_financial_statements: 財務データ取得（ページネーション対応）。
    - fetch_market_calendar: JPX カレンダー取得。
  - DuckDB 保存関数（冪等、ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - データ整形ユーティリティ: _to_float / _to_int（堅牢な変換ルール）。
  - デザインノート（ログ取得時刻 fetched_at を UTC 記録、look-ahead bias 対策等）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集、前処理、DuckDB への冪等保存を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルでないか検査、リダイレクト時の事前検査ハンドラ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 展開後のサイズチェック。
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、クエリソート、フラグメント除去。
  - 記事 ID 生成: 正規化 URL の SHA-256 先頭 32 文字による冪等 ID。
  - RSS 解析と記事前処理: URL 除去、空白正規化、pubDate のフォールバック処理。
  - DB 保存:
    - save_raw_news: チャンク INSERT + INSERT ... RETURNING による挿入済み ID の取得、トランザクションまとめ。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。
  - 銘柄コード抽出: 4 桁数字パターンから known_codes に含まれるものだけを抽出。
  - デフォルト RSS ソースに Yahoo Finance を設定。
- DuckDB スキーマ初期化 (src/kabusys/data/schema.py)
  - Raw Layer のテーブル定義（raw_prices / raw_financials / raw_news / raw_executions 等の DDL を定義）。
  - DataSchema に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した設計。
- リサーチ / ファクター計算 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB の prices_daily テーブルから一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（欠損・ties 対応）。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量計算。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev を prices_daily から計算（ウィンドウ判定でデータ不足は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播制御、部分窓対応）。
    - calc_value: raw_financials の最新財務データを結合して PER / ROE を計算（EPS が 0 または欠損時は None）。
  - research パッケージの公開 API に上記関数群と zscore_normalize（kabusys.data.stats 由来）を含むエクスポートを追加。
- 実装上のパフォーマンス考慮
  - DuckDB 側でウィンドウ関数を多用し、必要スキャン範囲を限定（カレンダーバッファ）することでクエリ数・IO を削減。
  - ニュース保存・シンボル紐付けでチャンク化してバルク INSERT を実行。

### Fixed
- （初期リリースのため特定のバグ修正履歴はなし。実装上の安全性・堅牢化を考慮した実装を行っています。）

### Security
- RSS パーサで defusedxml を使用し、また SSRF（リダイレクト検査、ホストプライベートチェック、スキーム検証）やレスポンスサイズ制限等の防御を実装。
- J-Quants クライアントはトークン自動リフレッシュ（401 の扱いを限定）、リトライ時のログ・スリープ制御を実装。

### Notes / Implementation details
- .env パーサはシェル風の export プレフィックスやクォート・エスケープを考慮しており、コメント処理はクォートあり/なしで異なるルールを適用しています。
- NewsCollector の記事 ID は URL 正規化後のハッシュにより生成しているため、トラッキングパラメータの有無による重複登録を防止します。
- DuckDB への保存は可能な限り冪等に設計（PRIMARY KEY / ON CONFLICT を利用）。
- 外部依存は最小限（defusedxml, duckdb を使用）、research モジュールは標準ライブラリ中心で実装されています（pandas 等に依存しない設計）。
- 公開 API は将来的な互換性を考慮して Settings クラス・各種 calc_* 関数・データ保存関数群を意図的に安定化させる方針です。

---

今後のリリースでは以下を検討すると良い点（提案）
- strategy / execution / monitoring の具体実装・テストの追加。
- 単体テスト・CI の整備（特にネットワーク依存部のモック）。
- DuckDB スキーマの完全な定義とマイグレーション機構の追加。
- 性能チューニング（大規模データセットにおけるクエリプラン最適化）およびメトリクスの収集。