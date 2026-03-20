CHANGELOG
=========

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマットの慣例:
- 追加: Added
- 変更: Changed
- 修正: Fixed
- 削除: Removed
- 非推奨: Deprecated
- セキュリティ: Security

Unreleased
----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-20
--------------------

初期リリース — 日本株自動売買システム "KabuSys" の基礎機能群を実装。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブモジュール: data, strategy, execution（execution は空の初期化ファイル）、monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込むユーティリティを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しないロードを実現。
  - .env 読み込みの優先順位: OS環境変数 > .env.local > .env。既存OS環境変数は保護（protected）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）および settings オブジェクトを提供。
  - .env パースの堅牢化（コメント処理、export プレフィックス、クォート内のバックスラッシュエスケープ等に対応）。

- データ取得 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 汎用リクエスト処理（JSON デコード、ページネーション対応）。
    - 冪等性を考慮した DuckDB 保存関数（raw_prices / raw_financials / market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE を使用。
    - リトライ処理（指数バックオフ、最大3回、ステータス 408/429/5xx を対象）。
    - 401 Unauthorized 発生時にリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
    - fetched_at を UTC ISO8601 で記録し、データ取得時点の可観測性を確保。
    - 型変換ユーティリティ (_to_float / _to_int) により外部データの不整合に耐性を持たせる。

- データ収集 (kabusys.data.news_collector)
  - RSS フィードからニュース収集するモジュールの実装（初期ソースとして Yahoo Finance の RSS を定義）。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホストの小文字化、フラグメント削除、クエリのソート）。
  - XML 実装に defusedxml を使用して XML Bomb 等の攻撃を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）やバルク INSERT チャンクサイズを設定し DoS を軽減。
  - 重複回避（記事ID は正規化 URL のハッシュ等で冪等性を担保）を想定した実装方針。

- 研究モジュール (kabusys.research)
  - factor_research:
    - モメンタム、ボラティリティ、バリュー系ファクター計算を実装（prices_daily / raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）、atr_20 / atr_pct、avg_turnover / volume_ratio、per / roe などを計算。
    - 営業日欠損に対処するためスキャン範囲にカレンダーバッファを導入。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）および IC（calc_ic）計算、rank/統計サマリー (factor_summary) を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究環境で計算した生ファクターを正規化・合成して features テーブルへ保存する処理を実装（build_features）。
  - ユニバースフィルタ（最低株価300円、20日平均売買代金 5億円）を適用。
  - Zスコア正規化（kabusys.data.stats の zscore_normalize を使用）と ±3 にクリップして外れ値を抑制。
  - 日付単位での置換（DELETE+INSERT）をトランザクションで実行し冪等性・原子性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features / ai_scores / positions を参照して売買シグナルを生成する generate_signals を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算、sigmoid 変換、欠損コンポーネントは中立値 0.5 で補完。
  - デフォルト重みとしきい値（デフォルト threshold=0.60）を実装。ユーザー指定 weights の検証と合計1への正規化を実施。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
  - エグジット条件（ストップロス -8% および final_score の低下）に基づく SELL シグナル生成。
  - signals テーブルへの日付単位置換をトランザクションで実行し冪等性を確保。
  - 実行ログ（INFO/DEBUG/警告）を適切に出力。

Changed
- （初回リリースのため過去バージョンからの変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- news_collector で defusedxml を使用し XML 関連の脆弱性を軽減。
- ニュース収集時に受信サイズ上限を設定してメモリDoSを緩和。
- URL 正規化時にトラッキングパラメータ削除やスキームチェックを行う方針を明記（SSRF/追跡パラメータ対策）。
- J-Quants クライアントは 401 でトークンリフレッシュを行い、無限再帰を防ぐため allow_refresh フラグを導入。

Removed / Deprecated
- （初回リリースのため該当なし）

Notes / Known limitations / TODO
- signal_generator のエグジット条件として記載の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date などが必要。
- news_collector の記事→銘柄紐付け（news_symbols）などの処理は方針記載のみで、結合ロジックの詳細実装は今後の課題。
- DuckDB 側で期待するテーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）が存在する前提。スキーマ管理やマイグレーション機能は本リリースに含まれない。
- 一部関数は外部 API（kabu API 等）への接続や注文発注ロジックを持たない（execution 層での実装を想定）。
- エラー時のロギングやリトライの挙動は実装済みだが、実運用での監視・アラート機能は monitoring モジュールでの追加を予定。

開発中の方向性
- execution 層（kabuステーションとの注文連携）、monitoring（Slack 通知等）、および news → シンボル紐付けの強化を優先。
- ストラテジーの実運用向け堅牢化（例: フェイルセーフ、シミュレーション/ペーパー取引モードの拡充）を計画。

Contributing
- バグ報告、機能提案、プルリクエストは歓迎します。README や開発ガイドに沿ってください。

-----

（この CHANGELOG はコードベースの実装内容から推測して作成しています。細かい実装意図や追加仕様がある場合は適宜更新してください。）