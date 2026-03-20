# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

現在版: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パブリック API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ に公開。

- 設定 / 環境変数管理
  - 環境変数/.env 読み込みモジュールを実装（src/kabusys/config.py）。
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出して .env / .env.local を読み込む（CWD に依存しない）。
    - 複雑な .env のパースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須設定取得用 helper _require と Settings クラスを提供。
    - 主要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルトパス（DUCKDB_PATH, SQLITE_PATH）を定義。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と補助プロパティ（is_live / is_paper / is_dev）を提供。

- データ取得 / 永続化（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライ戦略（指数バックオフ、最大3回）。HTTP 408/429/5xx に対する再試行。
    - 401 Unauthorized 受信時にリフレッシュトークンで自動的に ID トークンを更新して 1 回だけリトライ。
    - ページネーション対応のデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - 取得データを DuckDB に冪等保存する save_* 系関数（raw_prices / raw_financials / market_calendar）を実装。ON CONFLICT DO UPDATE による上書き。
    - データ変換ユーティリティ（_to_float, _to_int）を提供。
    - fetched_at は UTC で記録し、Look-ahead バイアスのトレーサビリティを確保。

- ニュース収集
  - RSS ベースのニュース収集モジュール（src/kabusys/data/news_collector.py）を実装。
    - デフォルト RSS ソース（Yahoo Finance のビジネス RSS）を定義。
    - URL の正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
    - 受信サイズ上限（10MB）や defusedxml による XML 攻撃対策、SSRF 回避等の安全対策を備える設計。
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - バルク INSERT のチャンク処理や ON CONFLICT DO NOTHING による冪等保存。

- 研究用 / ファクター計算
  - 研究向けモジュールを追加（src/kabusys/research/）。
    - factor_research.py:
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR、出来高比率、20 日平均売買代金）、バリュー（PER、ROE）を SQL + Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB のウィンドウ関数を活用して営業日ベースの算出とデータ不足時の None 扱いを行う。
    - feature_exploration.py:
      - 将来リターン計算（calc_forward_returns、複数ホライズン対応、1/5/21 日デフォルト）。
      - IC（Information Coefficient）算出（Spearman の ρ）calc_ic、ランク変換 util rank、factor_summary による統計要約を実装。
    - research パッケージの __all__ を整備してユーティリティを公開。
    - 研究モジュールは外部ライブラリ（pandas 等）に依存しない実装方針。

- 特徴量エンジニアリング / 戦略
  - feature_engineering.py:
    - research モジュールが出力する生ファクターを結合・ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用、Z スコア正規化（±3 クリップ）して features テーブルへ日付単位で UPSERT（冪等）する build_features を実装。
    - DuckDB トランザクションを用いた原子的な日付置換を実装。
  - signal_generator.py:
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ書き込む generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算、シグモイド変換、重み付けの取り扱い（デフォルト重みとユーザ指定のマージ、合計の正規化）、閾値による BUY 判定（デフォルト 0.60）を実装。
    - Bear レジーム検知（AI の regime_score の平均が負の時に BUY を抑制）を実装。
    - 保有ポジションのエグジット判定（ストップロス: -8% 以下、スコア低下）を実装。positions / prices_daily を参照。
    - SELL 優先ポリシー（SELL 対象銘柄は BUY から除外）や日付単位の signals テーブル置換（トランザクション＋バルク挿入）を実装。
    - 一貫してルックアヘッドバイアス防止（target_date 時点のデータのみ使用）を設計方針に採用。

- ロギング・エラーハンドリング
  - 各モジュールで適切なログレベル（info/debug/warning）を使用。
  - DB トランザクションにおける例外で ROLLBACK を試行し、失敗時に警告を出す実装を追加。

### 既知の制約 / TODO
- signal_generator のエグジット条件について、コメントで未実装の条件を明示:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加情報が必要で、現バージョンでは未実装。
- execution パッケージの実装は空（発注層との接続は現時点では実装がない）。
- news_collector の RSS 取得・パースのエンドツーエンド処理（サードパーティ RSS の個別検証等）は今後の改善対象。
- 一部ユーティリティ（例: zscore_normalize）は data.stats に依存しているが、実装詳細は該当ファイル参照のこと。

### セキュリティ (Security)
- defusedxml を利用して XML ベースの攻撃を軽減。
- news_collector で受信サイズ上限・SSRF の基本対策を導入。
- J-Quants クライアントはトークン自動リフレッシュとキャッシュを実装。ただし、環境変数の取り扱い・シークレット管理はユーザ側で適切に行う必要がある（Settings を参照）。

---

変更履歴は今後のリリースで更新します。バグ報告、改善提案は issue を作成してください。