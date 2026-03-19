Keep a Changelog 準拠の CHANGELOG.md を以下に作成しました。パッケージの __version__ が 0.1.0 のため、初回リリース 0.1.0 を記載しています。コードから推測できる実装・設計上の注意点や未実装機能（TODO）も記載しています。

CHANGELOG.md
=============

すべての変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- 次回リリースに向けた変更点は無し（現状では 0.1.0 が初版）。

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 行パーサは export プレフィックス、クォート値（エスケープ処理含む）、インラインコメント処理などに対応。
  - 必須環境変数取得ヘルパー（_require）と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境名/ログレベル判定、is_live/is_paper/is_dev）。
  - env / log_level の入力検証（許容値以外は ValueError）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（認証、ページネーション対応）。
  - レートリミッタ（120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 受信時はトークン自動リフレッシュを行い1回リトライ。
  - ページネーションキー共有のためのモジュールレベル token キャッシュを実装。
  - fetch_* 関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - DuckDB に対する冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT を使ったアップサート処理、fetched_at の UTC タイムスタンプ記録。
  - 入力変換ユーティリティ (_to_float / _to_int)。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集基盤を実装（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化（トラッキングパラメータ除去、クエリ排序、スキーム/ホスト小文字化、フラグメント削除）。
  - セキュリティ配慮（defusedxml を利用して XML Bomb 等に対応、受信サイズ上限の設定）。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - DB へのバルク挿入・チャンク処理や INSERT RETURNING を意識した実装（パフォーマンスと正確性の両立）。

- リサーチ機能（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足チェック）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - calc_value（最新財務データと株価から PER / ROE を算出、raw_financials からの最新レコード取得）
    - SQL ウィンドウ関数を活用した効率的な集計と欠損制御
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得、horizons 検証）
    - calc_ic（Spearman の ρ による情報係数計算、サンプル閾値チェック）
    - factor_summary（基本統計量: count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランクを割り当てる実装。丸めで ties の漏れを防止）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールから生ファクター収集→ユニバースフィルタ（最低株価/最低平均売買代金）適用。
    - 数値ファクターの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへの日付単位置換（トランザクション、DELETE→INSERT で冪等性を保証）。
    - 休場日や当日の欠損に対応するため target_date 以前の最新株価を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features / ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - コンポーネントは欠損時に中立 0.5 で補完。最終スコアは重み付き合算（デフォルト重みを定義し、ユーザ重みのバリデーションとリスケール対応）。
    - _sigmoid・平均化・各種スコア計算ユーティリティを実装。
    - Bear レジーム検出（ai_scores の regime_score の平均が負の場合。ただしサンプル数が閾値未満なら Bear としない）。
    - BUY シグナルは閾値（デフォルト 0.60）を超える銘柄に発行、Bear レジーム時は BUY を抑制。
    - SELL シグナル（エグジット）判定: ストップロス（終値/avg_price - 1 < -8%）とスコア低下（final_score < threshold）。
    - positions / prices_daily を参照し、保有ポジションに対して SELL 判定を実施。価格欠損時は判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で原子性を保証）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外し、BUY のランクを再付与）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース収集で defusedxml を使用し XML パースに対する安全性を向上。
- ニュース URL 正規化でトラッキングパラメータを除去、SSRF やトラッキングへの配慮。
- J-Quants クライアントはタイムスタンプを UTC で記録し、Look-ahead バイアス防止に配慮。

Removed
- （初版のため該当なし）

Known issues / TODO
- signal_generator の未実装条件（ソース内コメントで明示）
  - トレーリングストップ（peak_price を使った -10% ルール）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
- kabusys.data.news_collector 内での RSS パース／DB 保存の細部（記事→銘柄紐付け等）は実装済みの方針が示されているが、運用時の調整やエッジケース対応が必要。
- 外部依存:
  - zscore_normalize は kabusys.data.stats に依存（当該モジュールが存在することを前提）。
- エラーや例外の全ケースに対するユニットテストはリポジトリからは確認できないため、追加テストの整備を推奨。

注記
- 本 CHANGELOG はリポジトリ内のコードとドキュメンテーション文字列（docstring）から実装意図・仕様を推測して作成しています。実際のリリースノートには運用上の注意点や互換性情報を追加してください。