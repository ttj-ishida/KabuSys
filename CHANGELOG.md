Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベースから推測して作成しています。日付は本稿作成日を使用しています。

Unreleased
----------
- なし（次回リリースに備えた変更はここに記載します）

[0.1.0] - 2026-03-18
--------------------
Added
- パッケージ初回リリース (kabusys v0.1.0)
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - モジュール構成を整備（data, strategy, execution, monitoring 等を公開）。

- 環境変数 / 設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを追加（src/kabusys/config.py）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理を考慮）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティを安全に取得。未設定の必須値は ValueError を送出。
  - KABUSYS_ENV 値検証（development/paper_trading/live のいずれか）および LOG_LEVEL 検証を実装。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
  - 固定間隔のレート制御（120 req/min のスロットリング）を実装する RateLimiter を導入。
  - HTTP リトライロジック（指数バックオフ、最大試行回数、特定ステータスでのリトライ）を実装。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組みを実装（無限再帰防止のため allow_refresh フラグあり）。
  - ページネーション対応の fetch_* 関数を実装（fetch_daily_quotes, fetch_financial_statements 等）。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を用いた冪等性を確保。
  - 取り込み時に型変換ユーティリティ (_to_float, _to_int) を備え、不正な値を安全に無視する設計。

- ニュース収集（RSS ニュースコレクタ）
  - RSS フィードからのニュース取得・前処理・DB 保存ワークフローを実装（src/kabusys/data/news_collector.py）。
  - 記事 ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - XML パースに defusedxml を使用して XML Bomb 等への耐性を強化。
  - HTTP レスポンスに対するサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のチェックを実装。
  - リダイレクト時にスキーム・プライベートIP を検査する独自ハンドラを実装し SSRF を防止。
  - INSERT ... RETURNING を用いたチャンク（デフォルト 1000 件）挿入を実装し、実際に挿入された記事 ID の取得を可能に。
  - 銘柄コード抽出ユーティリティ（4桁コード抽出）と、抽出結果を news_symbols テーブルへ一括登録する機能を追加。
  - run_news_collection により複数ソースを横断して堅牢に収集・保存する処理を提供（ソース単位でエラーハンドリング）。

- 研究用/特徴量生成モジュール（Research）
  - ファクター探索ユーティリティ群を実装（src/kabusys/research/feature_exploration.py, factor_research.py）。
  - 将来リターン計算：calc_forward_returns（horizons = [1,5,21] デフォルト、DuckDB の prices_daily を利用）。
  - IC（Information Coefficient）計算：calc_ic（スピアマンのランク相関を実装）。rank 補助関数は同順位の平均ランクを扱う。
  - ファクター統計サマリー：factor_summary（count/mean/std/min/max/median を計算）。
  - Momentum/Volatility/Value ファクター計算：calc_momentum, calc_volatility, calc_value を実装。各関数は prices_daily（および raw_financials）テーブルのみを参照し本番口座や発注 API にはアクセスしない設計。
  - 主要パラメータ（窓長・ホライズン等）は定数化されており、データ不足時は None を返す挙動を採用。

- DuckDB スキーマ定義
  - Raw レイヤの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のスキーマ記述を追加）。
  - スキーマ定義は DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）を意識。

Changed
- ドキュメント的コメントと設計指針を各モジュールに追加し、挙動と安全性要件（Look-ahead bias 対策、冪等性、トランザクション単位の保存など）を明確化。

Security
- ニュース収集モジュールで SSRF 対策（リダイレクト先検査、ホストがプライベートアドレスかの判定）を実装。
- defusedxml による XML パースで XML に起因する攻撃を軽減。
- J-Quants クライアントでトークン自動更新を安全に扱い、機密情報は Settings を通じて取得。

Performance
- DuckDB へのバルク INSERT をチャンク化して実行し、1 トランザクションでコミットすることでオーバーヘッドを削減。
- calc_forward_returns 等は複数ホライズンを 1 クエリで取得することで DB スキャン回数を削減。
- API 呼び出しでは固定間隔スロットリングによりレート制限に適合（安定したスループットを維持）。

Notes / 互換性
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）が未設定の場合は ValueError を送出するため、環境変数の事前設定が必要。
- KABUSYS_ENV の許容値は "development", "paper_trading", "live" のみ。LOG_LEVEL は標準的なログレベルのみ受け付ける。
- news_collector.fetch_rss は http/https スキームのみ受け付け、ローカルファイルや mailto 等は拒否する。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + duckdb のみで動作するよう設計されている。

未解決 / 今後の課題（想定）
- Strategy / execution / monitoring の実装詳細は本リリースでは最小限。実際の発注ロジックやモニタリング連携は今後の実装対象。
- テストカバレッジや例外ケースの統合テスト（特にネットワーク異常や不正レスポンス時の挙動）の拡充。
- schema.py における Processed / Feature レイヤの DDL 定義およびマイグレーションの整備。

---

この CHANGELOG はコードから読み取れる機能と設計意図を基に推測して作成しています。必要であれば各変更点をクリック可能なチケットや対応ファイルへの参照（例: 行番号、関数名）に拡張します。どの程度の詳細まで記載するかご希望があれば教えてください。