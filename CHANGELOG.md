CHANGELOG
=========
すべての重要な変更点は Keep a Changelog の形式に従って記録します。
本ファイルは日本語で記載します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 破壊的変更 (Breaking Changes)
- 保留 / 未実装や既知の制約 (Known issues / Notes)

[Unreleased]
------------

(未リリースの変更はここに記載してください)

[0.1.0] - 2026-03-20
-------------------

Added
- 基本パッケージ構成を追加
  - kabusys パッケージの公開インターフェースを定義 (data, strategy, execution, monitoring)
  - パッケージバージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（OS 環境変数優先、.env.local が .env を上書き）
  - プロジェクトルート判定ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）
  - .env パーサを実装:
    - コメント/空行の無視、export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント判定（直前が空白/タブの場合のみ）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（プロパティ経由で設定取得）
    - 必須変数のチェック (_require)（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
    - 値検証: KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL（DEBUG/INFO/...）
    - DB パス既定値（duckdb/sqlite）と Path 型での扱い
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- データ取得 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - 固定間隔の RateLimiter（120 req/min に対応）
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）
    - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ
    - ページネーション対応とページキーの重複防止
    - JSON デコードエラー時の明示的な例外
  - 高レベル API:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - DuckDB への保存関数（冪等実装）
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE
    - 保存前の型変換ユーティリティ (_to_float / _to_int)
    - PK 欠損行のスキップとログ警告

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事取得・正規化・保存処理（raw_news / news_symbols を想定）
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等対策）
    - HTTP/HTTPS スキームの検証（SSRF 緩和）
    - 受信最大バイト数制限 (MAX_RESPONSE_BYTES)
    - トラッキングパラメータ除去（utm_*, fbclid 等）と URL 正規化（スキーム/ホスト小文字化、フラグメント削除、クエリソート）
  - 挿入処理の最適化:
    - SHA-256（先頭32文字）ベースの記事 ID 生成による冪等化
    - バルク INSERT のチャンク化処理（_INSERT_CHUNK_SIZE）

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: prices_daily / raw_financials を用いたファクター計算
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日窓チェック）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播制御）
    - calc_value: per, roe（raw_financials の最新報告を参照）
    - 期間スキャンのバッファ設計（週末祝日対応のカレンダーバッファ）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンに対する将来リターン計算（1,5,21 日がデフォルト）と SQL 一括取得
    - calc_ic: スピアマン情報係数（ランク相関）計算（サンプル数閾値: 3）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで扱うランク付け実装（round(v, 12) で ties 対応）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research モジュールからの生ファクター取得（calc_momentum/calc_volatility/calc_value）
    - ユニバースフィルタ: 最低株価(_MIN_PRICE=300 円)・20 日平均売買代金(_MIN_TURNOVER=5e8) を適用
    - 正規化: zscore_normalize を利用し対象列を Z スコア化、±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入、冪等性）
    - 欠損や非有限値の処理を明確化

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を結合し、複数のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）
    - コンポーネントの補完ポリシー: None は中立値 0.5 で補完
    - 重みの検証と再スケール（未知キーや負値・非数値は無視）
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）
    - SELL シグナル（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）
      - final_score が閾値未満
      - 価格欠損時は判定をスキップし警告出力
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入、SELL を優先して BUY から除外）
    - ログ出力で生成数を記録

Changed
- （初回リリースのため過去の変更はなし）

Fixed
- （初回リリースのため過去の修正はなし）

Breaking Changes
- なし（初回リリース）

Known issues / Notes / TODO
- signal_generator._generate_sell_signals の未実装/保留のエグジット条件:
  - トレーリングストップ（peak_price 情報が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
  - これらは positions テーブルに追加のメタデータ（peak_price / entry_date 等）が必要
- news_collector の残り実装:
  - 実際の RSS フィード取得ループや DB への具体的な INSERT/紐付け処理は本コード片の続きに依存（present file の続きが必要）
- J-Quants クライアント:
  - リトライ対象ステータス・挙動は現状で設計通りだが、実運用では API の仕様変化（429 Retry-After の形式等）に注意
- 自動 .env ロード:
  - プロジェクトルートが特定できない場合は自動ロードをスキップするため、配布形態によっては KABUSYS_DISABLE_AUTO_ENV_LOAD を明示的に設定する必要がある
- テスト・ドキュメント:
  - ユニットテストやモックを用いた外部 API 呼び出しのテストは別途用意する想定（現状コードベースは動作設計を含むがテストコードは含まれていない）

開発者向けメモ
- 必須環境変数の一覧:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベース既定パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- ログレベルと環境:
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

クレジット
- 初期設計・実装においては、データ収集・リサーチ・特徴量整形・シグナル生成の各層を明確に分離し、
  ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）と冪等性・トランザクション安全性を重視しました。

--- 
（以降のバージョンでは、実運用向けの細かなチューニング、追加のエグジット条件、ニュース→銘柄紐付けの強化、モニタリング/実行層の実装・テストを予定しています。）