# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に従い、セマンティックバージョニングを利用します。
このプロジェクトの初期バージョン 0.1.0 をリリースしました。

## [Unreleased]

（現在の開発中の変更はここに記載）

---

## [0.1.0] - 2026-03-18

### Added
- パッケージ基本構成を追加
  - kabusys パッケージの初期モジュール定義（data, strategy, execution, monitoring）。
  - バージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として管理。

- 環境設定管理機能を追加（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
  - .env パーサーの実装:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート対応、インラインコメントルールをサポート。
    - クォート内のエスケープシーケンスにも対応。
  - 必須設定取得時に未設定で例外を投げる `_require()` を実装。
  - Settings クラスに主要設定プロパティを提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/ 環境（development, paper_trading, live）/ ログレベル検証等。
    - デフォルト DB パス: `data/kabusys.duckdb`, `data/monitoring.db`。

- データ取得クライアントを追加（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（urllib ベース）。
  - 機能:
    - 日足（OHLCV）・財務データ（四半期）・取引カレンダーの取得（ページネーション対応）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回）と 408/429/5xx 再試行対応。
    - 401 受信時にリフレッシュトークンを使って ID トークンを自動更新して再試行。
    - 取得時の fetched_at を UTC で記録し Look-ahead Bias のトレースを可能に。
  - DuckDB への保存関数（冪等）を提供:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE による上書きで冪等性を確保。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、受信データの堅牢な正規化を行う。

- ニュース収集機能を追加（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する一連処理を実装。
  - 主要機能・設計:
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先のスキーム/ホスト検査（プライベート IP 判定）。
      - リクエスト前にホストがプライベートかをチェック。
    - レスポンスサイズ上限（10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 記事前処理（URL除去、空白正規化）。
    - 銘柄コード抽出（4桁数字、既知コードセットでフィルタリング）と news_symbols への一括保存処理（チャンク/トランザクション）。
    - DB 保存: INSERT ... RETURNING を利用して、実際に挿入された件数/ID を正確に返却。
    - 全体ジョブ `run_news_collection` によるソース単位の独立エラーハンドリング。

- リサーチ（特徴量・ファクター）機能を追加（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB 上の prices_daily から一括計算。
    - calc_ic: ファクターと将来リターンの Spearman（ランク）相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めで ties の検出安定化）。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算。
    - 標準ライブラリのみでの実装を志向（pandas 等に依存しない）。
  - factor_research:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足は None。
    - calc_volatility: 20日 ATR（atr_20）, atr_pct, 20日平均売買代金（avg_turnover）, volume_ratio を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から直近財務データを結合して PER (price / EPS) と ROE を計算（EPS 0/欠損は None）。
    - すべて DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注 API 等にはアクセスしない設計。

- DuckDB スキーマ初期化（kabusys.data.schema）
  - Raw Layer の DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（テーブル定義を含む。raw_executions は実行系テーブルの定義を含む）
  - DataModel に基づく 3 層（Raw / Processed / Feature / Execution）構想を反映する骨組みを用意。

### Security
- ニュース収集に関する SSRF 対策と XML パースの安全化を実装。
  - defusedxml を使用。
  - リダイレクト時のスキーム/ホスト検証、プライベート IP 判定を実装。
  - レスポンスサイズ制限・gzip 解凍後の再チェックで DoS 対策を強化。
- .env の読み込みはデフォルトで有効だが無効化フラグを用意（テスト時に環境汚染を防止）。

### Notes / Known limitations
- research/feature_exploration は標準ライブラリのみで実装しているため、大規模データや高度な統計解析では pandas/numpy に比べパフォーマンス・機能面で劣る可能性がある（将来的に置換検討）。
- J-Quants クライアントは urllib を使用。requests 等に比べインターフェースが素朴なため、必要に応じて拡張や移行を検討してください。
- ID トークンはモジュールレベルでキャッシュされる（ページネーション間で共有）。プロセス外でのトークン更新には対応していない点に注意。
- schema.py の Execution テーブル定義等は必要に応じて拡張予定。
- strategy / execution / monitoring パッケージの初期化は存在するが、具体的な発注ロジックやモニタリング実装は今後の実装対象。

---

今後のリリースで予定している改善例:
- research モジュールの性能改善（pandas/numpy の導入検討）。
- strategy / execution の発注ロジックとテスト用モックの追加。
- DuckDB スキーマの拡張（Processed/Feature 層の DDL 完全実装）。
- API クライアントの observability（メトリクス、詳細なリトライメトリクス等）。

もし CHANGELOG に追加すべき点や誤認があれば指摘してください。