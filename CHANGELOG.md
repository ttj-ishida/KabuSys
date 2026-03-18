# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティック バージョニングに従います。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージの初期リリース
  - src/kabusys/__init__.py にパッケージ名とバージョンを定義（__version__ = "0.1.0"）し、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定の自動読み込みと管理機能を追加（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
  - export KEY=val 形式やクォート付き値、インラインコメントなどに対応する堅牢な .env パーサを実装。
  - OS 環境変数を保護する protected キー機能、.env.local による上書きサポート、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を取得する Settings クラスを提供。KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - 再試行（指数バックオフ）を組み込んだ HTTP 呼び出しロジック。408/429/5xx を対象に最大3回リトライ、429 の場合は Retry-After を優先。
  - 401 受信時にリフレッシュトークンで自動取得（1回のみリトライ）し、ID トークンをモジュール内でキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）を実装。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT による upsert を使用。
  - 数値変換ユーティリティ（_to_float、_to_int）を追加し、入力の堅牢性を向上。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードの取得・パース・前処理・ID 生成・DuckDB への冪等保存ワークフローを実装。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - トラッキングパラメータ（utm_*, fbclid 等）の削除、クエリソート、フラグメント削除による URL 正規化を実装。
  - SSRF 対策を強化：http/https スキーム検証、ホストがプライベート/ループバックでないことの検査、リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）、最終 URL の再検証。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェックを実装（Gzip bomb 対策）。
  - defusedxml を使用した XML パース（XML Bomb 等対策）、不正フィードの安全なスキップ処理。
  - raw_news へのチャンク挿入（INSERT ... RETURNING）とトランザクション制御、news_symbols への銘柄紐付けの一括挿入機能を実装（チャンク処理、ON CONFLICT DO NOTHING）。
  - テキスト前処理（URL 除去、空白正規化）と記事内からの 4 桁銘柄コード抽出ユーティリティ（extract_stock_codes）を実装。
  - デフォルト RSS ソース（yahoo_finance）を定義。
- DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）
  - Raw layer のテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
- リサーチ/ファクター計算モジュールを追加（src/kabusys/research/*）
  - ファクター探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、factor_summary を実装。
    - DuckDB の prices_daily テーブルを想定した実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - ファクター計算（factor_research.py）
    - Momentum、Volatility、Value の各ファクター計算関数を実装（calc_momentum、calc_volatility、calc_value）。
    - 各関数は prices_daily / raw_financials テーブルを参照し、(date, code) をキーとする dict リストを返す。
  - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize を含む）。

### 変更 (Changed)
- なし（初回リリースのため既存の変更履歴はありません）

### 修正 (Fixed)
- データパース・変換に関する堅牢性向上
  - .env のパースにおけるクォート・エスケープ・コメント処理を改善。
  - fetch/save 系で主キー欠損行をスキップしログ出力することで不正行による例外を回避（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - RSS 日時パースに失敗した場合は警告ログを出し現在時刻で代替するようにして raw_news.datetime の NOT NULL 制約に対応。
  - 株価・指標計算関数でデータ不足（十分な窓がない等）の際は None を返すようにして downstream の安全性を確保（例: ma200_dev, atr_20 の cnt チェック等）。
  - calc_forward_returns の horizons 引数に対する入力検証（正の整数かつ <=252）を追加。

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 関連攻撃を軽減。
- HTTP 操作における SSRF 対策を導入（スキーム検証、プライベートIP/ホスト拒否、リダイレクト検査）。
- 外部から読み込む .env の読み取りはファイル読み込み例外をキャッチして警告を出すようにして安全性を向上。

### 既知の制限・注意点 (Known limitations / Notes)
- research モジュールは DuckDB の prices_daily / raw_financials 等のテーブル前提で実行されるため、事前にスキーマ初期化とデータ投入が必要です。
- jquants_client の _BASE_URL は固定値（https://api.jquants.com/v1）になっています。必要に応じてモックや設定で差し替えてください。
- news_collector の既定 RSS ソースは少数に留めているため、運用時は sources 引数で拡張してください。
- 一部テーブル定義（raw_executions など）の DDL は継続的に拡張される想定です。

---

今後のリリースでは以下の点を予定しています:
- Execution / strategy の具象実装（発注ロジック・バックテスト等）
- Feature layer / Execution layer の更なるスキーマ整備と移管処理
- テストカバレッジ拡充と CI 統合

（必要であれば、各ファイルごとのより詳細な変更点・設計意図を別途ドキュメント化します）