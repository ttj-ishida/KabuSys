CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
リンクや参照は主にモジュール／関数名を用いています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-20
--------------------

Added
- 全体
  - 初回公開リリース。パッケージバージョンは 0.1.0（src/kabusys/__init__.py）。
  - DuckDB を中心としたデータパイプライン・研究・戦略・実行層の基盤を実装。

- 環境設定（src/kabusys/config.py）
  - .env/.env.local を自動ロードする仕組みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない自動ロードを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env パーサーの堅牢化：export 形式、クォート内のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）および既定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）を管理。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）。

- データ取得 / 保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（認証、ページネーション、取得関数）。
  - 固定間隔スロットリングによるレート制限対応（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回）と HTTP 状態コード別のハンドリング（408/429/5xx の再試行）。
  - 401 受信時のリフレッシュトークンからの自動 ID トークン再取得を組み込み、1 回のみ再試行。
  - ページネーション対応の fetch_* 関数：
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数（冪等実装、ON CONFLICT DO UPDATE）：
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - データ変換ユーティリティ（_to_float / _to_int）を実装し、入力データのノイズに寛容に対応。
  - レスポンス JSON のデコード失敗や HTTP エラーに対する適切なログ・例外処理。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集機能を実装（デフォルトは Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ対策：
    - defusedxml を使用して XML 攻撃を回避。
    - URL の正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - HTTP/HTTPS スキーム以外の URL を拒否する方針（SSRF 緩和）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によりメモリ DoS を緩和。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）等で冪等性を確保する設計（仕様記載）。
  - DB 保存はバルク挿入をチャンク化（_INSERT_CHUNK_SIZE）し、トランザクションをまとめて実行。ON CONFLICT DO NOTHING 等で重複を防止。
  - テキスト前処理（URL 除去、空白正規化）を想定したユーティリティを提供。

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum（1/3/6 か月のモメンタム、200 日移動平均乖離）
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - calc_value（最新財務データ取得と PER/ROE 計算）
    - DuckDB SQL を多用し、営業日（連続レコード数）ベースのホライズン設計。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一度に計算）
    - calc_ic（Spearman の ρ による IC 計算。ties を平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
    - rank（同順位を平均ランク化する実装）
  - pandas 等の外部ライブラリに依存しない純 Python 実装を志向。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装：
    - research の calc_* 関数から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム群を zscore 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクション）。
    - 価格参照は target_date 以前の最新価格を用いることで休場日対応。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装：
    - features と ai_scores を統合し、各コンポーネント（momentum/value/volatility/liquidity/news）を算出。
    - Z スコア → シグモイド変換 → 重み付き合算で final_score を計算（デフォルト重みは StrategyModel.md に準拠）。
    - weights のバリデーション・フォールバック処理（合計が 1.0 になるよう正規化）。
    - Bear レジーム判定（AI の regime_score 平均が負）により BUY を抑制。
    - BUY（threshold デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）を生成。
    - SELL 優先方針（SELL 対象は BUY から除外しランク再付与）。
    - signals テーブルへ日付単位での置換（トランザクション + バルク挿入）。

- パッケージ公開インターフェース
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research/__init__.py で主要関数をエクスポート。
  - package __all__ に data/strategy/execution/monitoring を含む（execution パッケージは空の __init__ を用意）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known issues / TODO
- _generate_sell_signals 内の未実装条件:
  - トレーリングストップ（peak_price の追跡）および時間決済（保有 60 営業日超過）は positions テーブルに peak_price / entry_date を持たせる必要があり、現時点では未実装。
- execution / monitoring 層は今後の実装予定（現状は戦略・データ・研究にフォーカス）。
- news_collector の詳細な RSS パーサー実装（記事フィールドマッピング等）は追加実装が必要（現在は設計・ユーティリティ中心の実装）。
- 大量データ運用時の最適化（DuckDB の VACUUM / パーティショニング等）は別途検討予定。

Migration / Usage notes
- 自動 .env 読み込みを抑止したいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 既定値:
  - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
  - DUCKDB_PATH: "data/kabusys.duckdb"
  - SQLITE_PATH: "data/monitoring.db"
  - LOG_LEVEL: "INFO"
  - KABUSYS_ENV: "development"（有効値: development, paper_trading, live）
- DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る関数群（build_features / generate_signals / calc_* / fetch/save 等）が多いため、呼び出し側で接続管理とテーブルスキーマ準備を行ってください。

Acknowledgements / References
- 実装は各モジュール内の docstring（StrategyModel.md / DataPlatform.md 相当の設計ノート）に従っています。詳細な設計仕様・ドキュメントはリポジトリ内のドキュメント（未同梱の場合は今後追加予定）を参照してください。