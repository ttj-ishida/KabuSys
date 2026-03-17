Keep a Changelog準拠の CHANGELOG.md（日本語）を以下に作成しました。コードの内容から機能・改善点・セキュリティ対策などを推測してまとめています。

CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-17
--------------------

Added
- 初期リリース: KabuSys — 日本株自動売買のためのデータ取得・ETL・スキーマ基盤を実装。
- パッケージ基礎
  - kabusys パッケージの初期化（src/kabusys/__init__.py）を追加。バージョン: 0.1.0。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルートの検出: .git または pyproject.toml を探索）。
  - .env と .env.local の優先度/上書きルールを実装（OS環境変数の保護機構あり）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - .env パーサの実装: export 形式、クォート内エスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、J-Quants/Slack/kabuステーション/DBパス/実行環境/ログレベル等のプロパティを取得。環境値の検証（有効な環境名やログレベル）を行う。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（JSON レスポンス処理、エラー処理）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - 再試行（指数バックオフ）を実装（最大 3 回、408/429/5xx を再試行対象）。
  - 401 応答時にリフレッシュトークンで自動的に ID トークンを更新して再試行（1 回のみ）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等的保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - フェールセーフな数値変換ユーティリティ（_to_float, _to_int）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードの取得・パース・前処理・DB 保存のワークフローを実装。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト先のスキーム/ホスト検証、ホストがプライベートアドレスかどうかを判定してブロック。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検証。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保（utm_* 等トラッキングパラメータを除去して正規化）。
  - テキスト前処理（URL 除去・空白正規化）。
  - DuckDB への一括保存機能:
    - save_raw_news: チャンク化して INSERT ... RETURNING で新規挿入IDを返す。トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入、ON CONFLICT で重複を無視。
  - 銘柄抽出: 正規表現で 4 桁銘柄コード候補を抽出し、known_codes と照合して重複を排除して返す。
  - fetch_rss はソース単位で例外を局所的に扱い、失敗しても他ソースは継続。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定した包括的なテーブル定義とインデックスを実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー、
    prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー、
    features, ai_scores などの Feature レイヤー、
    signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などの Execution レイヤーを定義。
  - 各テーブルに対する制約（NOT NULL, PRIMARY KEY, CHECK 等）や外部キー関係を定義。
  - init_schema(db_path) でディレクトリ作成 → テーブル/インデックス作成（冪等）を行う。get_connection() を提供。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分更新ロジック用ユーティリティ（最終取得日取得、営業日調整）を実装。
  - run_prices_etl の下地を実装: 差分更新（最終取得日に対する backfill 日数の処理）、J-Quants からの取得 → 保存の流れをサポート。
  - ETLResult データクラスを導入し、取得数・保存数・品質チェック結果・エラー情報などをまとめて返却可能。
  - 品質チェック（quality モジュール）と連携する設計（品質問題は集約して呼び出し元が対処）。
- テスト/モック支援
  - news_collector._urlopen をテスト時にモックしやすい設計。
  - jquants_client の id_token 注入パラメータにより外部 ID トークンを注入可能でテスト容易性向上。

Changed
- 初期リリースのため該当なし（新規機能群の追加）。

Fixed
- 初期リリースのため該当なし。

Security
- XML パースに defusedxml を採用、RSS パーサで XML 攻撃を防止。
- SSRF 対策を強化: リダイレクト検査・プライベートアドレス判定・スキーム検証・レスポンスサイズ制限を実装。
- 環境変数ロード時に OS 環境を保護する protected 機構を導入。

Performance
- J-Quants API 呼び出しで固定間隔のレートリミッタを導入し、API レート制限に準拠。
- news_collector の DB 挿入でチャンク化（_INSERT_CHUNK_SIZE）とトランザクションまとめによりオーバーヘッド削減。

Notes / TODO / Observations
- ETL パイプラインは prices ETL の主要ロジックが実装済み。今後:
  - financials / calendar / 品質チェックの呼び出し・結果集約・通知フローを含めた完全なジョブ化。
  - ストラテジー層、実行層（execution）との統合テスト・エンドツーエンド検証。
- config._find_project_root は __file__ を基点に探索するため、配布後も .env 自動読込が正しく機能する設計。ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うこと。
- 一部戻り値／API の取り回し（例えば run_prices_etl の戻り値処理など）は今後の拡張で微調整される可能性あり。

（変更履歴はソースコードの現状から推測してまとめています。実際のリリースノート作成時は、コミット履歴・Issue・PR に基づき具体的な差分・責任者・引用を追加してください。）