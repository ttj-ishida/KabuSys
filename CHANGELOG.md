# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

現在のリリース方針: 初回リリース v0.1.0

[Unreleased]
- （なし）

[0.1.0] - 2026-03-19
Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定読み込み / 管理（src/kabusys/config.py）
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env の行パーサ実装（export プレフィックス対応、シングル/ダブルクォートとエスケープ対応、インラインコメントの扱いなど）。
  - 読み込み時の上書き制御（override フラグと protected OS 環境変数保護）。
  - Settings クラスを実装。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得とバリデーションを提供。
  - settings インスタンスをモジュールレベルで公開。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - レート制限実装（固定間隔スロットリングで 120 req/min を遵守）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対するリトライ、Retry-After の考慮）。
    - 401 (Unauthorized) 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE を使用し重複更新を防止。
    - 取得データの型変換ユーティリティ (_to_float / _to_int) を実装。
  - ニュース収集（news_collector.py）
    - RSS フィードから記事を収集し raw_news テーブルへ冪等保存する処理。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - defusedxml による XML パース（XML Bomb 等の防御）、受信サイズ制限（MAX_RESPONSE_BYTES）、HTTP スキームの厳格チェック（SSRF 対策）などのセキュリティ対策。
    - バルク挿入のチャンク化実装。

- リサーチ機能（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - momentum（mom_1m/mom_3m/mom_6m）、200日移動平均乖離（ma200_dev）。
    - volatility（20日 ATR / atr_pct、20日平均売買代金、出来高比率）。
    - value（PER、ROE） — raw_financials から最新の財務情報を参照。
    - DuckDB のウィンドウ関数を活用した実装、データ不足時に None を返す設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: LEAD を用いた任意ホライズン（デフォルト [1,5,21]）での将来リターン取得、horizons のバリデーション。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランクで処理、round による ties 対策）。有効レコードが少ない場合は None を返す。
    - ファクターの統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要関数を再公開。

- 戦略（src/kabusys/strategy/）
  - 特徴量生成（feature_engineering.py）
    - research の生ファクターを統合して features テーブルに保存する build_features を実装。
    - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5 億円）、Z スコア正規化（zscore_normalize を使用）、±3 でクリップし外れ値影響を低減。
    - target_date ごとの日付単位置換（DELETE + bulk INSERT）をトランザクションで実行し冪等性・原子性を確保。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し final_score を計算する generate_signals を実装。
    - コンポーネントスコア変換にシグモイド関数を使用。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み・閾値（weights デフォルト、BUY 閾値 0.60）や重みの妥当性検証・正規化を実装。
    - Bear レジーム判定（AI の regime_score の平均が負でかつサンプル数閾値以上の場合）による BUY 抑制。
    - エグジット判定（stop loss: -8% / final_score の閾値未満）を実装。SELL は保有ポジションに基づいて生成（価格欠損時は判定をスキップして安全性を確保）。
    - BUY/SELL の日付単位置換をトランザクションで実行し冪等性を保証。
  - strategy パッケージの __init__ で主要関数を公開（build_features, generate_signals）。

Security
- データ取得・ニュース処理周りで以下の安全対策を実装
  - defusedxml を用いた XML パース、RSS の受信サイズ制限、HTTP スキームの制限、SSRF 対策、トラッキングパラメータ除去。
  - J-Quants クライアントでタイムアウト・再試行・トークンリフレッシュを備え、API レート制限遵守。

Notes / Design considerations
- DuckDB を中心としたローカルデータストア設計。ほとんどの関数は prices_daily / raw_financials / features / ai_scores / positions 等のテーブルのみを参照し、本番注文・execution 層などの外部副作用を持たない（データ取得モジュールを除く）。
- ルックアヘッドバイアス防止のため、target_date 時点のデータのみを使用する設計方針を一貫して採用。
- 冪等性と原子性を重視（ON CONFLICT、DELETE + INSERT をトランザクションで実行等）。

Deprecated
- （なし）

Removed
- （なし）

Fixed
- （なし）

Security
- ニュース収集・XML パース・URL 正規化・J-Quants 通信でのセキュリティ対策を実装（詳細は上記参照）。

-- 
注: 上記はソースコードから推測できる機能・設計・実装の概要に基づく CHANGELOG です。実際のリリースノートに含める文章や日付はプロジェクト運用ポリシーに従って調整してください。