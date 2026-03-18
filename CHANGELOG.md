# CHANGELOG

このファイルは Keep a Changelog の形式に従っています。  
各リリースの主な変更点を日本語で記載しています。コードベースの内容から推測して記載しています。

全般的な注意
- バージョニングはセマンティックバージョン (MAJOR.MINOR.PATCH) を想定しています。
- 日付はこの CHANGELOG 作成時点（2026-03-18）を初回リリース日に使用しています（推測）。
- 実装設計・運用上の重要な挙動や制約も「Added」や「Security」「Notes」に記載しています。

## [Unreleased]
- 次期リリースに向けた未反映の変更点はありません（初版リリース直後の状態として作成）。

## [0.1.0] - 2026-03-18
初回公開リリース（推測）。以下の主要機能と実装が導入されています。

### Added
- パッケージ基礎
  - パッケージ名: kabusys。トップレベルで version が `0.1.0` に設定され、モジュール公開一覧 (__all__) に data, strategy, execution, monitoring を含める。
- 設定 / 環境変数管理
  - settings オブジェクトを提供する `kabusys.config.Settings`。
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。読み込み優先順位は OS 環境 > .env.local > .env。
  - 行パーサーの実装: export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープに対応。
  - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数チェック (`_require`) と、`KABUSYS_ENV`（development/paper_trading/live）および `LOG_LEVEL` の値検証。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
- Data レイヤー（DuckDB を前提）
  - `kabusys.data.schema` により DuckDB 用スキーマ定義を追加（raw レイヤーのテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions 等）。
  - `kabusys.data.jquants_client`:
    - J-Quants API クライアント実装（HTTP ユーティリティ、ページネーション対応 fetch_* 関数、取得データを DuckDB に保存する save_* 関数）。
    - レート制限を守る固定間隔スロットリング実装 (`_RateLimiter`)。デフォルト 120 req/min。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 時は Retry-After を考慮）。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - 取得データの冪等保存（INSERT ON CONFLICT DO UPDATE）を提供。
    - 型変換ユーティリティ `_to_float` / `_to_int` を実装し不正値や空値を安全に扱う。
  - `kabusys.data.news_collector`:
    - RSS フィード収集パイプライン（フェッチ、前処理、記事ID生成、DuckDB への冪等保存、銘柄紐付け）。
    - URL 正規化（トラッキングパラメータ除去、クエリパラメータソート、スキーム小文字化、フラグメント削除）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を使った XML パース（XML BOM 攻撃対策）。
    - SSRF 対策: スキーム検証（http/https のみ）、ホストがプライベートアドレスかチェック、リダイレクト先の事前検証ハンドラ。
    - レスポンスサイズ上限チェック（デフォルト 10MB、gzip 解凍後も検証）と受信制限。
    - bulk insert 最適化（チャンクサイズ、1 トランザクションでの挿入、INSERT ... RETURNING を使って実際に挿入された件数を取得）。
    - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数字の正規表現と known_codes フィルタ）。
    - フル収集ジョブ run_news_collection を実装（各ソース独立エラーハンドリング、既知銘柄との紐付け）。
- Research / Factor計算
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算: calc_forward_returns（単一クエリで複数ホライズン取得、営業日→カレンダー日バッファで効率化）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関、同順位は平均ランク）。
    - 基本統計量集計: factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、浮動小数丸め考慮）。
    - 標準ライブラリのみで実装（pandas など非依存）。
  - `kabusys.research.factor_research`:
    - モメンタムファクター: calc_momentum（1M/3M/6M リターン、MA200 乖離率）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR, ATR/close, 20日平均出来高・売買代金, 出来高比率）。
    - バリューファクター: calc_value（raw_financials から最新財務を取得して PER / ROE を計算）。
    - すべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番口座/API へはアクセスしない方針。
  - `kabusys.research.__init__` で主要関数を再エクスポート。
- パッケージ構成
  - strategy, execution, monitoring モジュールのパッケージプレースホルダを配置（__init__ あり）。

### Changed
- 該当なし（初回リリース）。

### Fixed
- 該当なし（初回リリース）。

### Security
- ニュース収集での SSRF 対策を強化（URL スキーム検証、プライベート IP 判定、リダイレクト時の事前検証）。
- XML パースに defusedxml を利用し XML 脆弱性を軽減。
- J-Quants クライアントは 401 時のトークン自動更新ロジックを導入し、認証エラー時の安全な回復をサポート。

### Performance
- J-Quants API のレート制限を守る固定間隔スロットリングを実装。
- RSS / news の保存はチャンク化・単一トランザクション・INSERT ... RETURNING を使い DB オーバーヘッドを削減。
- calc_forward_returns 等はスキャン範囲を必要最小限に限定するロジック（max_horizon に基づくカレンダーバッファ）を組み込み。

### Notes / Known limitations
- research モジュールはいずれも DuckDB の特定テーブル（prices_daily, raw_financials 等）に依存。事前にスキーマ準備およびデータロードが必要。
- calc_value の PBR や配当利回りは現バージョンで未実装（明記あり）。
- raw_executions の DDL はコード断片で途中までの定義が含まれている（スニペットの都合で全体が切れている可能性あり）。
- News 抽出の銘柄コードは 4 桁数字のみを対象とし、誤検出や文脈を無視する可能性があるため追加の NER やルール強化が今後必要。
- research パッケージは外部ライブラリに依存しない実装だが、大量データ処理や高度な統計処理では pandas 等を導入する余地あり。

### Internal / Developers
- 設定読み込みの振る舞い:
  - OS 環境変数が優先され、.env からは未設定のキーのみを読み込む (override=False)。
  - .env.local は override=True で読み込み、ただし OS 環境変数（読み込み前のキー集合）は保護される。
- jquants_client._request は最大再試行回数後に RuntimeError を送出。
- news_collector.fetch_rss は XML パース失敗時に空リストを返し、呼び出し側で例外伝播を抑止する設計。

---

今後のリリースで期待される改善例（非網羅）
- Strategy / Execution の実装強化（kabu ステーション API とのインテグレーション、発注・ポジション管理）。
- Feature Layer（特徴量保存テーブル）の DDL と ETL ツール化。
- News の自然言語処理強化（銘柄リンクの精度向上、記事分類）。
- 単体テスト・統合テスト用のモック/フィクスチャの整備（外部 API 呼び出しのモック等）。
- パフォーマンス改善のための並列取得・バックグラウンド更新機構。