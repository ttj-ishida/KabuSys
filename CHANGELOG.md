# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期リリースの変更履歴です。

バージョン番号はパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20
初期リリース。主要コンポーネントはデータ収集・保存、研究用ファクター計算、特徴量作成、シグナル生成、環境設定ユーティリティ、ニュース収集など、国内株の自動売買ワークフローを構成する機能を含みます。

### Added
- パッケージ初期設定
  - パッケージのメタ情報（kabusys.__init__）を追加。公開 API: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 環境変数・設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（__file__ ベースで CWD に依存しない）。
  - .env パーサの実装:
    - コメント行・空行・export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無し値のインラインコメント処理（# の前に空白/タブがある場合をコメントとみなす）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（J-Quants リフレッシュトークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境・ログレベル検証等）。
  - 環境変数必須チェック（未設定時は ValueError を送出）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 発生時はリフレッシュトークンで ID トークンを再取得して 1 回リトライ（無限再帰防止ロジックあり）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスの可視化を支援。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ挿入（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへ挿入（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar テーブルへ挿入（ON CONFLICT DO UPDATE）。
  - データ変換ユーティリティ: 型変換関数 _to_float / _to_int（float 文字列 → int の安全変換対応）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集フローを実装（デフォルトに Yahoo Finance のビジネス RSS を設定）。
  - XML パースに defusedxml を使用して XML ベース攻撃を軽減。
  - URL 正規化機能（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーでソート）。
  - 受信サイズ上限（10 MB）や HTTP スキーム検証などの安全対策。
  - 挿入はバルクでチャンク処理し、冪等性のため ID を正規化 URL の SHA-256 で生成する設計（コメントに記載）。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING を想定）、news_symbols と銘柄紐付けの設計を記載。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - ボラティリティ/流動性: 20日 ATR、atr_pct（ATR/価格）、avg_turnover、volume_ratio を計算。
    - バリュー: 最新の raw_financials を参照し per（株価/EPS）と roe を計算。
    - SQL ベースで DuckDB の prices_daily / raw_financials を参照して算出。データ不足時は None を返す。
  - ファクター探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（ランクの平均ランク処理・同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
    - ランク関数（rank）は丸め(12 桁)で ties を検出し平均ランクを与える実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究側で計算した生ファクターを統合・正規化して features テーブルへ UPSERT（ターゲット日単位で削除→挿入、トランザクションで原子性を保証）。
  - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
  - 正規化は zscore_normalize（kabusys.data.stats から利用）、正規化後に ±3 でクリップして外れ値の影響を抑制。
  - per は正規化対象外（逆数スコア化等を想定するコメントあり）。
  - 冪等性対応：target_date の既存レコードは削除してから挿入。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ書き込む（target_date 単位で置換、トランザクションで原子性保証）。
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news を計算（シグモイド変換や逆転処理等を組み合わせ）。
    - 欠損コンポーネントは中立値 0.5 で補完。
  - 重み処理: デフォルト重みを持ち、ユーザー重みを検証してマージ・正規化（負値・非数値・未知キーは無視）。合計が 1.0 でない場合は再スケール。
  - Bear レジーム検出: ai_scores の regime_score 平均が負なら Bear（十分なサンプル数が必要）。
  - BUY 条件: final_score >= threshold（デフォルト 0.60）。Bear レジーム時は BUY を抑制。
  - SELL 条件（エグジット判定）:
    - ストップロス: 終値 / avg_price - 1 < -8%（優先判定）
    - スコア低下: final_score が閾値未満
    - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - 保有ポジションに関する未実装機能（コメントで明示）: トレーリングストップ、保持日数による時間決済など。
  - signals テーブルへの書込時、SELL 対象銘柄は BUY から除外しランクを再付与（SELL 優先ポリシー）。

### Changed
- （初期リリースのためなし）

### Fixed
- （初期リリースのためなし）

### Security
- defusedxml の使用、受信サイズ制限、URL スキーム検証、SQL 側での PK チェックなど、外部入力に対する基本的な安全対策を実施。

### Known limitations / Notes / TODO
- シグナルの一部エグジット条件（トレーリングストップ、時間決済）は未実装でコメントとして保留。
- news_collector の記事 ID/銘柄紐付けや raw_news スキーマの詳細な実装（INSERT RETURNING 等）はコメントで設計方針が示されているが、実際のテーブルスキーマ依存で追加実装が必要。
- J-Quants クライアントのリトライ対象ステータスやリトライ回数、RateLimiter は固定実装（要調整可能）。
- settings.env / log_level の検証は厳格に行うため、既存環境変数の値が許容範囲外だと ValueError を投げる（運用時に .env.example を参照すること）。
- DuckDB テーブルスキーマ（features, signals, raw_prices, raw_financials, market_calendar, ai_scores, positions など）は外部で定義されている前提。スキーマに依存するため導入時にスキーマ整備が必要。

---

参考: 上記はソースコード内の docstring / コメント・実装から推測して作成しています。実際のリリースノートや運用手順はプロジェクトの README / ドキュメントと照合してください。