CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

未リリースの変更については "Unreleased" セクションを使用してください。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-19
-------------------

Added
-----
- 初期公開: KabuSys v0.1.0 を追加。
  - パッケージ公開のためのトップレベル初期化を追加（src/kabusys/__init__.py）。
  - モジュール構成を整理: data, strategy, execution, monitoring 等を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git / pyproject.toml を使用）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定時のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
  - export KEY=val 形式や引用符付き値（バックスラッシュエスケープ対応）、行内コメントの処理に対応する .env パーサを実装。
  - Settings クラスを提供し、必須環境変数の検査（_require）・デフォルト値・バリデーション（KABUSYS_ENV / LOG_LEVEL）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - rate limiter（120 req/min）を実装（固定間隔スロットリング）。
  - 汎用 HTTP 呼び出しユーティリティ (_request) を実装。ページネーション対応。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。
  - 401 発生時の自動トークンリフレッシュとリトライ（1 回のみ）を実装。ID トークンのモジュールキャッシュを保持。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装（ページネーション対応）。
  - DuckDB 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar を実装。fetched_at を UTC ISO 形式で記録し、ON CONFLICT DO UPDATE による冪等保存を実現。
  - 型変換ユーティリティ _to_float / _to_int を実装（不正値・空値を安全に None に変換）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集パイプラインを実装: フェッチ → 前処理 → raw_news への保存 → 銘柄紐付け。
  - セキュリティ対策:
    - defusedxml を利用して XML 攻撃を防御。
    - SSRF 対策: リダイレクト時のスキーム・ホスト検査、事前ホスト検証、プライベートアドレスへのアクセス拒否。
    - URL スキームの検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - URL 正規化（tracking params 削除、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
  - テキスト前処理（URL 除去・空白正規化）。
  - 銘柄コード抽出（4桁コードの正規表現、known_codes によるフィルタ）。
  - DB 保存はチャンク化＆トランザクション化して INSERT ... RETURNING を利用し、実際に挿入された件数/ID を返す。

- 研究（Research）モジュール（src/kabusys/research/）
  - ファクター探索・計算モジュールを実装:
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: DuckDB の prices_daily を参照して各ホライズンの将来リターンを単一クエリで取得。
      - calc_ic: ランク相関（Spearman ρ）を計算（ランク算出は同順位を平均ランクで処理）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
      - rank: 値をランクに変換（丸めによる ties 検出改善）。
      - 設計方針として標準ライブラリのみを使用（pandas 等に依存しない）。
    - src/kabusys/research/factor_research.py
      - calc_momentum: mom_1m/mom_3m/mom_6m および 200 日移動平均乖離 ma200_dev を計算。
      - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials と当日の価格を組み合わせて PER / ROE を計算（最新財務レコードの取得は ROW_NUMBER による）。
      - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照。取引 API にはアクセスしない設計。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw 層テーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む）。
  - DataSchema に基づいた 3 層（Raw / Processed / Feature）を想定した初期スキーマ設計。

Changed
-------
- 初期リリースのため特定の「変更」はなし（初回実装）。

Security
--------
- RSS パーサで defusedxml を利用して XML 攻撃を低減。
- news_collector における SSRF 対策（リダイレクト検査、プライベートアドレス拒否、スキーム検証）。
- .env 読み込みで OS 環境変数を protected として上書きを防止する挙動を実装。

Performance
-----------
- J-Quants API 呼び出しで固定間隔のレート制御を実装し API 制限に適合。
- fetch_* 系でページネーションをループして安全に収集。
- DuckDB への保存はバルク executemany / チャンク挿入 / ON CONFLICT を活用して効率化。
- news_collector の INSERT はチャンクングと単一トランザクションで実行しオーバーヘッドを削減。

Notes / Implementation details
------------------------------
- research モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB を用いた SQL + 純 Python で計算する設計。
- 日付スキャン範囲は「営業日 ≒ 連続レコード数」を前提にカレンダー日数にバッファを掛けている（週末・祝日吸収のため）。
- 各保存関数は PK 欠損行のスキップログを出力し、挿入件数を返すことで呼び出し側で処理状況を把握しやすくしている。
- ロギング（logger.debug/info/warning/exception）を多用して処理の可観測性を確保。

Deprecated
----------
- なし

Removed
-------
- なし

References
----------
- このリリースのソースコードは src/ 以下に配置されています（主要ファイルは上記の通り）。