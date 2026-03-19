# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- 初期リリース: kabusys パッケージの基本モジュール群を追加。
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ一覧を定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出（.git / pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
  - .env の行パースは export 構文、クォート／エスケープ、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別等のプロパティを取得可能に。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と is_live/is_paper/is_dev の便宜プロパティを実装。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API レートリミッタ（120 req/min 固定間隔スロットリング）実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュの共有。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務四半期データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等操作）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE / DO NOTHING を利用し冪等性を確保。
  - データ変換ユーティリティ _to_float/_to_int を追加（堅牢な型変換）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得、パース、前処理、DuckDB への保存ワークフローを実装。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事ID（SHA-256 先頭32文字）生成。
  - text 前処理（URL除去、空白正規化）ユーティリティ。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先検査を行うカスタム RedirectHandler（プライベート/ループバック検出）
    - ホストのプライベートアドレス判定（IP 直接判定および DNS 解決）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）や gzip 解凍後のサイズチェック（Gzip-bomb 対策）。
  - defusedxml を利用した安全な XML パース。
  - raw_news / news_symbols への保存（トランザクション、チャンク挿入、INSERT RETURNING を使用して実際に挿入された件数を取得）。
  - 銘柄コード抽出ユーティリティ（本文中の 4 桁数字を known_codes に照合して抽出）。
  - run_news_collection により複数ソースを順次処理し、個別ソース失敗時も他ソース継続。
- リサーチ（ファクター）モジュール
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: prices_daily を参照して複数ホライズンの将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ties を平均ランクで扱う）。
    - rank, factor_summary: ランク付け・基本統計量計算の実装（標準ライブラリのみで実装）。
  - src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB SQL で計算（窓関数利用）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御を厳格に実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新報告を銘柄ごとに取得）。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計（外部 API にアクセスしない）。
  - src/kabusys/research/__init__.py で主要ユーティリティを再エクスポート。
  - リサーチ系関数は外部ライブラリ（pandas 等）に依存せず標準ライブラリで実装（軽量性重視）。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw Layer 向けの DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - DataSchema.md に準拠した層構造の説明をコメントで明記。
- 設計/運用面の考慮点をコード内に記載
  - Look-ahead bias 回避のため fetched_at を UTC で記録。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間共有）。
  - DB 保存はトランザクションでまとめ、チャンク処理で SQL 長制限に配慮。
  - ログ出力を各所に追加（情報・警告・例外のトラッキング）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサに defusedxml を使用して XML 関連脆弱性を低減。
- ニュース取得での SSRF 対策を複数層で実装（スキーム検証、リダイレクト時検査、プライベート IP 検出）。
- J-Quants クライアントは 401 時に安全にトークンリフレッシュし、無限再帰を防止する設計。

### 既知の制限 / 注意点 (Known issues / Notes)
- strategy/execution パッケージの __init__ は存在するが、具体的な戦略ロジック・発注処理は今後の実装対象（現状は骨格）。
- research モジュールは標準ライブラリのみで実装されているため、大規模データ操作で pandas 等を使う場合は拡張を検討。
- DuckDB スキーマ定義は Raw Layer を中心に実装。Processed/Feature/Execution 層の完全な DDL は継続実装予定。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートやドキュメントとは差異がある可能性があります。必要であれば各項目をより厳密な日時・変更理由・対応コミットに紐づけて更新できます。