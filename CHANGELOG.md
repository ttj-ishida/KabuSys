# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

- リリース日付はソースコードのスナップショットに基づいて推測しています。
- 記載内容はコードベースから推測して要約したものであり、実運用上の詳細は該当モジュールの実装やドキュメントを参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-21

### Added
- 基本パッケージ
  - パッケージ名: KabuSys（src/kabusys）
  - __version__ を "0.1.0" として定義。パッケージの公開用エントリポイントを __all__ で指定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。
  - 読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の行パースの高度な取り扱い:
    - export プレフィックス対応、クォート文字列、バックスラッシュによるエスケープ、インラインコメントの扱い。
    - 上書き制御（override）および OS 環境変数保護（protected）。
  - Settings クラスを提供し、各種必須設定に対する取得メソッドを定義（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、データベースパス等）。
  - 設定値検証:
    - KABUSYS_ENV の許容値検査（development / paper_trading / live）。
    - LOG_LEVEL の許容値検査（DEBUG 等）。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象に設定。
  - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - fetch_* API: daily quotes / financial statements / market calendar の取得関数を提供。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等性を担保するため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO8601 で記録。
    - PK 欠損行はスキップしログ出力。
  - 型安全な変換ユーティリティ: _to_float / _to_int。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する処理。
  - セキュリティ・堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) の設定によるメモリ DoS 緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）を想定し冪等性を確保（docstring に明記）。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）とトランザクション単位での保存設計。
  - デフォルト RSS ソース（例: Yahoo Finance のビジネス RSS）。

- リサーチ関連 (src/kabusys/research)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB のウィンドウ関数を活用し、mom_1m/mom_3m/mom_6m、MA200 乖離、ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比率（volume_ratio）、per/roe 等を算出。
    - データ不足時の None ハンドリング、スキャン範囲のバッファ（カレンダー日ベース）を用いた実装。
  - feature_exploration.py:
    - calc_forward_returns: LEAD を用いた将来リターン計算（複数ホライズン対応）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。レコード数が少ない場合は None を返す。
    - rank: 同順位は平均ランクにする実装（丸め誤差対策として round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージ __init__ で主要関数をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research 側の生ファクター（momentum/volatility/value）を取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ。
    - features テーブルへの日付単位の置換（削除→挿入）をトランザクションで行い原子性を担保。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみ使用。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features / ai_scores / positions を参照して最終スコア（final_score）を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、デフォルトの重みで合成。デフォルト重みは momentum 0.40 等。
    - シグモイド変換・欠損値は中立値 0.5 で補完する設計。
    - 重みの入力値検証・補完・正規化を行う（未知キーや非数値は無視、合計が 1 でない場合は再スケール）。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かどうか、サンプル閾値あり）により BUY を抑制。
    - BUY 閾値デフォルト 0.60。BUY と SELL を分けて signals テーブルへ日付単位の置換（トランザクション）を行う。
    - SELL 条件（現バージョン）:
      - ストップロス: 終値 / 平均取得価格 - 1 < -8%（優先）。
      - スコア低下: final_score が threshold 未満。
      - 価格欠損時は SELL 判定をスキップしてログ出力。
    - positions に関する未実装の条件（トレーリングストップ、時間決済）は実装予定としてコメントあり。

- モジュール設計上の方針（ドキュメント文字列に明記）
  - ルックアヘッドバイアス防止: 全て target_date 時点のデータのみを使用する設計を徹底。
  - execution（発注）層への依存を持たない戦略層。発注層は分離。
  - DuckDB を主な永続化層として使用し、SQL と Python を組み合わせて処理を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- defusedxml を用いた RSS XML パース、受信サイズ制限、URL 正規化・トラッキングパラメータ除去等により外部入力に対する安全性を高める対策を実装。
- J-Quants クライアント側は認証トークン処理やリトライで安定性と堅牢性を確保。

---

注記:
- 上記はコードから推測した機能と設計方針の要約です。実際の動作や運用手順、外部設定の詳細は各モジュールの実装および README/.env.example 等のドキュメントを参照してください。