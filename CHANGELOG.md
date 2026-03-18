CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に準拠して記載しています。
詳細: https://keepachangelog.com/ja/

[未リリース]
------------

- （該当なし）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初回リリース。パッケージ名: kabusys、__version__ = 0.1.0。
- パッケージ構成を追加:
  - kabusys.config: 環境変数 / .env 管理（自動ロード機能を含む）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - .env パーサ実装: export KEY=val 形式・クォート付き値（バックスラッシュエスケープ対応）・インラインコメントの扱いを考慮。
    - override / protected 機能により OS 環境変数を保護しつつ .env.local で上書き可能。
    - 必須設定取得用 _require と Settings クラスを提供（J-Quants トークン、Kabu API パスワード、Slack 設定、DBパス等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値を限定）。
  - データ取得・保存 (kabusys.data):
    - jquants_client:
      - J-Quants API クライアント（prices / financials / trading_calendar）。
      - 固定間隔レートリミット（120 req/min）を実装する RateLimiter を採用。
      - 再試行（指数バックオフ、最大3回）と 401 の自動トークンリフレッシュ処理を実装。
      - ページネーション対応の fetch_* 関数と、DuckDB への冪等保存関数 save_*（ON CONFLICT DO UPDATE）を実装。
      - 型変換ユーティリティ (_to_float/_to_int) を追加し入力データの堅牢性を確保。
    - news_collector:
      - RSS フィード収集と raw_news / news_symbols 保存の実装。
      - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事ID生成（正規化URL の SHA-256 先頭32文字）で冪等性を確保。
      - defusedxml による XML パースで XML 脅威を軽減。
      - SSRF 対策: リダイレクト時のスキーム検査、ホストのプライベートアドレス検査、初期ホスト検査を実装。
      - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10 MB）や gzip 解凍後サイズ検査（Gzip bomb 対策）。
      - コンテンツ前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）。
      - バルク挿入はチャンク化してトランザクション内で実行、INSERT ... RETURNING による新規挿入数取得。
    - schema:
      - DuckDB スキーマ定義（Raw Layer など）の DDL を用意（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義）。
  - research モジュール (kabusys.research):
    - feature_exploration:
      - calc_forward_returns: 指定日の終値から将来リターン（デフォルト: 1/5/21 営業日）を計算するクエリを提供。ホライズン検証・結果の None ハンドリングなど。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。欠損・finite チェック、最小レコード数チェック（3未満は None）。
      - rank: 同順位は平均ランクで扱うランク化実装（丸め誤差対策で round(v,12) を利用）。
      - factor_summary: 複数ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を DuckDB 上の Window 関数で計算（データ不足時は None）。
      - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比を計算。true_range の NULL 伝播を適切に扱う実装。
      - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算（EPS が 0/欠損時は None）。
    - 研究用 API は DuckDB 内の prices_daily / raw_financials テーブルのみ参照、外部発注 API にはアクセスしない設計。
  - パッケージの __all__ に主要サブモジュールを追加（data, strategy, execution, monitoring, research のエクスポート）。

Security
- news_collector: defusedxml, SSRF対策、ホストプライベート判定、Content-Length/受信サイズ上限、gzip 解凍後サイズ検査で外部入力の安全性を強化。
- jquants_client: API トークンの自動リフレッシュは allow_refresh フラグで無限再帰を防止。
- config: OS 環境変数は protected として .env により不用意に上書きされないよう保護。

Changed
- 初版リリースのため、変更履歴は追加のみ。

Fixed
- 初版リリースのため、修正項目は無し。

Notes / Implementation details
- DuckDB 接続は関数に渡す形式で外部接続を利用する設計（副作用を限定）。
- 多くの処理は SQL のウィンドウ関数で実装しており、データ量が大きい環境でのパフォーマンスを想定。
- 設定値に対して厳密な検証（env / log level）を行い、不正な実行モードの誤設定を早期に検出する。
- News の記事ID/URL 正規化により重複挿入を抑止、tracking パラメータ削除で同一記事の正規化を強化。

開発者向け / 互換性
- このリリースは初版（0.1.0）であり、公開 API（関数名・戻り値フォーマット）は今後のリリースで変更される可能性があります。内部関数を直接呼ぶより、公開されたモジュール API を通じて利用してください。

関連ファイル
- 主要実装ファイル: src/kabusys/config.py, src/kabusys/data/jquants_client.py, src/kabusys/data/news_collector.py, src/kabusys/data/schema.py, src/kabusys/research/factor_research.py, src/kabusys/research/feature_exploration.py, src/kabusys/research/__init__.py, src/kabusys/__init__.py

もし CHANGELOG に追記したい注記や抜けがあれば、その点を教えてください。