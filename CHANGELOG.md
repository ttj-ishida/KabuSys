CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
-----------

（無し）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
- パッケージエントリポイント:
  - src/kabusys/__init__.py にてバージョン定義と公開モジュール一覧を追加。
- 設定/環境変数管理 (src/kabusys/config.py):
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサはコメント行、export プレフィックス、クォートおよびエスケープ、インラインコメント等に対応。
  - Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パスなど主要設定プロパティ（必須チェック・デフォルト値・妥当性検証）を実装。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックおよび is_live/is_paper/is_dev ヘルパーを提供。

- データ取得クライアント (src/kabusys/data/jquants_client.py):
  - J-Quants API クライアントを実装。fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar を提供（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min 相当を遵守する RateLimiter 実装。
  - リトライ: 指数バックオフによるリトライ（最大 3 回）、408/429/5xx を対象。429 の Retry-After ヘッダ優先。
  - 認証: refresh_token から id_token を取得する get_id_token、401 受信時は自動でトークンリフレッシュして 1 回リトライ。
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - fetched_at を UTC ISO 形式で記録。
    - PK 欠損行はスキップしログ警告。
    - 冪等 (ON CONFLICT DO UPDATE) による重複排除。
  - 入出力変換ユーティリティ _to_float / _to_int：不正値や空値は None にし、float 文字列の int 変換の取り扱いに注意。

- ニュース収集 (src/kabusys/data/news_collector.py):
  - RSS フィード取得・正規化・DB 保存ワークフローを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に配慮）。
    - SSRF 対策: リダイレクト先スキーム検証、プライベートアドレス判定（DNS 解決を含む）を行い内部ネットワークへの到達を防止。
    - URL スキーム制限 (http/https のみ)。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のチェックを実装（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_ 等）を除去し、ソート／フラグメント削除。記事ID は正規化 URL の SHA-256（先頭32文字）。
  - テキスト前処理: URL 除去と空白正規化。
  - DB 保存:
    - raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id で新規挿入 ID を取得。
    - news_symbols の紐付けは一括チャンク INSERT（ON CONFLICT DO NOTHING）で保存。トランザクションでロールバック対応。
  - 銘柄抽出ユーティリティ extract_stock_codes: 4桁の数字パターンを抽出し、known_codes でフィルタして重複除去。

- リサーチ・ファクター計算 (src/kabusys/research/*.py):
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを DuckDB の prices_daily からまとめて取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランクを採用。丸め誤差対策に round(v,12) を使用。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を標準ライブラリのみで計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。必要データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、atr_pct、20日平均売買代金、出来高比率などを計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から最新の財務データ（report_date <= target_date）を取得して PER/ROE を算出（EPS=0/欠損時は None）。
  - いずれも DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API にアクセスしない設計）。

- スキーマ定義 (src/kabusys/data/schema.py):
  - DuckDB 用の基本スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む）。
  - Raw / Processed / Feature / Execution 層の概念に基づいてテーブルを整理。

Security
- news_collector と jquants_client において外部入力・HTTP の取り扱いに対するセキュリティ考慮（SSRF/サイズ上限/defusedxml/認証リフレッシュ）を実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Notes / Implementation details
- 仕様上、research モジュールは本番取引や外部発注 API にはアクセスしないことを明示（安全設計）。
- .env のパースはシェル風の export やクォート・エスケープに対応しており、テスト・配布後の挙動を考慮して __file__ からプロジェクトルートを探索する実装。
- DuckDB への書き込みは冪等性を優先（ON CONFLICT）し、トランザクション管理でデータ整合性を担保。

Acknowledgements
- 初期機能群はデータ収集（J-Quants / RSS）、DuckDB スキーマ、ファクター計算、設定管理、及びセキュリティ対策を中心に実装しています。今後、strategy / execution / monitoring 等の上位レイヤー実装やテスト・ドキュメントの追加を予定しています。