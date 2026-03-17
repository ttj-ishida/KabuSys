# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

全ての変更はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期リリースを追加。
  - パッケージ名: KabuSys（日本株自動売買システム）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは環境変数から設定をロードする自動ロード機能を提供。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動検出（CWD非依存）。
  - .env パースの実装:
    - コメント行、export プレフィックス、シングル/ダブルクォートやエスケープを正しく処理。
    - クォートなし値でのインラインコメント認識（直前が空白/タブ時）。
  - 自動ロードの切り替え: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを提供（属性アクセスで必須項目を取得、未設定時は例外）。
  - 各種設定をプロパティで提供（J-Quants, kabuAPI, Slack, DBパス, 環境/ログレベル判定等）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 取得対象: 株価日足（OHLCV）、財務データ（四半期BS/PL）、マーケットカレンダー。
  - レート制御実装: 固定間隔スロットリングで 120 req/min を厳守（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大再試行回数 3 回、408/429/5xx を対象。
  - 401 応答時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
  - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除/更新。
    - PK 欠損行のスキップと警告ログ。
    - fetched_at を UTC ISO8601 形式で記録し、取得時点をトレース可能に。
  - ユーティリティ: 安全な型変換関数 `_to_float`, `_to_int`。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集し raw_news テーブルへ保存するワークフローを実装。
  - セキュリティ対策を備えた設計:
    - defusedxml を使用し XML Bomb 等を防御。
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先の事前検証でプライベートアドレス（SSRF）をブロック（カスタム RedirectHandler）。
    - レスポンスサイズ上限（10 MB）を設けてメモリDoSを防止。gzip 解凍後も検査。
  - トラッキングパラメータ（utm_ 等）の除去と URL 正規化機能。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - DB 保存:
    - save_raw_news: チャンク毎に INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（RETURNING で実挿入数を取得）。
    - トランザクションでまとめてコミット/ロールバック。
  - 銘柄コード抽出関数 extract_stock_codes（4桁数値の検出と既知銘柄セットでフィルタ、重複除去）。
  - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリ）を定義。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）。
  - 3層構造に対応するテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（CHECK, NOT NULL, PRIMARY KEY, FOREIGN KEY）を適用。
  - 検索性能を意識したインデックス群を定義（銘柄×日付スキャンやステータス検索向け）。
  - init_schema(db_path) を提供: DB ファイルの親ディレクトリ自動作成、全テーブル・インデックスの作成（冪等）。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新（差分取得）を行う ETL の設計を実装。
  - デフォルトバックフィル日数（3日）により後出し修正を吸収。
  - 市場カレンダーの先読み（デフォルト 90 日）を考慮する設計（定数定義）。
  - ETLResult dataclass を追加: 実行結果、取得数、保存数、品質チェック結果、エラー等を集約。
  - スキーマ存在チェック/最大日付取得などのユーティリティ関数を提供。
  - 日付が非営業日の場合に直近営業日に調整する `_adjust_to_trading_day` を実装。
  - run_prices_etl を実装（差分算出、fetch_daily_quotes 取得、save_daily_quotes で保存、ログ出力）。

- パッケージ構成のスケルトンを追加（src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py）。

### 変更 (Changed)
- 初回リリースのため変更履歴は該当なし。

### 修正 (Fixed)
- 初回リリースのため修正履歴は該当なし。

### パフォーマンス (Performance)
- J-Quants クライアントでのレート制御と指数バックオフにより API 呼び出しの安定性とレート順守を両立。
- news_collector と news_symbols のバルク挿入はチャンク処理（デフォルト 1000 件）でオーバーヘッドを低減。
- DuckDB 側のインデックスにより頻出クエリの応答性を改善する設計。

### セキュリティ (Security)
- RSS 処理で defusedxml を使用して XML 関連攻撃を緩和。
- URL 正規化とトラッキングパラメータ除去により冪等性を確保。
- SSRF 緩和:
  - リダイレクト時スキーム検証、ホストがプライベート/ループバック/リンクローカルでないことを検査。
  - 初回 URL と最終 URL の両方を検証。
- レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズ検査でメモリ爆発対策を実施。
- .env 読み込み時に OS 環境変数を保護するための protected セット実装（上書き制御）。

### 既知の問題 (Known issues)
- run_prices_etl の実装がファイル末尾で途中で終わっている（戻り値のタプルの記述が不完全な箇所あり）。実運用前に戻り値・例外処理周りの最終確認が必要。
- strategy / execution モジュールはスケルトンのみで、実際の売買ロジック・発注連携は未実装。

### 互換性に関する注意 (Compatibility)
- DB スキーマは初期化時に作成され、既存テーブルがある場合はスキップする（冪等）。ただしスキーマ変更が将来入るとマイグレーションが必要になる可能性あり。

### ドキュメント (Documentation)
- 各モジュール冒頭に設計方針・使用例・想定振る舞いの docstring を追加し、実装意図を明示。

---

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートには追加の変更やリファクタ、テスト結果、既知の脆弱性の修正情報などを反映してください。