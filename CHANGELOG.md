# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-19

初回公開リリース。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加 (src/kabusys/__init__.py)。バージョンを "0.1.0" に設定し、主要サブパッケージをエクスポート。
- 環境変数 / 設定管理
  - .env ファイル／環境変数からの設定読み込み機能を実装 (src/kabusys/config.py)。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動読み込みを提供。
    - .env と .env.local の読み込み順序を実装（OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env 行パース（export プレフィックス対応、シングル／ダブルクォート内のエスケープ、インラインコメントの処理）を実装。
    - Settings クラスにアプリケーション設定プロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン／チャンネル、DB パス、環境名・ログレベル検証等）。
- データ取得クライアント（J-Quants）
  - J-Quants API クライアント実装 (src/kabusys/data/jquants_client.py)。
    - 固定間隔のレートリミッター（120 req/min）を実装。
    - HTTP リクエストのリトライ（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。
    - 401 発生時のリフレッシュトークンによる自動 ID トークン更新（1 回までのリトライ）。
    - ページネーション対応の取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による重複更新を行う。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し不正値を安全に扱う。
- ニュース収集
  - RSS 収集・保存モジュールを実装 (src/kabusys/data/news_collector.py)。
    - RSS フィードの取得（gzip 対応）、XML パースに defusedxml を利用して安全性を高める。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/プライベートアドレス検査、DNS 解決による内部アドレス判定。
    - レスポンスサイズ上限（10 MB）や Gzip 解凍後サイズチェックを実装（DoS 対策）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。トラッキングパラメータ（utm_* 等）を除去して正規化。
    - テキスト前処理（URL 除去、空白正規化）と記事保存（save_raw_news）を実装。INSERT ... RETURNING を使い実際に挿入された ID を返す。
    - 銘柄コード抽出（4桁数字パターン）と news_symbols への紐付けを一括挿入するユーティリティを実装（重複排除・チャンク挿入）。
    - デフォルト RSS ソース（Yahoo Finance Business）を定義。
- リサーチ（ファクター・特徴量探索）
  - ファクター計算モジュールを実装 (src/kabusys/research/factor_research.py)。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新報告日ベース）。
    - 各関数は DuckDB 接続と target_date を受け取り prices_daily / raw_financials のみを参照する設計（本番発注 API 等にはアクセスしない）。
  - 特徴量探索ユーティリティを実装 (src/kabusys/research/feature_exploration.py)。
    - calc_forward_returns: 指定日からの将来リターン（デフォルト 1/5/21 営業日）を一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）を計算（同値処理・最小サンプルチェックあり）。
    - rank: 同順位は平均ランクを返すランク関数（丸めで浮動小数の ties を考慮）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの公開 API を定義 (src/kabusys/research/__init__.py)（calc_momentum 等をエクスポート）。
- DuckDB スキーマ定義（初期DDL）
  - DuckDB のスキーマ／DDL 断片を追加 (src/kabusys/data/schema.py)。
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義（NOT NULL・チェック制約・PK 指定）を含む。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- ニュース収集で次のセキュリティ対策を実装：
  - defusedxml による安全な XML パース（XML Bomb 等の防御）
  - SSRF 防止のためスキーム検証・リダイレクト検査・プライベートアドレス拒否
  - レスポンスサイズ上限と Gzip 解凍後のサイズ検査（メモリ DoS 対策）

---

注意:
- 本リリースでは外部発注（kabu ステーション）や実際の発注ロジックは含まれておらず、データ取得／保存・リサーチ用ユーティリティ群が中心です。
- 各モジュールのログ出力や例外は詳細に実装されており、運用時のトラブルシュートを考慮しています。
- 今後のリリースでは execution（発注）・monitoring（監視）・strategy の具体的な実装や CLI、テストカバレッジの追加を予定しています。