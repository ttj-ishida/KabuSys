# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

- リリース日付はコード内バージョン／実装から推測して設定しています。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買・データパイプライン基盤の最小実装を追加します。主な追加点と実装の要旨は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定管理
  - 環境変数・.env 管理モジュール（src/kabusys/config.py）を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）による .env/.env.local の自動読み込み。
    - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - .env.local を .env 上に上書きする挙動、OS 環境変数を保護する仕組み、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 必須環境変数取得ヘルパ _require と Settings クラスを実装（J-Quants/Slack/DB パス/ログレベル/環境種別などのプロパティ）。

- Data 層（DuckDB）関連
  - スキーマ定義モジュール（src/kabusys/data/schema.py）を追加（Raw 層テーブル定義の DDL を実装）。
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義（制約・型・PK）を含む。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
    - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - リトライロジックを実装（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）。
    - 401 時の自動トークンリフレッシュ（1 回のみ）をサポート。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements（pagination_key を追跡）。
    - fetch_market_calendar（JPX カレンダー）取得機能。
    - DuckDB への冪等保存関数 save_daily_quotes/save_financial_statements/save_market_calendar を実装（INSERT ... ON CONFLICT DO UPDATE）。
    - 値変換ユーティリティ _to_float / _to_int を追加して堅牢なデータ型変換を実現。
    - fetched_at を UTC ISO 形式で記録し、Look-ahead bias トレーサビリティを確保。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加（RSS ベースのニュース収集）。
    - RSS 取得（fetch_rss）、XML パース（defusedxml を使用）および前処理機能を実装。
    - セキュリティ対策：
      - URL スキーム検証（http/https のみ許可）。
      - SSRF 対策（リダイレクト先の事前検証、プライベートIP/ループバックの拒否）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と、SHA-256 ベースの記事 ID 生成（先頭32文字）。
    - テキスト前処理（URL除去・空白正規化）、RFC 2822 形式の pubDate 解析（UTC に正規化）。
    - DB への冪等保存：
      - save_raw_news：チャンク化＋トランザクション＋INSERT ... ON CONFLICT DO NOTHING RETURNING id で新規挿入 ID を返す。
      - save_news_symbols / _save_news_symbols_bulk：news_symbols への紐付けをチャンク単位で保存、重複除去。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁コードパターン、既知コードセットによるフィルタ）。
    - run_news_collection：複数 RSS ソースの統合収集ジョブ（個別ソースのエラーハンドリング、既知銘柄の紐付け）。

- リサーチ機能（特徴量探索・ファクター）
  - src/kabusys/research/feature_exploration.py を追加。
    - calc_forward_returns：DuckDB の prices_daily を参照して将来リターン（デフォルト [1,5,21]）を一回のクエリで取得する実装。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算。欠損・有限性チェック、3件未満のときは None を返す。
    - rank：同順位は平均順位を返すランク関数（丸めで ties 検出漏れを抑止）。
    - factor_summary：count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリを実装。
    - 標準ライブラリのみでの実装方針（pandas 等不使用）を採用。

  - src/kabusys/research/factor_research.py を追加。
    - calc_momentum：mom_1m/mom_3m/mom_6m/ma200_dev（200日移動平均乖離）を DuckDB SQL ウィンドウ関数で計算。データ不足時は None。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御によりカウント精度を保持。
    - calc_value：raw_financials から target_date 以前の最新財務を取得して PER（EPS が有効な場合）/ROE を計算。DuckDB 側で最新財務レコードを ROW_NUMBER により選択。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API へアクセスしない設計。

- モジュールのパブリックエクスポート
  - src/kabusys/research/__init__.py にて主要関数（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）を公開。

### 変更 (Changed)
- 設計方針として「本番口座・発注 API には一切アクセスしない」「標準ライブラリでの実装」を明確化。
- DuckDB への保存は原則冪等（ON CONFLICT）とし、fetched_at を付与してデータの取得時点を追跡可能にした。

### 修正 (Fixed)
- .env パーサ:
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント処理などの細かいパーシングを考慮し堅牢化。
- news_collector:
  - 大きすぎる/不正なレスポンスを事前に検出して早期にスキップすることでメモリ DoS を防止。
  - リダイレクト先や最終 URL の検証を追加し SSRF リスクを低減。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連脆弱性（XML bomb 等）に備えた。
- RSS フェッチ時のリダイレクト検査とホストのプライベートアドレス拒否により SSRF を防止。
- API クライアントでのトークン自動リフレッシュ時に無限再帰を防止するフラグ制御（allow_refresh）を実装。

### 既知の制限 / 注意事項
- research モジュールはパフォーマンス改善のために SQL を多用しているが、大規模データでの更なるチューニングや並列化は今後の課題。
- zscore_normalize は kabusys.data.stats で提供される前提（このリリースでの実装位置に依存）。
- news_collector の既知銘柄リスト（known_codes）は外部提供が必要（run_news_collection の抽出に利用）。

---

将来のリリースでは、モジュール間の結合（戦略→実行パス）、発注 API のラッパー、監視（monitoring）用の DB/Slack 通知統合、テストカバレッジ拡充、パフォーマンス最適化などを計画しています。