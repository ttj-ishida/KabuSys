# Changelog

すべての注目に値する変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主にデータ収集・保存、研究用ファクター算出、特徴量生成、シグナル生成、環境設定ユーティリティなどのコアモジュールを含みます。

### Added
- パッケージ基盤
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージエクスポート: `data`, `strategy`, `execution`, `monitoring` を __all__ に登録。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数からの設定自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - Settings クラスを追加し、以下の設定プロパティを提供：
    - J-Quants / kabuステーション / Slack / データベース（DuckDB / SQLite） / ログレベル / 実行環境（development/paper_trading/live）
  - 不正な KABUSYS_ENV / LOG_LEVEL 値に対する検証と例外処理を実装。

- Data モジュール: J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足 / 財務データ / マーケットカレンダー取得）。
  - レート制限（固定間隔スロットリング）実装: デフォルト 120 req/min。_RateLimiter により間隔制御。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）を実装。429 の Retry-After ヘッダを尊重。
  - 401 応答時にリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライする仕組みを実装。モジュールレベルの ID トークンキャッシュを導入。
  - ページネーション対応（pagination_key を利用）。
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes: raw_prices テーブルへの保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials テーブルへの保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar テーブルへの保存（ON CONFLICT DO UPDATE）
  - 入力変換ユーティリティ `_to_float`, `_to_int` を追加し、データの安全な型変換を実施。
  - Look-ahead バイアス対策として fetch 時の fetched_at を UTC タイムスタンプで記録。

- Data モジュール: ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集パイプラインを実装（デフォルトに Yahoo Finance Business RSS を登録）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）を実装。記事IDは正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を利用する設計方針を明示。
  - セキュリティ対策:
    - defusedxml を用いた XML の安全パース（XML Bomb 等対策）。
    - HTTP/HTTPS 以外のスキーム拒否（SSRF 緩和）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
  - DB バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）と、冪等保存ポリシー（ON CONFLICT / DO NOTHING）を想定。

- Research モジュール（kabusys.research）
  - ファクター計算 API を提供: calc_momentum, calc_volatility, calc_value。
  - 研究用途ユーティリティ:
    - zscore_normalize を外部に公開（kabusys.data.stats から利用）。
    - feature_exploration: calc_forward_returns（将来リターン計算）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
  - 実装方針: DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API / 発注層に依存しない。

- Strategy モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究用の生ファクターを取得（research.factor_research の calc_*）し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクションで原子性を保証）。冪等性を確保。
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores（AI スコア・レジームスコア）を統合し各銘柄の最終スコア final_score を計算。
    - コンポーネントスコアとして momentum / value / volatility / liquidity / news を算出（各種シグモイド・反転処理や欠損補完ロジックを含む）。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（デフォルト BUY=0.60）を採用。外部指定 weights の検証（不正値はスキップ）と正規化を実装。
    - Bear レジーム判定（AI の regime_score 平均が負でかつサンプル数が閾値以上の場合）では BUY シグナルを抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）を実装。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。SELL が BUY に優先されるポリシーを適用。
    - 実行（execution）層・発注 API には依存しない純粋なシグナル生成ロジック。

- DuckDB を前提とした SQL 実装
  - 多くの集計・窓関数を DuckDB SQL で実装（LEAD/LAG, AVG OVER, COUNT OVER など）。
  - パフォーマンスを意識したスキャン範囲のバッファ設計（営業日 ≒ カレンダー日 ×2 のバッファ等）を採用。

### Changed
- （該当なし）初回リリースのため過去変更はなし。

### Fixed
- （該当なし）初回リリースのため不具合修正履歴なし。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- news_collector で defusedxml を利用して XML パースの脆弱性を低減。
- ニュース取得で受信サイズ制限を設け、潜在的なメモリ DoS を緩和。
- RSS 経由の URL 正規化とスキームチェックにより SSRF / トラッキングの影響を低減。

### Notes / Known limitations
- strategy.signal_generator のトレーリングストップや時間決済（保有 60 営業日超過）等は未実装（コード内に TODO コメントあり）。positions テーブルに peak_price / entry_date 等のカラムが必要。
- calc_value は現時点で PBR・配当利回りをサポートしていない（コメントで未実装と明記）。
- news_collector の詳細な銘柄紐付け処理（news_symbols）は実装想定だが、本コードスニペットでは未完の可能性あり。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は別モジュールに依存しており、同梱利用前提。
- 外部 API 呼び出しや DB スキーマの前提があるため、実行には適切な DuckDB スキーマおよび環境変数設定が必要。

---

開発・運用に際して差し支えがなければ、次回リリースでは下記を検討してください:
- シグナル→注文（execution）パイプラインの実装と統合テスト
- news_collector の完全な銘柄エンリッチ処理（news_symbols との連携）
- 監視（monitoring）およびメトリクス収集の実装（Slack 通知の実装箇所の明示）
- 単体/統合テストと CI 設定ファイルの追加

（以上）