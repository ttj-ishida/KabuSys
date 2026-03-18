# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

リリース日: 2026-03-18

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要機能とモジュールを追加しました。

### 追加 (Added)
- 基本パッケージ
  - パッケージ定義とバージョン: kabusys v0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み自動化:
    - プロジェクトルート検出: .git または pyproject.toml を起点に自動探索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動読み込み停止用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - 無効行のスキップやエラーハンドリングを実装。
  - Settings クラスを提供し、型付けされたプロパティ経由で設定取得:
    - J-Quants / kabu API / Slack / DB パス（DuckDB・SQLite）/ 環境種別・ログレベルの検証。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の入力検証。

- Data 層 (src/kabusys/data)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しユーティリティ:
      - 固定間隔スロットリングによるレート制御（120 req/min）。
      - リトライ（指数バックオフ、最大3回）および 408/429/5xx 処理。
      - 401 発生時の ID トークン自動リフレッシュ（1回のみ）とトークンキャッシュ。
      - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - データ保存ユーティリティ:
      - DuckDB への冪等保存（ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
      - 型変換ヘルパー: _to_float, _to_int（文字列からの堅牢な変換ルール）。
    - Look-ahead bias 対策として fetched_at を UTC で記録。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィード収集パイプライン:
      - RSS フェッチ（fetch_rss）、前処理（URL 除去・空白正規化）、記事ID 生成（正規化 URL の SHA-256 先頭32文字）。
      - defusedxml を用いた安全な XML パース。
      - gzip 圧縮対応・レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）による DoS 対策。
      - SSRF 対策:
        - URL スキーム検証（http/https のみ許可）。
        - リダイレクト時にホストを検査するカスタムリダイレクトハンドラ（プライベートアドレス拒否）。
        - 初回 URL と最終 URL の両方でプライベートホスト検査。
      - トラッキングパラメータ（utm_* 等）除去と URL 正規化。
      - 記事データの DuckDB への冪等保存:
        - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id を用い新規挿入 ID を正確に取得。チャンク & トランザクション対応。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT スキップ、チャンク化）。
      - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字マッチ + known_codes に基づくフィルタ）。
      - run_news_collection: 複数ソースの独立した取得処理、エラー耐性、既知銘柄による紐付けの一括処理。
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを登録。

  - DuckDB スキーマ初期化（src/kabusys/data/schema.py）
    - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む／一部列定義掲載）。
    - 各テーブルに対する制約（PRIMARY KEY, CHECK 等）を含む DDL を用意。

- Research 層 (src/kabusys/research)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、単一クエリで取得）。
    - IC（Information Coefficient）計算: calc_ic（スピアマン順位相関、欠損値・非有限値の除外、最小レコード数チェック）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めによる ties 考慮）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median、None の除外）。
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部 API へはアクセスしない、標準ライブラリのみで実装。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタムファクター: calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足時は None）。
    - ボラティリティ／流動性: calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）。
    - バリューファクター: calc_value（raw_financials から直近財務を取得し PER/ROE を計算）。
    - スキャン範囲最適化（カレンダーバッファ）やウィンドウ集約を SQL 内で実装。
  - research パッケージの __init__ で代表的ユーティリティを再公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS フィード取得に対する SSRF 緩和策を実装（スキーム検証、プライベート IP/ホスト検査、リダイレクトガード）。
- XML パースに defusedxml を使用し XML Bomb 等に対する防御を追加。
- ニュース取得でのレスポンス上限と gzip 解凍後のサイズチェックによりリソース枯渇攻撃を軽減。

---

注意:
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily/raw_* テーブルを前提として動作します。実行前にスキーマ初期化と DB 接続の準備が必要です。
- 外部通信を行う箇所（J-Quants, RSS）ではネットワーク例外や API エラーが発生する可能性があります。適切なログ／再試行ポリシーの採用を推奨します。
- 今後のリリースでは strategy / execution / monitoring の具体的な実装や、Schema の完全定義（Processed / Feature / Execution レイヤ）を追加予定です。