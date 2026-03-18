# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更点を分かりやすく記載しています。

全般:
- 本リリースはパッケージバージョン 0.1.0 を想定した初期リリースです（src/kabusys/__init__.py の __version__ = "0.1.0" に基づく）。
- 日付: 2026-03-18

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-18

### Added（追加）
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュールとして data, strategy, execution, monitoring を __all__ に定義（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数/.env 読み込みユーティリティを追加（src/kabusys/config.py）。
    - .git または pyproject.toml を起点にプロジェクトルートを検出して .env/.env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化オプション。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント（スペース/タブ前の#）に対応。
    - settings オブジェクトを提供し、J-Quants / kabuAPI / Slack / DB パスなど主要設定をプロパティ経由で取得。バリデーション（env 値・ログレベル等）を実施。
    - デフォルトの DB ファイルパス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）や API ベース URL のデフォルト値を設定。

- Data レイヤー
  - DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等。初期化用の DDL を含む）。
    - スキーマ設計は Raw / Processed / Feature / Execution の3層構造に準拠。

  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - API レート制限（120 req/min）に対応する固定間隔レートリミッタ実装。
    - リトライ（指数バックオフ、最大3回）と 408/429/5xx ハンドリング。
    - 401 受信時にはリフレッシュトークンから id_token を再取得して1回リトライする自動リフレッシュ機構を実装。
    - ページネーション対応で fetch_daily_quotes, fetch_financial_statements を実装。
    - fetch_market_calendar を実装（JPX カレンダー取得）。
    - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除し、fetched_at を UTC で記録して Look-ahead-bias のトレースを可能に。

  - News コレクタを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得 -> 前処理 -> raw_news へ冪等保存 -> 銘柄紐付け のワークフローを実装。
    - セキュリティ/堅牢性対策:
      - defusedxml を用いた XML パース（XML Bomb 等を軽減）。
      - SSRF 対策：URL スキーム検証（http/https のみ）、プライベート/ループバック/リンクローカル判定、リダイレクト時の検査用ハンドラ（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）の導入、gzip 解凍時のサイズ再確認（Gzip bomb 対策）。
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
      - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - DB 保存:
      - save_raw_news はチャンク分割 + トランザクション + INSERT ... ON CONFLICT DO NOTHING RETURNING id による正確な新規挿入判定を実装。
      - news_symbols（記事と銘柄紐付け）を一括挿入する内部ユーティリティを実装（重複除去、チャンク挿入、トランザクション）。
    - 銘柄抽出ユーティリティ:
      - 4桁コード検出（正規表現）と既知コードセットによるフィルタリング（extract_stock_codes）。

- Research（リサーチ）機能
  - feature_exploration モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン算出 calc_forward_returns（複数ホライズン対応、SQL LEAD を活用）。
    - Information Coefficient（Spearman の rho）計算 calc_ic（ランク変換、ties 対応）。
    - 基本統計量要約 factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、丸めによる tie 検出の安定化）。
    - 研究用途に限定し、DuckDB の prices_daily テーブルのみ参照、外部 API にはアクセスしないという設計方針を明記。
    - 標準ライブラリのみで実装し外部依存を避ける方針。

  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）。データ不足時は None を返すロジック。
      - calc_volatility: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio。true_range の NULL 伝播制御や cnt による検査を実施。
      - calc_value: raw_financials から最新財務データを取得し per, roe を計算。target_date 以前の最新レコードを ROW_NUMBER で取得。
    - 各関数は DuckDB 接続を受け取り SQL ウィンドウ関数を多用して高速に計算する設計。
    - 戦略/研究用途に限定し、外部 API へアクセスしない旨を明記。

- パッケージ re-export
  - src/kabusys/research/__init__.py で主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### Changed（変更）
- （初回リリースのため該当なし）

### Fixed（修正）
- （初回リリースのため該当なし）

### Security（セキュリティ関連）
- RSS ニュース収集における SSRF/リダイレクト対策、XML パースにおける defusedxml の使用、大きなレスポンスや gzip 解凍後サイズ検査など多数の安全対策を導入。
- J-Quants クライアントは 401 自動リフレッシュとリトライ制御を実装し、認証/ネットワーク障害時の堅牢性を向上。

### Notes（注意事項 / 既知の制約）
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装しており、大規模データ処理時はパフォーマンスや利便性の点で追加最適化（pandas/NumPy の導入など）を検討する余地があります。
- news_collector の _is_private_host は DNS 解決失敗時を「非プライベート」と見なす設計（安全寄りの検出では DNS 解決成功時にプライベートと判定すればブロック）。運用環境によってはホワイトリスト/プロキシ設定等が必要になる可能性があります。
- DuckDB への保存は ON CONFLICT を使用した冪等化を行っていますが、スキーマに依存するためスキーマ変更時は互換性に注意してください。
- jquants_client のレート制限は固定間隔スロットリング（簡易）を採用しているため、厳密なバースト性や複数プロセスからの呼び出しがある場合は追加制御が必要です。

---

（参考）主要ファイル:
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/factor_research.py

今後のリリースでは、テストカバレッジ・ドキュメント・CLI/運用スクリプト・監視/アラート統合などの追加を検討してください。