CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
このプロジェクトではセマンティックバージョニングを採用しています。  

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
-----------------

Added
- 基本パッケージ構成を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール一覧: data, strategy, execution, monitoring
  - strategy、execution パッケージの初期化ファイルを追加（プレースホルダ）

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの自動検出は .git または pyproject.toml を基準に行う（__file__ ベースで探索）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーの実装
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポート
    - インラインコメント判定（クォート無しの場合は '#' の直前が空白/タブならコメントとみなす）
    - 無効行はスキップし、読み込みエラーは警告ログとして扱う
  - Settings クラスを提供して設定値をプロパティ経由で取得
    - J-Quants / kabuステーション / Slack / DB パス等の必須/任意設定をラップ
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証
    - duckdb/sqlite のデフォルトパスを提供

- データ取得・永続化（kabusys.data）
  - J-Quants クライアント（data/jquants_client.py）
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）
    - リトライロジック（指数バックオフ、最大3回）を実装。対象はネットワークエラーや 408/429/5xx
    - 401 発生時はリフレッシュトークンから id_token を再取得して 1 回だけリトライする処理を実装
    - ページネーション対応の fetch_* 関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
    - DuckDB への保存用関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）
      - ON CONFLICT DO UPDATE による冪等保存
      - PK 欠損行をスキップして警告ログを出力
    - 型変換ユーティリティ (_to_float/_to_int) を実装し、柔軟かつ安全に数値変換を行う
  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィード取得・パース機能を実装
      - defusedxml を用いた安全な XML パース（XML Bomb 対策）
      - gzip 圧縮対応・受信サイズ上限（MAX_RESPONSE_BYTES=10MB）でメモリDoSを防止
      - リダイレクト時にスキームとホストの検証を行うカスタムハンドラ（SSRF 対策）
      - URL スキーム検証、プライベートアドレス（ループバック/プライベート/リンクローカル等）検査
      - コンテンツ長ヘッダチェックと読み込み後サイズチェックの二重防御
      - title/description (content:encoded) の前処理（URL 除去、空白正規化）
      - 記事IDは URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保
    - DB 保存処理
      - raw_news に対するチャンク挿入 + INSERT ... RETURNING により実際に挿入された記事IDを返す
      - トランザクションを用い、失敗時にはロールバックして例外を再送出
      - news_symbols（記事と銘柄コードの紐付け）を一括挿入する内部ユーティリティ（重複排除・チャンク処理）
    - 銘柄抽出ユーティリティ
      - テキストから4桁の銘柄コードを抽出し、与えられた known_codes に含まれるもののみを返す
  - DuckDB スキーマ定義（data/schema.py）
    - Raw レイヤの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の雛形を含む）
    - データ保存に適した型定義・チェック制約・主キーを明示

- リサーチ / 特徴量探索（kabusys.research）
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から将来リターン（例: 1日/5日/21日）を DuckDB の prices_daily を参照して一括計算
      - ホライズン検証（正の整数かつ <= 252）
      - LEAD ウィンドウを用いた1クエリ取得、スキャン範囲のバッファリングによる効率化
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（同順位は平均ランク）
      - 有効レコードが3未満の場合は None を返す
      - NaN/無限大を除外
    - rank: 同順位は平均ランクを採用し、丸め誤差対策に round(..., 12) を用いる
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算
      - 過去取得レンジにバッファを設け、ウィンドウ内のデータ不足時は None を返す
    - calc_volatility: atr_20（20日ATR平均）/atr_pct/avg_turnover/volume_ratio を計算
      - true_range の NULL 伝播を慎重に扱い、部分窓でも正確にカウント
    - calc_value: raw_financials の最新財務（target_date以前）と prices_daily を組み合わせて per/roe を算出
  - research パッケージ __all__ に主要ユーティリティを公開（calc_momentum 等と zscore_normalize の再公開）

Changed
- （初回リリースのため特になし）

Fixed
- データ取り込み時の PK 欠損行をスキップし警告ログを出すようにして不整合突入を防止（jquants_client / news_collector）
- RSS の日付パース失敗時に現在時刻で代替し NULL を回避（raw_news.datetime は NOT NULL のため）

Security
- RSS 収集に関する SSRF 対策を多数実施（スキーム検査、プライベートIP検査、リダイレクト検査）
- XML パースに defusedxml を利用
- API クライアントでの認証トークン自動リフレッシュは再帰を防ぐ制御を追加（allow_refresh フラグ）

Deprecated
- （なし）

Removed
- （なし）

Notes / Known limitations
- research モジュールは標準ライブラリのみで実装されており、pandas 等の高速処理ライブラリには依存していません。大規模データでのパフォーマンス改善は今後の課題です。
- data/schema.py の raw_executions 定義はファイル終端で切れている（現時点で部分的に定義済み）。実運用前に Execution レイヤの完全なスキーマ定義が必要です。
- strategy / execution の具象実装（発注ロジック、モニタリング）はこのバージョンでは未実装・プレースホルダの段階です。

今後の予定（次バージョンで予定）
- Execution レイヤのスキーマ完成と kabuステーション連携の実装
- Strategy の実装とバックテスト基盤の統合
- 大規模データ処理のためのパフォーマンス最適化（DuckDB クエリ・バッチ処理改善、可能なら pandas/numba の導入検討）
- 追加のニュースソース/言語対応と NLP 前処理強化

以上。