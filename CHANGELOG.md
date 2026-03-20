# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
タグ付けされたリリースはセマンティックバージョニングに従います。

## [Unreleased]

### Known limitations / 未実装
- signal_generator のエグジット条件として言及されている
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
 これらは positions テーブル側の追加フィールド（peak_price / entry_date 等）が揃っていないため未実装です。

---

## [0.1.0] - 2026-03-20

### Added
- パッケージ基礎
  - kabusys パッケージ初期版を追加。公開 API: data, strategy, execution, monitoring を __all__ で定義（src/kabusys/__init__.py）。
  - バージョン番号を 0.1.0 に設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env パーサは以下をサポート：
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ
    - クォートなし値でのインラインコメント処理（直前が空白/タブの場合のみ）
  - _load_env_file による上書き制御（override）、OS 環境変数保護（protected）をサポート。
  - 環境設定を取得する Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、SQLite/DuckDB パス等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値外で ValueError を発生）。
  - is_live / is_paper / is_dev の補助プロパティを提供。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限を守る固定間隔スロットリング実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx の再試行、429 の場合は Retry-After を優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止あり）。
  - ページネーション対応（pagination_key の扱い）。
  - データ保存時に取得時刻（fetched_at）を UTC ISO8601 で記録し look-ahead bias のトレースを可能に。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - どれも冪等性のため ON CONFLICT DO UPDATE または DO NOTHING を使用。
    - PK 欠損行はスキップし、スキップ件数をログに出力。
    - 型安全な変換ユーティリティ _to_float / _to_int を提供。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードを収集して raw_news テーブルに保存する処理を実装（既定ソース: Yahoo Finance ビジネス RSS）。
  - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ除去、断片削除、クエリソート）を実装。
  - 記事 ID は正規化後 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を担保。
  - defusedxml を使用して XML Bomb 等を防止。
  - 受信バイト数上限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を軽減。
  - SSRF 対策として HTTP/HTTPS スキーム以外を拒否する方針（モジュール内設計思想）。
  - バルク INSERT のチャンク化によるパフォーマンス配慮とトランザクションまとまりの設計。

- 研究（research）モジュール (src/kabusys/research/)
  - ファクター計算群を実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 約1/3/6ヶ月リターン、200日移動平均乖離（ma200_dev）。
    - Volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（price / EPS）、ROE（raw_financials の最新レコード参照）。
  - 将来リターン計算（calc_forward_returns）を提供（複数ホライズン対応、データ欠損は None）。
  - IC（Information Coefficient）計算（calc_ic）: Spearman の ρ（ランク相関）を実装。
  - ファクター統計サマリー（factor_summary）とランク化ユーティリティ（rank）を提供。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で計算した raw ファクターを合成・正規化して features テーブルへ書き込む build_features を実装。
  - ユニバースフィルタを実装（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）。
  - Z スコア正規化を適用（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
  - 日付単位で一括置換する（DELETE + INSERT）トランザクション実行で冪等性・原子性を確保。
  - 欠損や非数値の取り扱いに注意して実装。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し、signals テーブルに書き込む generate_signals を実装。
  - コンポーネントスコア:
    - Momentum（momentum_20, momentum_60, ma200_dev）
    - Value（per の逆数スコア化）
    - Volatility（atr_pct の Z スコア反転）
    - Liquidity（volume_ratio）
    - News（AI スコアのシグモイド）
  - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
  - 重み（weights）の検証・補完・再スケーリング処理を実装（デフォルトは StrategyModel.md に準拠）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制。ただしサンプル数閾値あり）。
  - BUY シグナル閾値（デフォルト _DEFAULT_THRESHOLD=0.60）を超える銘柄に BUY を生成。Bear 相場での抑制。
  - SELL シグナル（_generate_sell_signals）:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
    - 価格が欠損している銘柄の SELL 判定はスキップして誤クローズを防止（警告ログ）。
    - features に存在しない保有銘柄は final_score=0.0 として SELL 対象にする旨の警告ロジック。
  - SELL 優先ポリシー: SELL 対象を BUY から除外し、BUY のランクを連番で再付与。
  - signals テーブルへの日付単位置換をトランザクションで行い冪等性を確保。
  - 生成した BUY/SELL 数をログ出力。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を使用する等、外部入力（RSS/XML）に対する基礎的な安全対策を実施。
- J-Quants API クライアントはトークンリフレッシュ処理時に無限再帰を避けるフラグを導入。

### Documentation / Logging
- 各モジュールに詳しい docstring と設計方針・処理フローの説明を追加（開発者向けに設計仕様を明記）。
- 主要処理において冪等性・原子性・スキップ理由をログで出力するように実装（warnings / logger）。

### Removed / Deprecated
- （初期リリースのため該当なし）

---

Notes / 補足
- 多くの処理は DuckDB 上のテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）に依存します。実運用ではスキーマ整備とマイグレーションが必要です。
- signal_generator の未実装部分（トレーリングストップ、時間決済）は将来的な拡張項目です。positions テーブルのスキーマ拡張（peak_price, entry_date など）が前提となります。
- 環境変数読み込みロジックは配布後も .env 検出が機能するように .git / pyproject.toml を基準にプロジェクトルートを探索します。CI/コンテナ環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して挙動を制御してください。