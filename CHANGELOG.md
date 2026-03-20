# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在日付: 2026-03-20

リンクや履歴が増えたら適宜更新してください。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買基盤「KabuSys」のコア機能群を実装しました。主な追加点・設計方針は以下のとおりです。

### Added
- パッケージエントリポイント
  - src/kabusys/__init__.py にてバージョン情報と公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパースを強化（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、コメント扱いのルール等）。
    - 環境変数未設定時に例外を投げる _require と、Settings クラスを提供。Settings は以下のプロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - is_live / is_paper / is_dev ブールヘルパー

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しの共通処理（JSON パース、ページネーション、レート制御、リトライ、トークン自動リフレッシュ）を実装。
    - 固定間隔スロットリングによるレート管理（120 req/min）を実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 429 の場合は Retry-After を優先。対象ステータスの扱いを明示。
    - 401 発生時はリフレッシュを 1 回だけ行い再試行（無限再帰防止）。
    - get_id_token による ID トークン取得とモジュールレベルキャッシュ。
    - データ取得関数を実装:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
    - DuckDB へ冪等に保存する関数:
      - save_daily_quotes（raw_prices テーブルへの upsert）
      - save_financial_statements（raw_financials テーブルへの upsert）
      - save_market_calendar（market_calendar テーブルへの upsert）
    - データ型変換ユーティリティ _to_float / _to_int（不正値を安全に None に変換）
    - 取得時刻（fetched_at）は UTC ISO8601 で保存し、look-ahead bias のトレースを可能にする設計

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news に保存する基礎実装（デフォルトソースに Yahoo Finance を含む）。
    - セキュリティ対策: defusedxml を使った XML パース、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、HTTP(S) スキームのみ許可、SSRF/IP 直指定の遮断方針を想定した実装方針。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）と記事 ID を SHA-256 のハッシュで生成し冪等性を確保。
    - バルク INSERT のチャンク化（チャンクサイズ _INSERT_CHUNK_SIZE）とトランザクションで保存する方針を採用。
    - 設計として news -> news_symbols（銘柄紐付け）を想定。

- リサーチ系モジュール（研究/解析用）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター算出を実装:
      - calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
      - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
      - calc_value（per, roe：raw_financials と prices_daily を組合せ）
    - DuckDB のウィンドウ関数を活用し、営業日ギャップ（週末/祝日）に耐性のある設計。
  - src/kabusys/research/feature_exploration.py
    - 研究向けの補助関数実装:
      - calc_forward_returns（複数ホライズンの将来リターン算出、デフォルト [1,5,21]）
      - calc_ic（Spearman のランク相関による IC 計算）
      - factor_summary（count/mean/std/min/max/median の統計サマリー）
      - rank（同順位を平均ランクで扱うランク計算）
    - 外部依存を最小化（標準ライブラリのみ）する設計

- 戦略実行前処理およびシグナル生成
  - src/kabusys/strategy/feature_engineering.py
    - 研究で計算した raw factor を正規化・合成して features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化は zscore_normalize（kabusys.data.stats）を利用、±3 でクリップして外れ値対策。
    - features テーブルへの日付単位置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性と原子性を確保。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成（generate_signals）。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を計算（シグモイド等を適用）。
    - デフォルト重みや閾値を定義（デフォルト閾値 0.60、stop loss -8% 等）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - 保有ポジションに対するエグジット判定（stop_loss、score_drop）を実装。SELL を優先し BUY から除外するポリシー。
    - signals テーブルへの日付単位置換で冪等性・原子性を確保。
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開

- データ統計ユーティリティ（参照）
  - research と strategy で zscore_normalize 等を利用する設計（kabusys.data.stats を参照）

### Changed
- 初回リリースにつき後方互換の変更履歴はありません。

### Fixed
- 初回リリースにつき修正履歴はありません。

### Security
- news_collector で defusedxml を使用、受信バイト数上限、トラッキングパラメータ除去、HTTP(S) のみ許可など複数の安全対策を設計に含めています。
- J-Quants クライアントはトークン自動リフレッシュとリトライ戦略を導入し、失敗時の過度な情報露出や無限ループを防止する実装としています。
- 環境変数自動ロード時に OS 環境変数を保護する protected セットを導入（.env ファイルで OS 変数が上書きされないように）。

### Notes / Migration
- 必須環境変数（未設定の場合は起動時または該当 API 呼び出し時に ValueError）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 環境: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定してください。
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のデフォルトパスは settings.duckdb_path / settings.sqlite_path を参照（それぞれ data/kabusys.duckdb, data/monitoring.db）。
- jQuants API のレート上限とリトライ方針に注意してください（120 req/min、最大 3 回の指数バックオフ等）。

---

今後のリリースでは、execution 層（発注ロジック）、monitoring（監視/アラート）、AI スコア生成パイプライン、news ↔ code の自動紐付けロジックや追加の統計・評価指標の強化等を予定しています。