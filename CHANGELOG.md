Changelog
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
安定版リリースについてはセマンティックバージョニングを使用します。

[Unreleased]
-------------

- (なし)

[0.1.0] - 2026-03-18
--------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を追加しました。

Added
- パッケージ基盤
  - パッケージ初期化: src/kabusys/__init__.py にてバージョン ("0.1.0") と公開 API(__all__) を定義。
- 設定管理
  - 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。
    - .env ファイル行パーサ（export 形式やクォート、行内コメントの扱いに対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 必須環境変数取得時に ValueError を投げる _require ヘルパー。
    - KABUSYS_ENV や LOG_LEVEL の検証（許容値チェック）と利便性プロパティ（is_live 等）。
- データ取得/保存（J-Quants）
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - API レート制限を守る固定間隔レートリミッタ実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx 対象）。
    - 401 発生時はトークンを自動リフレッシュして 1 回リトライする仕組み。
    - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
      - INSERT ... ON CONFLICT DO UPDATE による更新で冪等性を確保。
    - データ型変換ヘルパー（_to_float / _to_int）を実装し不正データに寛容に対応。
    - fetched_at を UTC タイムスタンプで記録し Look-ahead Bias の追跡を可能に。
- ニュース収集（RSS）
  - ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得と記事パース（defusedxml を利用し XML Bomb 等の防御）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - SSRF 対策:
      - fetch 前のホスト検証、リダイレクト時のスキーム/プライベートアドレス検査用ハンドラ(_SSRFBlockRedirectHandler) を実装。
      - URL スキーム検証（http/https のみ）。
      - プライベート/ループバック/リンクローカルの検出機構（IP/DNS 両面で評価）。
    - メモリ DoS 対策:
      - MAX_RESPONSE_BYTES による受信バイト上限（既定 10 MB）。
      - gzip 圧縮対応・解凍後サイズ再チェック（Gzip bomb 対策）。
    - テキスト前処理ユーティリティ（URL除去・空白正規化）。
    - DuckDB への保存:
      - save_raw_news: チャンク単位挿入、INSERT ... RETURNING で実際に挿入された記事IDを返す。トランザクションまとめて実行。
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けを一括で保存。ON CONFLICT により重複をスキップし実際に保存された件数を返す。
    - 銘柄抽出ロジック（4桁数字パターン）と既知コードセットによるフィルタリング実装。
    - デフォルトの RSS ソースに Yahoo Finance のカテゴリフィードを登録。
- 研究（Research）モジュール
  - 特徴量探索とファクター計算を追加（src/kabusys/research/*）。
    - feature_exploration.py:
      - calc_forward_returns: 指定日から各ホライズン（営業日）先までの将来リターンを一括SQLで取得。
      - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。データ不足時は None を返す。ties（同順位）に対応。
      - rank: 同順位は平均ランクを与えるランク付け関数（丸め誤差対策あり）。
      - factor_summary: count/mean/std/min/max/median を計算する基本統計量ユーティリティ。
    - factor_research.py:
      - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率（ma200_dev）を計算。データ不足（MA200 未満等）は None。
      - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
      - calc_value: raw_financials から最新の財務情報を結合して PER（eps が 0/欠損時は None）と ROE を計算。
    - すべての関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照（外部 API にアクセスしない設計）。
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats 由来）や上記関数を公開。
- データスキーマ
  - DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw レイヤー用テーブル定義例（raw_prices, raw_financials, raw_news, raw_executions の DDL を準備）。
    - 初期化・DDL 管理の基礎を実装（DDL テキストはファイル内で定義）。
- その他ユーティリティ
  - 多数のログ出力を追加し操作の可視化とデバッグを助ける（logger を各モジュールで使用）。

Security
- ニュース収集における SSRF 対策、XML パーサに defusedxml を利用、受信サイズ制限・gzip 解凍後チェック等の対策を実装。
- J-Quants クライアントはトークン自動更新やリトライ制御を備え、異常時の情報漏えいや不安定挙動を低減。

Performance
- DuckDB 側でウィンドウ関数を活用し多くの集計を SQL 側で行うことでパフォーマンスを意識。
- fetch_* のページネーションでトークンキャッシュとレートリミッタを共有し効率的な API 呼び出しを実現。
- news_collector のバルク挿入はチャンク化してトランザクションをまとめ、オーバーヘッドを低減。

Notes / Known limitations
- 外部依存は最小限に抑えられているが、duckdb と defusedxml は必要。
- 一部の DDL（raw_executions の続きなど）はファイル提供分で途中までの定義になっているため、実運用前にスキーマ全体を確認してください。
- calc_forward_returns 等は「営業日数」をホライズンとして想定しており、scan 範囲のバッファは週末/祝日を考慮した簡易的な設計になっています。極端な取引カレンダー差分は要確認。

Authors
- KabuSys 開発チーム

References
- 各モジュールの詳細は src/kabusys 以下のソースコードを参照してください。