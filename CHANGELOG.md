# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-19
初期リリース

### 追加 (Added)
- パッケージ初期構成
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を追加。
  - strategy/ と execution/ パッケージのプレースホルダを追加（実装は今後）。

- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env の行パーサは export KEY=val 形式、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - override と protected パラメータにより OS 環境変数を保護して上書きを制御。
    - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、実行環境・ログレベル検証等のプロパティ）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値セット）を実装。is_live / is_paper / is_dev のユーティリティ。

- J-Quants データ取得クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しユーティリティ（HTTP request ラッパー）を実装。
    - レート制限機構: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter。
    - 再試行ロジック: 指数バックオフ、最大試行回数 3、408/429/5xx をリトライ対象。
    - 401 Unauthorized 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライ。
    - ページネーション対応とモジュール内トークンキャッシュ（ページ間でトークン共有）。
    - データ取得関数:
      - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
      - fetch_financial_statements: 財務データ（四半期）をページネーション対応で取得。
      - fetch_market_calendar: JPX マーケットカレンダーを取得。
    - DuckDB 保存ユーティリティ:
      - save_daily_quotes / save_financial_statements / save_market_calendar: fetched_at を UTC ISO 形式で記録、ON CONFLICT DO UPDATE による冪等保存。
    - 型変換ユーティリティ: _to_float / _to_int（文字列→数値の堅牢変換。小数文字列からの int 変換では小数部が非ゼロなら None を返す等の方針を明示）。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィード取得 → 前処理 → DuckDB への冪等保存ワークフローを実装。
    - セキュリティ対策:
      - defusedxml を用いて XML 関連攻撃を軽減。
      - SSRF 対策: リダイレクト時にスキームとホスト/IP を検証するカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば接続を拒否。
      - 許可スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL 正規化と記事ID生成:
      - _normalize_url によりトラッキングパラメータ（utm_* 等）削除、クエリソート、フラグメント削除等を行う。
      - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字を使用し冪等性を担保。
    - テキスト前処理: URL 削除、空白正規化。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用い、チャンク分割して 1 トランザクションで挿入。実際に挿入された記事 ID を返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク挿入・RETURNING で正確に集計。
    - 銘柄コード抽出: テキスト内の4桁数字を候補とし、既知銘柄セット known_codes との照合で有効コードを抽出（重複除去）。
    - run_news_collection: デフォルトソース（Yahoo Finance のビジネス RSS）を用いた統合収集ジョブ。各ソースは独立して例外処理。

- Research（特徴量／ファクター計算）
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: LEAD を使って指定日から指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。SQL 範囲は max_horizon×2 日のバッファで限定。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。None や非有限値を除去し、有効レコード数 < 3 の場合は None を返す。rank は同順位時に平均ランクを採る実装。
    - factor_summary: count/mean/std/min/max/median を計算。None や非数値を除外。
    - rank: 値を round(v, 12) して同順位検出の丸め誤差を抑え、平均ランクを返す。
  - src/kabusys/research/factor_research.py
    - calc_momentum:
      - mom_1m/mom_3m/mom_6m（営業日ベース: LAG を利用）、ma200_dev（200日移動平均乖離）を計算。
      - データ不足（行数不足やゼロ除算）時は None を返す。
      - スキャン範囲に余裕をもたせるためのカレンダーバッファを適用。
    - calc_volatility:
      - atr_20（20日 ATR の単純平均）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高/20日平均出来高）を計算。
      - true_range は high/low/prev_close が NULL の場合は NULL とすることでカウントを正確に評価。
    - calc_value:
      - raw_financials から target_date 以前の最新財務データを取得して PER（price / eps）と ROE を算出（EPS が 0 または NULL の場合は None）。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API へはアクセスしない、冪等かつローカル分析向け）。
  - src/kabusys/research/__init__.py に主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize の再エクスポート。

- スキーマ定義（DuckDB）
  - src/kabusys/data/schema.py
    - Raw Layer の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の雛形）。主キー・CHECK 制約を含む堅牢な型定義。
    - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution 層）設計を想定。

### 変更 (Changed)
- （初版のため過去の変更はなし）

### 修正 (Fixed)
- （初版のため過去の修正はなし）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用、SSRF/リダイレクト先検証、レスポンス・サイズ検査、gzip 解凍後の上限チェック等を実装し、外部入力による攻撃リスクを低減。

### 既知の制限・今後の作業 (Known issues / TODO)
- strategy/ および execution/ パッケージはプレースホルダのみ（まだ具体的な取引ロジックや発注処理は実装されていません）。
- DuckDB 以外の DB バックエンドは未対応（現在は duckdb 依存）。
- feature / factor の計算は pandas 等の外部ライブラリに依存しない純 Python + SQL 実装だが、大規模データでの性能評価・最適化は今後の課題。
- NewsCollector のデフォルトソースは限定的（DEFAULT_RSS_SOURCES）。追加のフィード管理やスクレイピング対応は今後検討。

---

（このファイルはプロジェクトの開発履歴を人間可読に保つために維持してください。機能追加や API 変更のたびに新しいバージョンセクションを追加してください。）