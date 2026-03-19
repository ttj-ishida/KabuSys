変更履歴
=========
(このファイルは "Keep a Changelog" の形式に準拠しています。)

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。KabuSys パッケージのコア機能を実装しました。
  - パッケージ構成:
    - kabusys.config: 環境変数・設定管理
      - .env / .env.local の自動読み込み機能（OS環境変数を保護しつつ .env.local が上書き可能）
      - 読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応
      - .env パーサーは export プレフィックス、クォート、インラインコメント等に対応
      - 必須変数取得時に未設定なら ValueError を送出する Settings API
      - 許可される環境値（KABUSYS_ENV, LOG_LEVEL）の検証ロジック
      - DB パス設定（DUCKDB_PATH / SQLITE_PATH）を Path 型で提供
  - kabusys.data:
    - jquants_client: J-Quants API クライアント
      - レート制限 (120 req/min) を守る固定間隔スロットリング実装（内部 RateLimiter）
      - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx に対応）
      - 401 受信時にリフレッシュトークンで自動的に ID トークン再取得して1回リトライ
      - ページネーション対応（pagination_key）で全件取得
      - DuckDB への保存用ユーティリティ（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT による冪等保存を行う
      - 型変換ユーティリティ (_to_float / _to_int) による健全なパース処理
    - news_collector: RSS ニュース収集／保存
      - RSS フィード取得（gzip対応、Content-Length/サイズ上限チェック）
      - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）
      - SSRF 対策: リダイレクト先のスキーム検証、プライベート IP/ホストの検出とブロック、カスタム redirect handler を使用
      - 取得記事の前処理（URL 除去、空白正規化）
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
      - raw_news / news_symbols へのチャンク化されたバルク保存（INSERT ... RETURNING を利用し、実際に挿入された件数を返す）
      - テキストから銘柄コード（4桁）を抽出する抽出ロジック（既知コード集合でフィルタ）
      - 公開ソースのデフォルト定義（例: Yahoo Finance のカテゴリRSS）
    - schema: DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層のためのDDLを定義）
      - raw_prices, raw_financials, raw_news 等のテーブル定義を含む（制約・型・PRIMARY KEY を含むDDL）
  - kabusys.research:
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度のクエリで取得、ホライズン検証（1..252）
      - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関を標準ライブラリのみで実装
      - ランク付けユーティリティ（rank）：同順位は平均ランク、丸め誤差に対する対策あり
      - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を計算
    - factor_research:
      - Momentum/Volatility/Value 系ファクター計算関数（calc_momentum / calc_volatility / calc_value）
      - DuckDB 経由で prices_daily / raw_financials テーブルのみ参照する実装
      - 各ファクターはデータ不足時に None を返す設計（ウィンドウ不十分時の保険）
      - パフォーマンス配慮：スキャン範囲にカレンダーバッファを導入（営業日=連続レコードを前提）
    - research パッケージ __all__ に主要ユーティリティをエクスポート（zscore_normalize を含む）
  - パッケージトップ (__init__.py) にバージョン "0.1.0" を設定

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector:
  - defusedxml を用いた XML パースで XML 攻撃を低減
  - HTTP リダイレクト時にスキームと到達先ホストの検査を行い SSRF を防止
  - レスポンスサイズ上限と gzip 解凍後の上限チェックでメモリ DoS を軽減
- jquants_client:
  - 認証フローでトークン自動リフレッシュ時の再帰を防ぐ設計（allow_refresh フラグ）

Performance
- jquants_client:
  - レートリミッタにより API 制限を厳守しつつ安定した取得を実現
  - ページネーションをループで処理し、重複 pagination_key を検出してループ終了
- news_collector:
  - 保存処理はチャンク化し、1 トランザクションでまとめてコミットすることでオーバーヘッドを削減

Notes / Requirements
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
  - これらは settings のプロパティアクセス時に存在しない場合 ValueError を発生させます
- 設定例:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか
- DuckDB のテーブル名（例: prices_daily, raw_financials 等）に依存します。既存の DB を使用する場合はスキーマが整っていることを確認してください。
- research モジュールは pandas 等に依存せず標準ライブラリと DuckDB の SQL のみで実装されています（研究環境での安全性を重視）

Known limitations / Future work
- Strategy / Execution / Monitoring パッケージの詳細実装は未提供（パッケージの骨組みは存在）
- Value ファクターでは PBR・配当利回りは未実装
- news_collector の URL 正規化やコード抽出は単純なルールベース（今後 NLP・辞書拡張の余地あり）
- DB スキーマ定義は一部のみ（raw_executions の定義がファイル末尾で途中切れの状態）。完全な Execution 層の DDL は今後追加予定

Acknowledgements
- 初回リリースノート。利用・テストフィードバックを歓迎します。

(以降バージョンはここに追加してください)