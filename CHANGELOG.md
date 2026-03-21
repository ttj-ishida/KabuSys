CHANGELOG
=========

すべてのリリースは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従います。
このファイルは日本語で書かれており、プロジェクトの重要な変更点・設計上の意図・既知の制限などをまとめています。

最新: Unreleased
----------------

（現在差分はありません）

[0.1.0] - 2026-03-21
-------------------

Added
- 初回公開リリース。日本株自動売買システム「KabuSys」の基礎モジュールを追加。
- パッケージ入口:
  - src/kabusys/__init__.py にてバージョン `0.1.0` と公開 API（data, strategy, execution, monitoring）を定義。
- 環境設定:
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および OS 環境変数からの設定読み込みを実装（プロジェクトルート検出は .git または pyproject.toml を探索）。
    - export KEY=val 形式、クォート付き値、インラインコメント処理等を考慮した行パーサーを実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得用の _require と Settings クラスを提供。以下の必須キー（例）を扱うプロパティを定義:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - システム設定のバリデーション（KABUSYS_ENV の許容値: development / paper_trading / live、LOG_LEVEL の許容値）を実装。
    - DB パス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で提供。
- データ取得・保存:
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（株価日足 / 財務データ / マーケットカレンダー）。
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - HTTP リトライロジック（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ機構を実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を冪等に実装（ON CONFLICT DO UPDATE を使用）。
    - 入力変換ユーティリティ (_to_float / _to_int) を提供し、不正な値は None として扱う。
    - 取得時刻（fetched_at）を UTC ISO8601 で保存し、Look‑ahead bias 防止を意識した設計。
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集・前処理して raw_news に保存するモジュール（設計文書に基づく実装）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）を実装（_normalize_url）。
    - defusedxml を用いた XML の安全パース、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF 対策といった安全対策を設計に組み込み。
    - 挿入はバルクチャンク化してトランザクション内で行い、INSERT RETURNING 等により実際の挿入件数を正確に扱う方針。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。
- リサーチ・ファクター計算:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、ATR比率）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - 計算用の窓幅やスキャン範囲等の定数を定義し、営業日欠損（週末・祝日）に配慮したスキャンバッファを実装。
    - データ不足時は None を返す等、安全に扱う実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を用いず標準ライブラリ＋DuckDB で処理する方針。
  - src/kabusys/research/__init__.py で主要関数を公開。
- 特徴量エンジニアリング:
  - src/kabusys/strategy/feature_engineering.py
    - research で生成された raw ファクターを統合して features テーブルへ保存する処理（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
    - 指数外れ値対策として Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）→ ±3 でクリップを実施。
    - DuckDB トランザクション内で日付単位の置換（DELETE→INSERT）を行い原子性を保証。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用する設計。
- シグナル生成:
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存する generate_signals を実装。
    - momentum/value/volatility/liquidity/news の重み付けをデフォルトで定義（合計 1 に正規化）。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、AI レジームスコアによる Bear 判定（市場レジームが Bear の場合 BUY を抑制）等を実装。
    - エグジット判定（_generate_sell_signals）ではストップロス（-8%）とスコア低下を実装。トレーリングストップ・時間決済は未実装（設計上のTODO として明記）。
    - BUY/SELL の日付単位置換をトランザクションで行い原子性を保証。SELL 優先ポリシー（SELL 対象は BUY から除外）。
- パッケージ戦略:
  - src/kabusys/strategy/__init__.py にて build_features / generate_signals を公開。
- ロギング:
  - 主要処理にログ出力（info/warning/debug）を追加し、運用時のトラブルシュートを容易にする。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- news_collector にて defusedxml を採用し XML 関連の脆弱性（XML Bomb 等）に対処。
- ニュース URL の正規化・トラッキング除去・スキーム検証等で SSRF / 不正 URL のリスクを低減する設計。
- jquants_client で 401 時のトークン自動リフレッシュは allow_refresh フラグにより無限再帰を防止。

Known issues / TODO
- execution パッケージは空（src/kabusys/execution/__init__.py）。実際の発注ロジック・kabuステーション API 連携は未実装。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等が必要。
- news_collector の全文実装（RSS パース → DB 保存のフロー）は設計方針に沿っているが、外部 RSS の多様性・エンコーディング等で追加の調整が必要になる可能性がある。
- DuckDB スキーマ定義（テーブル作成 SQL）は本リリースに含まれないため、利用前に期待テーブル（raw_prices/raw_financials/market_calendar/features/ai_scores/positions/signals/raw_news 等）を作成する必要がある。
- 一部関数はデータ不足時に None を返す仕様（上位での補完や中立値扱いを行う設計）。運用時に None 扱いによる影響を理解しておくこと。

Upgrade notes（他プロジェクトからの移行）
- 環境変数名（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を .env に設定してください。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に実行する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、必要に応じて独自ロード処理を行ってください。
- DuckDB を用いるため、DuckDB Python パッケージが必須です。テーブルスキーマをプロジェクトのドキュメントに従って準備してください。

Authors
- KabuSys 開発チーム（ソースコードの docstring と実装から要約）

Acknowledgements / References
- 本プロジェクトのアルゴリズム説明は StrategyModel.md, DataPlatform.md 等の設計文書を参照して実装されています（ソース内コメント参照）。

[0.1.0]: https://example.com/releases/0.1.0  (注: リンクは必要に応じて置き換えてください)