CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」仕様に概ね準拠します。

注: 以下の変更点は、提供されたコードベースの内容から推測して記載しています。

## [Unreleased]
- 今後のリリースに向けたマイナー改善やテストの追加を想定。
  - research / factor_research のさらなる指標追加や最適化
  - schema の Execution Layer 完全実装（raw_executions テーブル定義の続き等）
  - 単体テスト・CI ワークフローの追加

## [0.1.0] - 2026-03-19
初回公開リリース。

### 追加 (Added)
- コアパッケージ
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数からの設定自動読み込み機能を実装
  - プロジェクトルート検出 (_find_project_root): .git または pyproject.toml を基準に探索
  - .env パーサー (_parse_env_line): export 形式、クォート処理、インラインコメント処理に対応
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを公開
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）

- Research（特徴量・ファクター分析）
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括で計算
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 集計
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio 等を計算（ATR, 20日平均等）
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を算出
  - research パッケージの __all__ に主要関数をエクスポート

- Data クライアント / ETL ツール (kabusys.data)
  - jquants_client
    - J-Quants API 用クライアントを実装（価格日足、財務データ、マーケットカレンダー取得）
    - レート制限対応: 固定間隔スロットリングで 120 req/min 制御（_RateLimiter）
    - 再試行ロジック: 指数バックオフ / 最大 3 回、408/429/5xx 対象
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）と再試行
    - ページネーション対応（pagination_key）
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（冪等: ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float / _to_int（安全な None ハンドリング）
  - news_collector
    - RSS フィード取得と raw_news への保存ワークフローを実装
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等の防止）
      - SSRF 対策: リダイレクト時のスキーム/ホスト検証用ハンドラ (_SSRFBlockRedirectHandler)
      - ホストのプライベートアドレス判定（DNS 解決 / IP チェック）
      - URL スキーム検証（http/https のみ許可）
      - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES、Gzip 解凍後も検査）
    - コンテンツ処理:
      - URL 正規化およびトラッキングパラメータ除去 (_normalize_url, _TRACKING_PARAM_PREFIXES)
      - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成（_make_article_id）
      - テキスト前処理 (preprocess_text)：URL 除去・空白正規化
      - pubDate パース（RFC 2822）と UTC 変換（_parse_rss_datetime）
      - 銘柄コード抽出 (extract_stock_codes)：4桁数字パターンと known_codes フィルタ
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING を使用して新規挿入 ID を返す。チャンク・トランザクション化。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けを一括挿入（ON CONFLICT DO NOTHING）
    - run_news_collection: 複数ソースからの統合収集ジョブ（個々のソースは独立してエラーハンドリング）
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録

- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw Layer の DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions（raw_executions の定義はファイル途中まで提供）
  - テーブル定義に PRIMARY KEY / CHECK 制約 / fetched_at デフォルト値を付与

- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" とパッケージ __all__ を定義

### 変更 (Changed)
- （初回リリースのため該当なし。今後のリリースで既存機能の改良を予定）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサーで defusedxml を使用し、XML に対する潜在的攻撃を軽減
- HTTP リダイレクト検査およびホストのプライベートアドレス判定で SSRF リスクを低減
- ニュース収集時に受信サイズ上限・gzip 解凍後チェックを導入し DoS リスクを軽減
- .env 読み込みはプロジェクトルート検出を用い、任意のディレクトリからの誤読を防止

### 既知の制限 / 注意点 (Known issues / Notes)
- research モジュールは標準ライブラリのみで実装されており、高度な集計や大規模データに対する最適化（pandas 等の利用）は今後の改善余地あり
- schema の Execution Layer（発注・約定・ポジション管理）や raw_executions テーブル定義の続きは未完（ファイルは途中まで）
- jquants_client は urllib を使用しており、高度な HTTP 機能が必要な場合は requests 等への移行を検討
- .env 自動読み込みはデフォルトで有効。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能

---

脚注:
- 日付はコード解析時点の想定日を記載しています。
- 実際のリリースノートでは、実行結果やマイグレーション手順、既存ユーザーへの影響等を追記してください。