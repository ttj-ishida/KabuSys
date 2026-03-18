# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

注意: コードベースから推測して作成したため、実際のコミット履歴と差異がある場合があります。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン 0.1.0）。
  - モジュール構成: data, research, strategy, execution, monitoring 等の名前空間を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（未設定時は ValueError を送出）
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の値検証
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装:
    - レート制限対応（120 req/min, 固定間隔スロットリング）
    - リトライ処理（指数バックオフ、最大3回、408/429/5xx をリトライ対象）
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して再試行
    - ページネーション対応（pagination_key）
    - タイムアウトと JSON デコードエラーハンドリング
  - データ取得関数:
    - fetch_daily_quotes (株価日足 OHLCV)
    - fetch_financial_statements (財務四半期データ)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC ISO8601 で記録し、挿入は ON CONFLICT を使用して上書き
  - ユーティリティ: _to_float / _to_int による安全な型変換
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集ロジックを実装
    - デフォルトソース: Yahoo Finance ビジネスカテゴリ RSS
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証
    - テキスト前処理（URL 除去、空白正規化）
    - defusedxml による安全な XML パース（XML Bomb 対策）
    - SSRF 対策:
      - リダイレクト先のスキーム・ホストを検査するカスタムリダイレクトハンドラ
      - ホストのプライベート IP 判定（直接 IP／DNS 解決両対応）で内部ネットワークアクセスを拒否
      - http/https 以外のスキームを拒否
    - レスポンスサイズ制限（10 MB）、Content-Length チェック、gzip 解凍後の再チェック（Gzip bomb 対策）
    - raw_news テーブルへのチャンク INSERT（ON CONFLICT DO NOTHING）と INSERT ... RETURNING による挿入 ID の取得
    - news_symbols（記事と銘柄の紐付け）を一括挿入する内部ユーティリティ（チャンク化、トランザクション、RETURNING）
    - テキストから 4 桁銘柄コードを抽出するユーティリティ（既知銘柄セットでフィルタ、重複排除）
    - run_news_collection: 複数ソースを順に収集し DB に保存、個別ソースごとにエラーハンドリング

- リサーチ / 特徴量探索 (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（標準: 1,5,21 営業日）に対する将来リターンを一括で取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合・欠損/非有限値の除外、3件未満は None）
    - factor_summary: 各ファクター列の基本統計（count, mean, std, min, max, median）
    - rank: 同順位は平均ランクとするランク変換（丸め処理で ties 検出の安定化）
    - 設計上 pandas 等に依存せず標準ライブラリのみで実装
    - DuckDB の prices_daily テーブルのみ参照（本番発注 API にはアクセスしない）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200日移動平均乖離）を DuckDB の窓関数で計算
    - calc_volatility: ATR(20), 相対ATR (atr_pct), 20日平均売買代金, 出来高比率等を計算（true_range の NULL 伝播制御）
    - calc_value: raw_financials から直近財務（report_date <= target）を取得して PER/ROE を計算
    - 各関数は prices_daily / raw_financials のみ参照し、本番取引 API には触れない
    - 計算結果は (date, code) キーの辞書リストとして返却
    - 設計上、データ不足時は None を返す（ウィンドウ行数や EPS=0 など）

- DuckDB スキーマ定義の骨格 (kabusys.data.schema)
  - Raw レイヤのテーブル DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions（定義の一部まで実装）
  - スキーマ初期化用モジュールの基盤を追加

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- ニュース収集で以下を導入して安全性を向上:
  - defusedxml を用いた XML パース（外部 XML 攻撃対策）
  - リクエスト/リダイレクト時のホスト/スキーム検証とプライベートIP拒否（SSRF 緩和）
  - レスポンスサイズ制限および gzip 解凍後サイズチェック（DoS / Gzip bomb 対策）

### 既知の制限 / 備考
- research モジュールは標準ライブラリと DuckDB を前提に実装しており、外部依存（pandas など）は使っていません。データ量が多い場合はパフォーマンスチューニングを検討してください。
- schema モジュールは Raw レイヤの DDL を中心に実装済み。Processed/Feature/Execution レイヤの完全な DDL は今後整備予定。
- strategy/execution/monitoring パッケージの初期化ファイルは存在するものの、具体的な戦略ロジックや発注実装は未実装の領域があります。

---

将来のリリースでは、Processed/Feature レイヤのスキーマ・ETL パイプライン、戦略実装、実行（kabuステーション等との連携）、モニタリング/アラート機能の追加、テストカバレッジ拡充などを予定しています。