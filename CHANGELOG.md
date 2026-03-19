CHANGELOG
=========

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。
以下の内容は提供されたコードベースの実装から推測して作成したものであり、実際のコミット履歴ではありません。

Unreleased
----------

- なし

0.1.0 - 2026-03-19
------------------

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境変数・設定管理（src/kabusys/config.py）。
  - .env / .env.local 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から行う実装を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント判定などを考慮した堅牢な処理を実装。
  - OS 環境変数を保護する protected set を導入し、.env.local で OS 環境変数を上書きしないように制御。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須で取得（未設定時に ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルト値を設定。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティメソッドを提供。

- データ取得・保存（src/kabusys/data/jquants_client.py）。
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等性を考慮した DuckDB 保存（ON CONFLICT DO UPDATE）を実装（raw_prices, raw_financials, market_calendar）。
    - ページネーション対応、ID トークンのキャッシュと自動リフレッシュ（401 の際に1回リトライ）。
    - ネットワーク/HTTP エラーに対する指数バックオフ付きリトライ（408, 429, 5xx 等）。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - save_* 系関数: save_daily_quotes, save_financial_statements, save_market_calendar。
    - 変換ユーティリティ: _to_float / _to_int（不正値・空値を安全に扱う）。

- ニュース収集（src/kabusys/data/news_collector.py）。
  - RSS フィードからの記事収集と raw_news への保存処理を実装の基礎を追加。
    - デフォルト RSS ソース（Yahoo Finance のカテゴリフィード）を定義。
    - 受信サイズ上限（10 MB）や受信時の防御（defusedxml を使用）を導入。
    - URL 正規化ロジック（クエリから utm_* 等トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保する方針を採用。
    - HTTP スキームの検証・SSRF 対策、挿入バッチサイズ制御などの安全機構を想定。

- 研究用ファクター計算（src/kabusys/research/*）。
  - ファクター計算モジュール:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe を計算。
    - ウィンドウサイズやスキャン範囲の安全マージン、欠損データに対する None 扱いを明示。
  - 特徴量探索モジュール:
    - calc_forward_returns（任意ホライズンの将来リターン計算。horizons の検証あり）。
    - calc_ic（Spearman ランク相関による IC 計算。サンプル不足時は None）。
    - factor_summary / rank（基本統計量と同順位処理の実装）。
  - zscore_normalize を外部（kabusys.data.stats）から利用する設計で統合を想定。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）。
  - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300円、20日平均売買代金 5 億円）を適用。
  - 指定カラムを Z スコア正規化して ±3 でクリップ。
  - データベース（features テーブル）へ日付単位での置換（トランザクション+バルク挿入）を実装し、冪等性を担保。
  - target_date 以前の最新価格をユニバース判定に用いることで休場日などへの対応を実現。

- シグナル生成（src/kabusys/strategy/signal_generator.py）。
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（デフォルト重みを定義）。
    - スコア変換・補完: Z スコアをシグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - SELL 条件にストップロス（-8%）とスコア低下を実装。保有ポジションの価格欠損時は SELL 判定をスキップ。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等性を担保。
    - ユーザー指定の weights を妥当性チェックし、合計が 1.0 になるよう正規化。

- モジュール公開 API の整理（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）。

Security
- defusedxml を用いた XML パース（news_collector）により XML ベースの攻撃を緩和。
- news_collector における URL 正規化とスキーム検証、受信サイズ制限により SSRF / DoS リスク低減を想定。
- config モジュールは OS 環境変数を protected set として扱い、意図しない上書きを防止。

Changed
- 初回リリースのため該当なし（初期導入機能）。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 推測
- 上記はソースコードから機能・設計意図を読み取って作成した変更履歴案です。実際のコミットメッセージや開発履歴が存在する場合は、そちらに基づく正確な CHANGELOG の作成を推奨します。
- DB スキーマ（テーブル名やカラム）はコード中で言及されていますが、実際のスキーマ定義（CREATE TABLE 等）はこのスニペットに含まれていないため、マイグレーションや互換性に関する情報は明記していません。
- news_collector / jquants_client の一部振る舞い（トークンキャッシュの永続化、詳細なエラーハンドリング方針等）は実装の一部から推測しています。