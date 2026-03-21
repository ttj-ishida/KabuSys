# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載します。  
このプロジェクトの初期リリース（推測に基づく記述）をまとめています。

注: 下記は与えられたソースコードから実装内容を推測して作成した CHANGELOG です。実際の履歴やリリース手順と差異がある可能性があります。

## [0.1.0] - 2026-03-21

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）
  - .env 行パーサ（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 設定アクセス用 Settings クラス（プロパティ経由）
    - 必須/デフォルト環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）
    - DB パスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境種別検証: KABUSYS_ENV の検証（development, paper_trading, live）
    - ログレベル検証: LOG_LEVEL の検証（DEBUG/INFO/...）

- データ取得/保存 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出しラッパー（ページネーション対応）
    - 固定間隔レート制限 (120 req/min) のスロットリング実装
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 時のトークン自動リフレッシュ（1 回まで）と module-level ID トークンキャッシュ
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB への保存関数（冪等性: ON CONFLICT DO UPDATE）
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 変換ユーティリティ: _to_float / _to_int

  - ニュース収集 (news_collector.py)
    - RSS フィード取得・パース・正規化処理
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、キーソート）
    - defusedxml を用いた XML パース（セキュリティ対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - バルク挿入のチャンク処理など、DB 挿入の効率化と冪等性考慮
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定

- 研究用モジュール (src/kabusys/research/)
  - factor_research.py
    - Momentum / Volatility / Value / Liquidity 等のファクター計算を実装
    - DuckDB 上の prices_daily / raw_financials を参照する SQL と計算ロジック
    - 主要関数: calc_momentum, calc_volatility, calc_value
    - 営業日相当のウィンドウやスキャン範囲バッファを考慮した実装
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)
    - IC（Spearman の ρ）計算 (calc_ic)、ランク変換ユーティリティ (rank)
    - ファクター統計サマリー (factor_summary)
  - research パッケージの公開 API を整備（__init__.py）

- 戦略モジュール (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - 研究環境で計算した生ファクターを結合・正規化（Z スコア正規化を使用）
    - ユニバースフィルタ（最低株価/最低平均売買代金）を実装（デフォルト: 300 円 / 5 億円）
    - Z スコアを ±3 にクリップして外れ値の影響を抑制
    - データの日付単位での置換（トランザクション + バルク挿入）により冪等性と原子性を保証
    - 公開関数: build_features(conn, target_date) → upsert した銘柄数を返す
  - シグナル生成 (signal_generator.py)
    - features テーブルと ai_scores を統合して final_score を計算
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（シグモイド変換、欠損は中立 0.5 補完）
    - デフォルト重み・閾値を実装（デフォルト閾値 0.60）
    - Bear レジーム検出（ai_scores の regime_score の平均が負かつ十分なサンプル数の場合）
    - BUY/SELL シグナル生成と signals テーブルへの書き込み（削除→挿入の置換、トランザクション処理）
    - SELL 判定ロジック（ストップロス -8% / final_score が閾値未満）
    - 公開関数: generate_signals(conn, target_date, threshold=None, weights=None) → 書き込んだシグナル数を返す

- パブリック API 統合 (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py)
  - 主要関数を __all__ により公開し、外部から利用しやすいように整理

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- ニュース XML パースに defusedxml を利用し XML Bomb 等の攻撃を防止
- ニュース URL 正規化でトラッキングパラメータを除去し、ID 生成の冪等性を確保
- RSS の受信サイズ上限を設定してメモリ DoS を軽減
- .env 読み込み時に OS 環境変数を protected として上書きを防止する仕組みを導入

### 注記 / 設計方針（重要）
- Look-ahead bias（ルックアヘッドバイアス）対策:
  - 取得時刻（fetched_at）を UTC で記録
  - features/signals/AI 統合いずれも target_date 時点までの情報のみを用いる設計方針が一貫して適用されている
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / 日付単位の DELETE→INSERT により冪等化
  - ニュースや価格データの重複挿入に対する保護あり
- レートリミット・リトライ:
  - J-Quants API 呼び出しは固定間隔スロットリングで 120 req/min を守る
  - ネットワーク・HTTP エラーに対する再試行と指数バックオフを実装
- 設定:
  - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 自動 .env 読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- データベーススキーマ（利用するテーブル、推定）
  - raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news などのテーブル存在を前提とした実装

### 移行 / 利用上の注意 (Migration / Usage)
- 初期導入時に以下を確認・設定してください:
  - .env（または環境変数）に必要なキーを設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - DuckDB のスキーマ（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar / raw_news 等）を適切に作成すること
  - 本リポジトリの自動 .env ロードはパッケージ配布環境でも動作するように __file__ ベースでプロジェクトルートを探索します。CWD に依存しない点に注意。
- テスト環境:
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

### 既知の制限 / TODO
- signal_generator のエグジット条件において未実装の条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）— positions に entry_date 等の追加が必要
- news_collector の銘柄紐付け（news_symbols への保存処理等）や詳細なテキスト処理は実装の余地あり
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、大規模データでのパフォーマンス検証が必要
- DuckDB のテーブル定義・インデックス・VACUUM 等の運用ドキュメントは別途整備が必要

### 互換性 (Breaking Changes)
- 初回リリースのため互換性破壊はなし（新規導入）

### 開発者 / 貢献
- この CHANGELOG はソースコードの静的解析に基づいて作成した推定履歴です。実際のリリースノートはプロジェクトのリリース方針に従って記載してください。

--- 

今後のリリースでは、実装済みの TODO（トレーリングストップ、時間決済、news→symbols 紐付け強化など）や運用改善（ログ詳細化、メトリクス公開、DuckDB スキーマ管理の自動化）を反映してください。