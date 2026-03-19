# Changelog

すべての重要な変更をこのファイルに記録します。
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性のある改善等）
- Deprecated: 非推奨
- Removed: 削除
- Fixed: バグ修正
- Security: セキュリティ関連の対策

※バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

---

## [Unreleased]
（現時点で未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムの基盤機能を実装しました。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys v0.1.0）。
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring（strategy/execution は雛形）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする仕組みを実装（読み込み優先度: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準に探索、パッケージ配布後も動作）。
  - .env 行パーサ実装:
    - コメント行 / export プレフィックス対応
    - シングル／ダブルクォート対応（バックスラッシュエスケープ処理）
    - インラインコメント処理（クォート無の場合もスペース直前の#をコメントとみなす）
  - 環境変数保護（protected）を考慮した上書きロジックを実装。
  - 設定ラッパー Settings を実装:
    - 必須変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パス既定値（DUCKDB_PATH, SQLITE_PATH）
    - 環境モード検証（KABUSYS_ENV: development / paper_trading / live）
    - ログレベル検証（LOG_LEVEL: DEBUG/INFO/...）
    - ユーティリティプロパティ（is_live / is_paper / is_dev）

- データ収集・保存（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API のベース実装: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
    - HTTP リクエストユーティリティを実装（JSON デコード検査）
    - レート制御: 固定間隔スロットリング（120 req/min）による RateLimiter を導入
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を考慮。429 の場合は Retry-After を優先。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ
    - DuckDB への冪等保存ユーティリティ:
      - save_daily_quotes: raw_prices への挿入（ON CONFLICT DO UPDATE）
      - save_financial_statements: raw_financials への挿入（ON CONFLICT DO UPDATE）
      - save_market_calendar: market_calendar への挿入（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float / _to_int（安全な変換・空値ハンドリング）
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得と記事整形の実装（DEFAULT_RSS_SOURCES を含む）
    - セキュリティ・堅牢性:
      - defusedxml を用いた XML パース（XML Bomb などの防御）
      - SSRF 対策: 非 http/https スキーム排除、プライベート IP/ループバック/リンクローカル判定を行いアクセスを拒否
      - リダイレクト時もスキームとホスト検証を行うカスタム RedirectHandler を導入
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 緩和）
    - URL 正規化とトラッキングパラメータ除去（utm_ 等の除去・クエリソート・フラグメント削除）
    - 記事 ID 生成: 正規化 URL の SHA-256（先頭32文字）で冪等性確保
    - テキスト前処理: URL 除去・空白正規化
    - DB 保存:
      - save_raw_news: raw_news へのチャンク INSERT（ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用して新規 ID を返す）
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付け保存（チャンク処理・トランザクション）
    - 銘柄コード抽出: 正規表現による 4 桁コード抽出と known_codes によるフィルタ
    - 統合ジョブ: run_news_collection（複数ソース処理、個別エラー隔離、紐付け自動実行）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw Layer の DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の雛形を含む）
  - 初期化用スクリプトの基礎を実装（DataSchema.md に基づく設計）

- 研究（Research）モジュール（src/kabusys/research/*）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から各ホライズン（例: 1,5,21 営業日）先への将来リターン計算（DuckDB の prices_daily を参照）
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（結合・欠損除外・最小レコード数チェック）
    - rank: 平均ランク処理（同順位は平均ランク、丸めで ties 検出の安定化）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（ウィンドウ・行数チェック含む）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio の計算（true_range の NULL 伝播制御含む）
    - calc_value: PER / ROE の計算（raw_financials から最新報告を取得して結合）
  - research パッケージ __init__ を整備して主要関数を公開

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- ニュース収集における多層の安全対策を導入:
  - defusedxml による XML パース
  - SSRF 対策（ホスト/IP 検査、リダイレクト時検査）
  - レスポンスサイズ制限と gzip 解凍後のチェック
  - 許可されないスキームを拒否（http/https のみ）

### Migration / Notes
- 必須環境変数（未設定時は Settings プロパティで ValueError が発生します）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env の自動読み込みはデフォルトで有効。テストや特殊用途では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- DuckDB スキーマは初期DDLを含みますが、さらに詳細なテーブル（Processed / Feature / Execution 層）は今後追加予定です。
- strategy / execution / monitoring パッケージはエントリポイントを用意していますが、実装はこれからです。

---

今後の予定（例）
- Strategy 実装（アルファ生成・ポートフォリオ構築）
- Execution 層の実装（kabuステーション API 統合・注文ロジック・約定管理）
- Monitoring（Slack 通知周りの実装と稼働監視）
- DuckDB スキーマの拡張（Processed/Feature/Execution 層の完全定義）
- テストカバレッジ拡充（ユニット・統合テスト）

---

参照: Keep a Changelog — https://keepachangelog.com/en/1.0.0/