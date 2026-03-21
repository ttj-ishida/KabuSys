# CHANGELOG

すべての重要な変更点をここに記載します。本プロジェクトは Keep a Changelog の慣習に従います。  

既知のバージョンはセマンティックバージョニングに従います。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下は主要な追加点と設計上の要点です。

### Added
- パッケージ基底
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを公開）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロード順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートの探索: .git または pyproject.toml を基準に決定（__file__ 起点で探索）
  - .env パーサを実装（コメント処理、export KEY=val、クォート内のエスケープ処理対応）。
  - Settings クラスを提供し、主要設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（未設定で ValueError）。
    - KABUSYS_ENV に対する値検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔のレートリミッタ（デフォルト 120 req/min）。
    - リトライ（最大 3 回、指数バックオフ、408/429/5xx を再試行）。429 の場合は Retry-After を優先。
    - 401 を受けた場合はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
    - ページネーション対応（pagination_key の利用）。
    - UTC タイムスタンプ（fetched_at）を記録し、Look-ahead バイアスの追跡を可能にする設計。
  - fetch_* / save_* API:
    - fetch_daily_quotes / save_daily_quotes（raw_prices へ冪等保存、ON CONFLICT DO UPDATE）
    - fetch_financial_statements / save_financial_statements（raw_financials へ冪等保存）
    - fetch_market_calendar / save_market_calendar（market_calendar へ冪等保存）
  - 内部ユーティリティ: 安全な型変換関数 _to_float / _to_int。

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集して raw_news へ保存する基盤を実装（デフォルト RSS ソースに Yahoo Finance を設定）。
  - セキュリティ/堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - 非 HTTP/HTTPS スキームや SSRF を考慮したチェック（実装方針）。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE = 1000）。

- リサーチ（kabusys.research）
  - ファクター計算と特徴量探索機能を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日株価を組み合わせて PER / ROE を算出（EPS が 0/欠損時は None）。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコード数が 3 未満の場合は None）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - rank: 同順位は平均ランクを返すランク関数（丸め処理により ties の検出漏れを抑制）。
  - 実装方針: DuckDB の prices_daily / raw_financials のみ参照、外部依存なし（pandas 未使用）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 正規化対象カラムを zscore_normalize（kabusys.data.stats に依存）で正規化し、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入）により冪等性と原子性を確保。
    - データ欠損や外れ値処理に配慮。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、複数コンポーネント（momentum / value / volatility / liquidity / news）のスコアを計算。
    - コンポーネントの計算ユーティリティ実装（シグモイド変換、欠損補完は中立 0.5）。
    - デフォルト重みを実装（momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10）。ユーザ指定の weights は検証・補完・再スケールされる。
    - BUY シグナル閾値デフォルト 0.60。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）。Bear 時は BUY を抑制。
    - エグジット（SELL）判定:
      - ストップロス（終値 / avg_price - 1 < -0.08 = -8%）
      - スコア低下（final_score < threshold）
      - positions / prices_daily を参照し、価格欠損時は判定をスキップまたは警告。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を確保。
    - ロギングにより処理状況を記録（INFO/WARNING/DEBUG）。

### Changed
（初回リリースのため、既存からの変更点はありません）

### Fixed
（初回リリースのため、既知のバグ修正はありません）

### Security
- 外部データ取込部分（RSS / XML / HTTP）に対して防御的実装を行っています（defusedxml、受信サイズ制限、URL 正規化、既知トラッキングパラメータ除去など）。
- 環境変数読み込みでは OS 環境変数を保護する設計（読み込み時 protected set を利用してオーバーライド制御）。

### Notes / Implementation decisions
- Look-ahead bias を避けるため、すべての戦略／シグナル生成は target_date 時点のデータのみを使用する設計。
- DuckDB を中心に SQL と最小限の Python を組み合わせて処理する方針（高性能バッチ処理重視）。
- 多くの DB 操作はトランザクション + バルク挿入で原子性と効率性を確保。
- 一部機能（例: トレーリングストップ、時間決済など）は設計コメントで未実装として残しており、将来の拡張を想定。

### Breaking Changes
- なし（初回リリース）

---

今後のリリースでは、戦略パラメータの運用インタフェース、より詳細なモニタリング / 実行レイヤ（execution モジュール）やテストカバレッジの強化、トレーリングストップ等の追加実装を計画しています。