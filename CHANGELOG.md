# CHANGELOG

すべての破壊的変更は遵守するものとし、このファイルは Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
初期公開リリース。日本株自動売買システムのコア機能群を実装しました。以下はコードから推測される主要な追加点・設計方針・既知制約です。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0。
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - 行パーサは export 形式やクォート、行内コメント、エスケープ等に対応。
  - settings オブジェクトを提供。J-Quants / kabuAPI / Slack / DB パス等の設定プロパティを持つ。
  - 環境値の簡易バリデーション（KABUSYS_ENV の有効値、LOG_LEVEL の有効値など）。
  - デフォルト DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（トークン取得・ページネーション対応）。
  - レート制限対応（120 req/min、固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429 と 5xx を再試行）。
  - 401 応答時はリフレッシュトークンから id_token を自動更新して再試行（1 回のみ）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ _to_float / _to_int を実装し、不正フォーマットを安全に扱う。
  - fetched_at を UTC ISO8601 で記録し、データ取得時点を追跡可能に実装（Look-ahead バイアス対策の一環）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得 → 前処理 → raw_news への冪等保存フローを実装（仕様とセキュリティ対策を考慮）。
  - defusedxml を用いた XML パース（XML Bomb 等対策）。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリパラメータソート。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、HTTP スキーム検証、IP/SSRF 対策などを想定した設計。
  - バルク挿入チャンク（_INSERT_CHUNK_SIZE）で SQL 長・パラメータ数を抑制。

- 研究用ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: prices_daily と raw_financials を組み合わせて PER / ROE を計算（最新報告日ベース）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番注文系には依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日ベース想定）。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数丸めで ties 対応）。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research の生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 ≥ 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルを置換（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）して冪等性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算。
    - シグモイド変換、欠損値は中立 0.5 で補完するポリシーを採用。
    - デフォルト重みは StrategyModel に基づく（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定 weights は検証・正規化して適用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3）で BUY シグナルを抑制。
    - BUY 閾値デフォルト 0.60。SELL 条件は (1) ストップロス -8% (2) final_score が閾値未満。
    - 保有株（positions）に対するエグジット判定を実装。売買シグナルを signals テーブルへ日付単位で置換（冪等）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY にランクを連番で再付与。

### Changed
- （初版のため履歴なし）

### Fixed
- （初版のため履歴なし）

### Removed
- （初版のため履歴なし）

### Security
- RSS パーサに defusedxml を採用、受信サイズ上限と URL 正規化で攻撃面を低減。
- J-Quants クライアントの HTTP レスポンス処理で JSON デコードエラーを明示的に扱い、認証失敗時にトークンを安全にリフレッシュする実装。

### Notes / Known limitations
- signal_generator の SELL 条件に記載の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の実装は概ね整っているが、実際の RSS フェッチ処理・DB マッピング周りは外部環境依存のため運用テストが必要。
- DuckDB スキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news など）はこのコードから想定されるが、マイグレーション・スキーマ定義は別途必要。
- zscore_normalize の実装は kabusys.data.stats に委譲（本ログでは実装の詳細は記載なし）。
- 一部関数は外部環境（DuckDB 接続、J-Quants の有効トークン、.env 設定等）に依存するため、実行前に設定と DB スキーマの整備が必要。

## 参考（設計方針の抜粋）
- ルックアヘッドバイアス回避: データ取得時に fetched_at を UTC で記録、計算時は target_date 時点以下のデータのみ参照。
- 冪等性: DB 保存は ON CONFLICT / トランザクションによる日付単位の置換を多用。
- ロバスト性: 不正データをスキップして警告をログ出力、トークン期限切れやネットワークエラーに対するリトライを実装。
- 研究 / 本番の分離: research モジュールは本番発注系に依存しないよう設計。

----

（この CHANGELOG はコードから推測して記載したものであり、実際のリリースノートや設計ドキュメントと差異がある可能性があります。実運用時は追加の確認・補足を推奨します。）