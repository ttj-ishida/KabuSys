# Changelog

すべての重要な変更はこのファイルに記録します。本書式は「Keep a Changelog」に準拠します。  
現在のバージョンは 0.1.0 です。

フォーマット:
- 主要カテゴリ: Added / Changed / Fixed / Removed / Security / Known limitations
- 日付はリリース日（YYYY-MM-DD）

---

## [0.1.0] - 2026-03-20

初回公開リリース。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0。モジュール公開: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
- 設定管理
  - 環境変数・.env 自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml ベース）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env の行パーサは export プレフィックス、クォート、エスケープ、コメント処理をサポート。
  - Settings クラスを提供し、必須環境変数の取得や値検証（KABUSYS_ENV / LOG_LEVEL など）を行う。
  - デフォルト値やパス（duckdb/sqlite 等）の展開を実装。
- データ取得・保存 (J-Quants)
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レートリミッタ（120 req/min 固定間隔スロットリング）。
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx 対応。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して再試行。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT / DO UPDATE）。
    - レスポンス時刻（fetched_at）を UTC で記録し、look-ahead バイアスのトレースを可能に。
- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）。
    - 受信サイズ上限（10MB）による DoS 対策。
    - defusedxml を用いた XML 攻撃対策。
    - 記事 ID の冪等化（URL 正規化後のハッシュ）とバルク保存の実装方針。
- リサーチ（ファクター計算）
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）。
    - Value（per, roe）: raw_financials の最新財務データを参照。
    - DuckDB の prices_daily / raw_financials のみを参照する設計（本番発注や外部 API にはアクセスしない）。
  - 研究ユーティリティ（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - IC（Spearman 相関）計算（calc_ic）。
    - ランク変換（rank）とファクター統計サマリー（factor_summary）。
    - 依存を最小限にして標準ライブラリのみで実装。
  - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）。
- 特徴量エンジニアリング
  - build_features 実装（src/kabusys/strategy/feature_engineering.py）。
    - research 側の生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で UPSERT（トランザクションで原子性確保）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ利用。
- シグナル生成
  - generate_signals 実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）スコアを計算。
    - final_score を重み付き合算（デフォルト重みは StrategyModel.md に基づく）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負であるか）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）を生成し signals テーブルへ日付単位で置換（トランザクション）。
    - weights の入力検証と正規化、無効値の警告ログ出力。
- その他
  - strategy パッケージの公開 API（build_features, generate_signals）。
  - 実行層 placeholder（src/kabusys/execution/__init__.py を追加、将来の実装余地）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- news_collector で defusedxml を使用し XML 関連の脆弱性（XML Bomb 等）に対処。
- ニュース収集で受信サイズ上限を設け、メモリ DoS を緩和。

### Known limitations / Notes
- signal_generator のエグジット条件のうち、トレーリングストップ（peak_price 必要）や時間決済（保有 60 営業日超）などは未実装。positions テーブルに追加情報が必要。
- zscore_normalize は外部モジュール（kabusys.data.stats）に依存しているため、当該実装が正しく存在する前提。
- jquants_client の HTTP 実行部は urllib を使用しており、より高度な要求（接続プーリング等）は未対応。
- news_collector の URL 正規化以降の DB 保存・シンボル紐付けの最終実装（INSERT RETURNING 等）については仕様に従い実装済みだが、運用環境での大規模データ投入時のパフォーマンス検証が必要。
- .env パーサは多くのケースを考慮しているが、極めて特殊な構文の .env ファイルは想定外の扱いになる可能性がある。

---

今後の予定（主な TODO）
- execution 層の実装（kabu ステーション等との発注連携、注文管理）。
- monitoring パッケージの実装（Slack 通知、健常性監視）。
- テストカバレッジ拡充（特にネットワークリトライ・DB 保存部分）。
- パフォーマンス最適化（DuckDB クエリ・バルク挿入のチューニング）。

---
参考: 開発中のドキュメント（StrategyModel.md / DataPlatform.md 等）に準拠して設計・実装が進められています。