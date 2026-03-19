Keep a Changelog 準拠の形式で、コード内容から推測した変更履歴を作成しました。バージョンはパッケージの __version__ = "0.1.0" を基に初期リリースとして記載しています。

CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
<https://keepachangelog.com/ja/1.0.0/>

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-19
--------------------

Added
- 基本パッケージ導入
  - パッケージ名: kabusys、バージョン 0.1.0
  - 公開 API: kabusys.strategy.build_features, kabusys.strategy.generate_signals などを __all__ で公開。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装: コメント、export 形式、クォート内エスケープ、インラインコメント処理に対応する堅牢な行パース処理。
  - 読み込みの優先度: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - 設定クラス Settings を提供（J-Quants トークン、kabu API 設定、Slack トークン・チャネル、DB パス、環境 / ログレベル検証等）。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック、未設定必須変数の明示的エラー。

- データ収集・永続化（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - レート制限制御（固定間隔スロットリング、120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）および 408/429/5xx のリトライ対応。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を処理）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等保存用関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - 型安全な数値変換ユーティリティ: _to_float / _to_int。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを想定。

  - ニュース収集（news_collector）
    - RSS から記事収集 → raw_news へ保存（冪等性）。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成しトラッキングパラメータ除去。
    - defusedxml を用いた XML パース（XML Bomb 等への耐性）。
    - SSRF 対策と受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
    - バルク INSERT のチャンク化により SQL パラメータ数上限対策。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - Volatility: ATR（20 日）、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio を計算。
    - Value: PER, ROE を raw_financials と prices_daily から算出。
    - データ不足時の None 扱い、SQL + ウィンドウ関数を活用した効率実装。
  - Feature exploration（feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン、デフォルト [1,5,21]）。
    - IC（calc_ic）: Spearman（ランク相関）計算実装（同位は平均ランク扱い）。
    - ファクター統計サマリ（factor_summary）、rank ユーティリティ。
  - zscore_normalize を用いる設計思想の統合（kabusys.data.stats を参照する設計）。

- 戦略層（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）適用。
    - 指定列に対する Z スコア正規化と ±3 でのクリップ。
    - 日付単位での置換（DELETE + INSERT をトランザクションで実行し冪等性・原子性を保証）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントスコアはシグモイド変換および欠損時は中立 0.5 で補完。
    - デフォルト重みを用いた重み付け合算（デフォルト合計を 1.0 に再スケールするロジックあり）。
    - BUY の閾値はデフォルト 0.60、STOP_LOSS は -8%。
    - Bear レジーム（ai_scores の regime_score 平均が負）検出時は BUY を抑制。
    - 保有ポジションに対する SELL ルール（ストップロス・スコア低下）を実装。売却優先ポリシーにより SELL 対象は BUY から除外。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。

Changed
- （初回リリースのため「Changed」は特になし）

Fixed
- （初回リリースのため「Fixed」は特になし）

Security
- ニュースパーサ: defusedxml による安全な XML パースを採用。
- RSS収集: HTTP スキームの検証、受信サイズ制限、トラッキングパラメータ除去等の入力サニタイズを考慮。
- J-Quants クライアント: 401 自動リフレッシュの制御やネットワーク例外に対する堅牢なリトライ実装を導入。

Notes / Observations
- DuckDB を主要な計算・永続化ストレージとして想定しており、テーブル名（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar, raw_news 等）に依存する実装になっています。
- Look-ahead バイアス防止（fetched_at の UTC 記録、target_date 時点での参照のみを行う設計）が一貫して意識されています。
- 一部未実装・将来対応予定: signal_generator 内でのトレーリングストップや時間決済（positions に peak_price/entry_date が必要）。

Deprecated
- なし

Removed
- なし

Acknowledgments
- 初期リリースとして、データ収集、リサーチ、特徴量作成、シグナル生成の主要機能を実装。今後は execution 層（発注 API 統合）や監視（monitoring）等の統合が想定されます。

もし他に記載したい形式（日時の取り扱い、より細かい変更カテゴリ分け、英語併記など）があれば指示ください。