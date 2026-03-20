# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
日付はリリース日を示します。

## [Unreleased]

- 今後のリリースで対応予定の未実装・改善項目を tracked します（下部の「既知の制限」を参照）。

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース。
- 基本モジュールを実装:
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機構（プロジェクトルートは .git / pyproject.toml を探索）。
    - 高度な .env パーサ（コメント・export プレフィックス・クォート／エスケープ対応）。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 必須環境変数取得時のチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - 設定値検証（KABUSYS_ENV / LOG_LEVEL の制約）。
  - データ取得・保存（kabusys.data）
    - J-Quants API クライアント（jquants_client）
      - レート制限対応（120 req/min 固定間隔スロットリング）。
      - 冪等かつ耐障害性の高い HTTP 層（リトライ: 指数バックオフ、408/429/5xx を再試行、最大 3 回）。
      - 401 発生時のリフレッシュトークンによる自動トークン更新（1 回のみ再試行）。
      - ページネーション対応（pagination_key を用いたループ）。
      - DuckDB への保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）:
        - PK 欠損行のスキップと警告。
        - ON CONFLICT DO UPDATE による冪等保存。
        - fetched_at を UTC で記録（Look-ahead バイアス追跡用）。
      - 型変換ユーティリティ（安全な _to_float / _to_int）。
    - ニュース収集モジュール（news_collector）
      - RSS フィード収集の基盤実装（デフォルトに Yahoo Finance）。
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去、スキーム/ホスト小文字化）。
      - 安全性対策: defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF を念頭においた URL 検証方針（実装注記あり）。
      - 記事ID の生成方針（URL 正規化後の SHA-256 の先頭 32 文字を想定して冪等性を確保する設計）。
      - バルク挿入のチャンク化（INSERT チャンクサイズ上限）。
  - リサーチ/ファクター計算（kabusys.research）
    - ファクター計算モジュール（factor_research）
      - Momentum（1M/3M/6M、MA200 乖離率）、Volatility（20 日 ATR、ATR %、20 日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials から算出。
      - 営業日ベースのラグ計算、ウィンドウサイズに基づく欠損処理。
    - 研究支援ユーティリティ（feature_exploration）
      - 将来リターン計算（複数ホライズン、1/5/21 日デフォルト）。
      - IC（Spearman の ρ）計算、ランク処理（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）。
      - pandas 等外部依存を持たない実装。
    - research パッケージの公開 API を整理（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。
  - 戦略層（kabusys.strategy）
    - 特徴量エンジニアリング（feature_engineering.build_features）
      - research の生ファクターを結合・ユニバースフィルタ適用（最低株価: 300 円、20 日平均売買代金 >= 5 億円）。
      - 指定カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 にクリップ。
      - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
      - ルックアヘッドバイアス防止のため target_date 時点のみ参照する設計。
    - シグナル生成（signal_generator.generate_signals）
      - features と ai_scores を統合して最終スコア（final_score）を算出（デフォルトの重みは momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）。
      - 重みの入力検証と合計 1.0 への再スケーリング処理（不正値は無視、負値や NaN/Inf を弾く）。
      - スコア変換ユーティリティ（Z スコア -> sigmoid -> 0..1）。
      - Bear レジーム検知（ai_scores の regime_score 平均が負のとき BUY を抑制、サンプル不足時は判定しない）。
      - BUY シグナル閾値デフォルト 0.60、STOP-LOSS -8%（positions と price を参照して SELL を生成）。
      - signals テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
  - パッケージ公開インターフェース
    - kabusys.__init__ にてバージョン情報と主要サブパッケージをエクスポート。

Fixed
- データ保存処理で PK 欠損行をスキップし、スキップ件数をログに残すようにしてデータ品質を担保。

Security
- news_collector で defusedxml を採用し XML 関連攻撃（XML Bomb など）に対処。
- ニュース取得時の受信サイズ制限（10MB）によりメモリ DoS を軽減。
- J-Quants クライアントでトークンリフレッシュを制御し無限再帰を回避。
- DB に保存する際に fetched_at を UTC で記録しデータ取得時刻のトレーサビリティを確保（Look-ahead バイアス対策）。

Notes / 設計上の注記
- 研究モジュール / 戦略モジュールはいずれも発注・execution 層に直接依存しない設計。
- DuckDB を中心としたデータフローを想定（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等のテーブル設計が前提）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では無効になる可能性あり（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御）。

Known limitations / 未実装事項
- signal_generator 内の一部エグジット条件は未実装（コード内コメント参照）:
  - トレーリングストップ（peak_price を参照するため positions テーブルに peak_price / entry_date が必要）
  - 保有期間による時間決済（保有 60 営業日超過）
- value ファクターで PBR・配当利回りは未実装。
- news_collector の一部実装（SSRF 的チェックや完全な URL 検証・ブラックリスト）は設計方針として記載されているが、実運用での追加検証が必要。
- execution パッケージは空のまま（発注ロジックは別途実装を予定）。

Acknowledgements
- 本リリースは初期版のため、内部 API の安定化、追加のユニットテスト、CI/配布周りの整備を順次進めます。

-----------

（必要であれば、各モジュールごとの詳細な変更履歴や今後のロードマップも追記できます。どの粒度で記載するか指示してください。）