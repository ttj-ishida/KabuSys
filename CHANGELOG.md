# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 0.1.0 は初回公開（初版）リリースです。

[Unreleased]
- なし

[0.1.0] - 2026-03-20
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。
  - サブパッケージの公開 API を定義（strategy, execution, data, monitoring のエクスポート）。

- 環境設定・自動 .env ロード（src/kabusys/config.py）
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルートを .git または pyproject.toml から探索して決定（CWD 非依存）。
  - .env 行パーサを実装：コメント行、export KEY=val 形式、クォート文字列、エスケープ処理、インラインコメント判定に対応。
  - .env.local は .env を上書き（override=True）、OS 環境変数は protected として上書き不可。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や各種設定（DB パス、KABUSYS_ENV/LOG_LEVEL の検証、is_live/is_paper/is_dev）を型安全に取得可能。

- データ取得・保存（src/kabusys/data/jquants_client.py, news_collector.py）
  - J-Quants API クライアント実装
    - レートリミッタ（120 req/min 固定間隔スロットリング）。
    - リトライ処理（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 の場合は自動トークンリフレッシュを 1 回行って再試行する仕組み。
    - ページネーション対応でデータを連続取得。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を行う。
    - 値変換ユーティリティ _to_float / _to_int を用意し、不正データを安全に扱う。
    - 取得時刻（fetched_at）を UTC ISO 形式で保存して Look-ahead バイアスのトレースを可能に。
  - ニュース収集モジュール（news_collector）
    - RSS フィード収集の骨子を実装（デフォルトソース: Yahoo Finance のビジネス RSS）。
    - defusedxml を用いた安全な XML パース、応答サイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS を軽減。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）除去、フラグメント削除、クエリパラメータソート。
    - 記事 ID は正規化後 URL の SHA-256 ハッシュ（先頭 32 文字）等で冪等性を確保する方針（実装方針がコメントに明記）。
    - バルク INSERT のチャンク処理や SQL の安全化を考慮した設計（チャンクサイズ定義など）。
    - セキュリティ考慮（SSRF の緩和、XML 脆弱性対策、受信サイズ制限）を導入。

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - factor_research.py: prices_daily / raw_financials を利用したファクター計算を実装
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、20 日平均売買代金、volume_ratio を計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0 や欠損時は None）。
    - 各関数は DuckDB SQL ウィンドウ関数を活用し、高速に一括計算を実施。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算。ホライズンパラメータのバリデーションあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。サンプル数不足時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの公開 API を整備（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。

- 特徴量作成（src/kabusys/strategy/feature_engineering.py）
  - build_features 実装:
    - research モジュールの calc_* で得た raw ファクターを集約。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化 (zscore_normalize) を実行し、Z スコアを ±3 でクリップして外れ値の影響を抑制。
    - target_date による日単位の置換（DELETE + bulk INSERT）で冪等性を担保。トランザクションで原子性確保。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals 実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み（momentum 0.40 等）と閾値（BUY: 0.60）を備える。ユーザー指定 weights は検証・リスケールして受け付ける。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完する戦略的設計。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）により BUY を抑制可能。
    - エグジット条件（stop_loss: -8% / final_score が閾値未満）で SELL を生成。SELL を優先して BUY から除外。
    - signals テーブルへ日単位の置換（トランザクションで原子性保証）を行う。
    - ログ出力と警告を多用し、欠損データ時の挙動を明示。

Changed
- （初版リリースのため変更履歴はなし）

Fixed
- （初版リリースのため修正履歴はなし）

Security
- defusedxml を用いた RSS XML パース、受信バイト数の制限、URL 正規化・トラッキング除去、HTTP スキームの検証など、外部入力に対する安全策を導入。

Notes / Known issues / TODO
- signal_generator のトレーリングストップ（直近最高値からの X%）と時間決済（保有 60 営業日超）についてはコメントで未実装と明記。positions テーブルに peak_price / entry_date の追加が必要。
- news_collector の記事 ID 生成・news_symbols との紐付けや INSERT RETURNING による実際の挿入件数取得は設計方針として記載されているが、実装の詳細（全ての SQL 実装）は部分的にコード化が必要な箇所がある可能性あり。
- J-Quants クライアントは HTTP レスポンスの JSON デコードエラーやネットワーク例外時の再試行ロジックを持つが、実運用ではレート制御やエンドポイント変更に伴う追加対応が想定される。
- 一部の関数は DuckDB のテーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals 等）を前提としているため、初期化・マイグレーションスクリプトが別途必要。

開発 / 貢献
- 初期アーキテクチャは「データ層（fetch/save）」「リサーチ（ファクター計算）」「戦略（特徴量生成・シグナル生成）」「実行層（execution）」「監視（monitoring）」の分離を意識して設計されています。将来的な拡張（実行エンジン、バックテスト、監視アラート等）を想定したモジュール分割がなされています。

---
この CHANGELOG はコードベースのコメント・実装から推測して作成しています。リリースノートの正確性向上のため、実際のコミットメッセージや差分（Git タグ）に基づく追記・修正を推奨します。