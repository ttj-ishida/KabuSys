CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]
-------------

- 今後の課題・予定
  - execution 層（発注実行）および monitoring モジュールの実装・統合。
  - ポジション管理に必要な peak_price / entry_date を positions テーブルに持たせ、
    トレーリングストップや時間決済（保有日数による決済）を実装する。
  - AI スコアの運用改善（サンプル不足時の扱い、レジーム判定の微調整）。
  - 単体テスト・統合テストの追加（ネットワーク I/O を伴う箇所のモック整備）。

0.1.0 - 2026-03-20
------------------

Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。読み込み順: OS環境変数 > .env.local > .env。
  - プロジェクトルート探索は __file__ から .git または pyproject.toml を探索して行い、CWD に依存しない実装。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - 読み込み時の上書き制御（override と protected set）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - Settings クラスで設定値をラップ（必須キーのチェック、デフォルト値、enum 検証: KABUSYS_ENV / LOG_LEVEL、パスの Path 化）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンを使って id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key の扱い）。
    - 取得時の fetched_at を UTC ISO 形式で記録し、look-ahead バイアス追跡を可能に。
  - データフェッチ関数を追加: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB 保存関数を追加（冪等性を担保する ON CONFLICT / DO UPDATE 使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 入力検証と変換ユーティリティ実装: _to_float / _to_int により安全に変換。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得・正規化して raw_news に保存する基盤を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）。
    - メモリ DoS 対策のため受信最大バイト数制限（MAX_RESPONSE_BYTES）。
    - 安全設計: defusedxml 利用、HTTP スキーム検証、SSRF 考慮。
    - 冪等性: 記事ID は正規化 URL の SHA-256 ハッシュ先頭で生成（重複防止）。
    - バルク挿入のチャンク化を実装（パフォーマンス／SQL パラメータ制限対策）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ）。

- リサーチ（kabusys.research）
  - ファクター計算群を実装・公開:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - calc_value: PER, ROE（raw_financials と prices_daily を組合せ）。
  - 解析ユーティリティ:
    - zscore_normalize（kabusys.data.stats から再公開）。
    - calc_forward_returns: 指定日から各ホライズン先の将来リターン取得（複数ホライズン対応、SQL 内で一括取得）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。データ不足（<3）なら None を返す。
    - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランク扱い（丸めにより ties 検出の精度を担保）。
  - 実装方針: DuckDB 接続のみ使用、外部ライブラリ（pandas 等）非依存。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research モジュールで計算した生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - ユニバース閾値: 最低株価 300 円、最低 20 日平均売買代金 5 億円を適用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ日付単位で置換保存。
    - コンポーネントスコアを計算するユーティリティを実装（momentum/value/volatility/liquidity/news）。
      - momentum: momentum_20、momentum_60、ma200_dev のシグモイド平均。
      - value: PER を 20 を基準に変換（PER が小さいほど高スコア）。
      - volatility: atr_pct の Z スコアを反転してシグモイド化（低ボラ = 高スコア）。
      - liquidity: volume_ratio をシグモイド化。
      - news: ai_score をシグモイド化、未登録は中立扱い。
    - 重み付け: デフォルト重みを提供（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー重みは検証・正規化（非数値/負値/未知キーは無視）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、かつサンプル数が閾値以上の場合に BUY を抑制。
    - SELL 条件（既実装）
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
    - SELL 条件（未実装・計画）
      - トレーリングストップ（peak_price 必要）
      - 時間決済（保有 60 営業日超過）
    - デフォルト BUY 閾値: final_score >= 0.60
    - signals テーブルへは BUY/SELL を分けて挿入し、SELL を優先して BUY から除外するポリシーを採用。

- API エクスポート
  - strategy パッケージの __all__ に build_features / generate_signals を追加。
  - research パッケージの各関数を再エクスポート。

Changed
- 初回リリースのため履歴なし。

Fixed
- 初回リリースのため履歴なし。

Security
- news_collector で defusedxml を用いた XML パースと受信サイズ制限を導入。
- J-Quants クライアントでトークン管理・自動リフレッシュ、ネットワークエラーの扱いを厳密に実装。

Notes / Implementation details
- 冪等性: DuckDB への書き込みは可能な限り ON CONFLICT / DO UPDATE または日付単位の DELETE + INSERT（トランザクション）で原子性を確保。
- Look-ahead バイアス対策: 取得データに fetched_at を付与して「データをいつ知り得たか」を追跡可能に。
- 外部依存の最小化: research モジュールは標準ライブラリと duckdb のみで実装（pandas などには依存しない）。
- ロギング: 各主要処理で logger を使用して警告・情報・デバッグを出力。

免責事項
- 本 CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際の変更履歴・コミットログとは差異がある場合があります。