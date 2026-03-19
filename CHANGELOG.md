# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はコードベースからの推測に基づき記載しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコア機能を実装しました（環境設定、データ取得・保存、リサーチ用ファクター計算、特徴量生成、シグナル生成、ニュース収集など）。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ情報（kabusys.__init__）を追加。バージョンは 0.1.0。
  - サブパッケージ公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 環境変数取得用 Settings クラスを追加。J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）やログレベル等のプロパティとバリデーションを提供。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティを提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 時は Retry-After ヘッダを優先。
    - 401 を受けた場合は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止）。
    - ページネーション対応で複数ページを結合して取得。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録（Look-ahead バイアス・トレーサビリティ確保）。
  - DuckDB への保存ユーティリティを実装（raw_prices, raw_financials, market_calendar を想定）。
    - save_*** 系は冪等性を考慮して ON CONFLICT DO UPDATE を使用する実装。
    - 型変換ユーティリティ _to_float / _to_int を追加し、不正データや空値に対する堅牢性を確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニューススクレイピング機能を追加（デフォルトで Yahoo Finance のビジネスカテゴリを想定）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）を実装。
  - XML 解析に defusedxml を使用し XML ベースの攻撃を緩和。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 回避（HTTP/HTTPS スキームの検証や IP チェック等を想定）により安全性向上を意識した設計。
  - 記事 ID を正規化 URL の SHA-256 ハッシュの先頭で生成し冪等性を確保する設計（トラッキングパラメータでの多重登録防止）。
  - バルク INSERT のチャンク処理を導入し DB 負荷を低減。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
    - Volatility: 20日 ATR / atr_pct / avg_turnover / volume_ratio を計算。
    - Value: PER（EPS を用いた株価/EPS）および ROE を計算（raw_financials との結合）。
    - DuckDB 上の prices_daily/raw_financials テーブルを前提に、データ不足時は None を返す堅牢な実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1/5/21 営業日）での将来リターンを計算。
    - IC 計算（calc_ic）: factor と将来リターンの Spearman ランク相関（Information Coefficient）を計算（有効サンプルが 3 未満の場合は None）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す。
    - rank ユーティリティ: 同順位は平均ランクで扱う。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価: 300 円、20 日平均売買代金: 5 億円）を適用。
  - 指定カラム群を Z スコア正規化し ±3 でクリップ（外れ値耐性）。
  - 日付単位で削除→挿入するトランザクション処理により冪等性・原子性を確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を計算して BUY/SELL シグナルを生成する generate_signals を実装。
  - スコア計算:
    - momentum, value, volatility, liquidity, news の重み付けによる統合（デフォルト重みを定義）。
    - 不足値は中立 0.5 で補完し、weights は入力検証後に合計 1.0 へ正規化。
    - Z スコアをシグモイド変換してコンポーネントスコア化。
  - Bear レジーム検出（_is_bear_regime）: ai_scores の regime_score の平均が負かつサンプル数が閾値以上なら BUY を抑制。
  - SELL（エグジット）判定:
    - ストップロス（終値/avg_price - 1 <= -8%）を最優先。
    - final_score が閾値未満（デフォルト 0.60）。
    - 保有銘柄の価格欠損時は SELL 判定をスキップしログ出力。
    - 未実装だが設計で想定している追加エグジット（トレーリングストップ、時間決済）を注記。
  - signals テーブルへの日別置換（DELETE + bulk INSERT）で冪等性・原子性を保証。
  - 生成結果は BUY（ランク付け）と SELL（ランクなし）を分離し、SELL 優先で BUY を除外。

### Security
- defusedxml を用いた XML パース（news_collector）で XML 関連の攻撃を緩和。
- RSS URL 正規化およびトラッキングパラメータ削除により同一記事の多重登録を抑制。
- ニュース受信の最大バイト数制限によりメモリ DoS を軽減する方針を導入。
- J-Quants クライアントのトークンリフレッシュは allow_refresh フラグで無限再帰を防止。

### Reliability / Robustness
- 各種データ保存処理は冪等化（ON CONFLICT DO UPDATE / DO NOTHING 等）を意識した実装設計。
- DuckDB へのトランザクション処理（BEGIN/COMMIT/ROLLBACK）を多用し、失敗時のロールバックと警告ログ出力を実装。
- env ファイルパーサや数値変換ユーティリティは不正入力や欠損値を安全に扱うよう実装。

### Notes / Limitations
- execution（発注）層はパッケージに存在するが具体的な発注ロジックは本スニペットでは未実装／空の状態。
- 一部のエグジット条件（トレーリングストップ、時間決済）は設計に記載されているが positions テーブルの追加情報（peak_price / entry_date 等）が必要なため未実装。
- news_collector の DB 保存周り（INSERT RETURNING 等）や最終的な news→news_symbols の紐付け処理は設計方針として述べられているが、コード断片の範囲では一部を仮定して記載しています。
- 外部依存（DuckDB、defusedxml 等）が必要。

---

今後のリリースでは、execution 層の実装（kabuステーションとの接続・注文管理）、監視（monitoring）・運用周りの強化、さらに追加のファクター・AI スコア連携などを想定しています。必要であればこの CHANGELOG を英語版に翻訳したり、各変更点をより細かく分割したセクション（例: data、research、strategy、infra）で展開できます。ご希望があれば指示してください。