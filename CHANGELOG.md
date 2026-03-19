# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリース (v0.1.0) の変更点を日本語でまとめています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パブリック API としてモジュール群をエクスポート: `data`, `strategy`, `execution`, `monitoring`。

- 環境設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ファイル行のパース機能を強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、クォート無しでのコメント判定などに対応。
  - .env 読み込み時の上書き制御（override / protected）を導入し、OS 環境変数を保護。
  - 必須環境変数取得用 `_require` と `Settings` クラスを実装（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の値検証（限定列挙）/ユーティリティプロパティ（is_live / is_paper / is_dev）を提供。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - レート制御: 固定間隔スロットリング（120 req/min）を守る `_RateLimiter` を導入。
    - 自動ページネーション対応（pagination_key を用いた取得ループ）。
    - リトライ戦略: 指数バックオフ、最大3回、408/429/5xx を対象にリトライ。
    - 401 受信時はリフレッシュ（トークン取得）して一度だけ再試行する仕組みを実装。
    - トークンキャッシュ（モジュールレベル）によりページネーション間で ID トークンを共有。
    - JSON デコード失敗時の明確なエラー報告。
  - データ保存ユーティリティ:
    - fetch_* 系関数（株価・財務情報・マーケットカレンダー）を実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。冪等性を保つために SQL の ON CONFLICT を使用して INSERT を UPDATE に切り替える。
  - 入出力変換ユーティリティ `_to_float`, `_to_int` を提供し、形式不正な値の安全な扱いを行う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集・前処理・DB 保存ワークフローを実装:
    - RSS フェッチ (`fetch_rss`)：HTTP タイムアウト、gzip 対応、Content-Length/実際の読み込みバイト数による上限チェック（10MB）、gzip 解凍後の再チェック（Gzip-bomb 対策）。
    - XML パースに defusedxml を利用して XML ベースの攻撃を緩和。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト検査用 `_SSRFBlockRedirectHandler` と最終 URL の再検証。
      - プライベート/ループバック/リンクローカル/マルチキャスト IP を検出してアクセスを拒否（DNS 解決を行い A/AAAA を検査）。
    - URL 正規化 (`_normalize_url`) とトラッキングパラメータ除去（utm_, fbclid, gclid 等）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）`preprocess_text` を提供。
    - 記事の DuckDB 保存 (`save_raw_news`)：チャンク化挿入、トランザクション管理、INSERT ... RETURNING を使って新規 ID を返す。
    - 記事と銘柄コードの紐付け（news_symbols）保存関数（`save_news_symbols` / `_save_news_symbols_bulk`）を実装（重複除去、チャンク化、トランザクション）。
    - テキストからの銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁コード検出、既知コードセットでフィルタ、重複排除）。
    - 統合収集ジョブ `run_news_collection` を実装（各ソース個別のエラーハンドリング、known_codes による銘柄紐付け）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema に基づくテーブル定義（Raw 層を中心に）を実装:
    - raw_prices（生株価）、raw_financials（生財務データ）、raw_news（収集記事）などの DDL を用意。
    - テーブル定義には制約（NOT NULL、PRIMARY KEY、CHECK 句等）を含め、データ品質を保つ設計。

- リサーチ機能 (kabusys.research)
  - 主要ファクター計算モジュールを実装（`research` パッケージの公開 API を定義）。
  - 特徴量探索 (feature_exploration.py):
    - calc_forward_returns: 指定日から複数ホライズンにおける将来リターンをまとめて取得する処理（DuckDB の prices_daily を参照、単一クエリで複数ホライズンを取得）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。欠損や定数系列を適切に扱い、データ不足（<3 レコード）では None を返す。
    - rank: 同順位は平均ランクで処理。丸め誤差対策に round(v, 12) を用いる。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー。
  - ファクター計算 (factor_research.py):
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility: atr_20（20日 ATR）、atr_pct（相対 ATR）、avg_turnover、volume_ratio（当日 / 20日平均）を計算。true_range の NULL 伝播を考慮した実装。
    - calc_value: raw_financials から直近財務を取得して PER（EPS が 0 または欠損なら None）と ROE を計算。
  - research パッケージの __all__ を整備し、主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector における SSRF 対策、defusedxml による XML パースの安全化、受信サイズ制限や gzip 解凍後の再検査等、外部入力に対する複数の防御策を導入。
- J-Quants クライアントでのトークン管理と例外ハンドリングにより、認証関連の安全なリトライを実現。

### 既知の制限 / 注意事項
- DuckDB スキーマ定義は Raw 層を中心に定義されているが、Execution 層など一部の DDL は継続実装が必要（スニペットの途中でファイルが終端している箇所あり）。
- research モジュールは標準ライブラリのみで実装されているため、大規模データ処理性能や高度な統計機能は別途 Pandas 等で補うことが想定される。
- J-Quants API のレート制限やレスポンス仕様の変化はクライアント側の修正を要する可能性がある。

---

初期リリース (v0.1.0) では、データ収集・永続化、RSS ニュース収集、基本的なファクター計算・解析ユーティリティ、環境設定管理といった基盤機能を整備しました。今後のリリースでは Execution（発注／ポジション管理）や Strategy/Monitoring の具体実装、追加のスキーマ・ユーティリティ、テスト/ドキュメントの拡充を予定しています。