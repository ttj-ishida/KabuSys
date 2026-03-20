# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py, version=0.1.0）。
  - サブパッケージ公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パーサ（export 形式／クォート／インラインコメント対応）を実装。
  - .env 読み込み時の上書きポリシー（override / protected）を実装し OS 環境変数を保護。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境・ログレベル等のプロパティを取得。環境変数の必須チェックと値検証（KABUSYS_ENV, LOG_LEVEL）を行う。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - 401 時の自動トークンリフレッシュ、リトライ（指数バックオフ, 最大3回）、429 の Retry-After 優先処理を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）で冪等性を確保（ON CONFLICT DO UPDATE）。
    - fetched_at は UTC で記録、型安全な数値変換ユーティリティ（_to_float/_to_int）を提供。
  - ニュース収集（news_collector.py）
    - RSS から記事を収集して raw_news テーブルへ冪等保存する基本実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリ整列）および記事 ID 生成方針を用意。
    - defusedxml による XML セキュリティ対策、受信サイズ上限（MAX_RESPONSE_BYTES）、SSRF/不正スキーム対策、バルク挿入のチャンク化を想定した設計（実装済みユーティリティを含む）。
    - デフォルト RSS ソース定義（Yahoo Finance ビジネスカテゴリ）。

- リサーチ・ファクター（src/kabusys/research/）
  - ファクター計算モジュール（factor_research.py）
    - Momentum（1M/3M/6M リターン / MA200 乖離）、Volatility（20日 ATR / atr_pct / 20日平均売買代金 / 出来高比率）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を提供。
    - スキャン範囲のバッファや欠損時の扱いを明確化（行数不足時は None を返す等）。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズンに対応、入力検証あり）。
    - スピアマン IC（calc_ic）、列の統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。

- 戦略層（src/kabusys/strategy/）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research モジュールから生ファクターを取得してマージ、ユニバースフィルタ（最低株価、平均売買代金）適用、Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）および ±3 でクリップして features テーブルへ日付単位で置換（トランザクションで原子性を確保）。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を計算。
    - デフォルト重みと閾値を定義し、ユーザー指定 weights の検証・フォールバック・再スケール処理を実装。
    - Bear レジーム判定（AI の regime_score を集計）、Bear 時の BUY 抑制、エグジット判定（ストップロス・スコア低下）を実装。
    - BUY/SELL シグナルを signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

### Changed
- （初回リリース）設計指針・実装コメントを充実させ、将来的な拡張（トレーリングストップ、PBR/配当利回り、positions の peak_price 等）を明確化。

### Fixed
- N/A（初回リリース）

### Security
- ニュース XML のパースに defusedxml を使用して XML 関連攻撃を軽減。
- RSS/URL 正規化と受信サイズ制限によりメモリ DoS や SSRF リスクを低減する設計を導入。
- J-Quants クライアントのトークン管理と自動リフレッシュにより認証失敗時の安全な再試行を実装。

### Notes / Known limitations
- 一部の機能は将来の拡張予定：
  - signal_generator のトレーリングストップや時間決済の判定は positions テーブルに peak_price / entry_date 等が必要であり未実装。
  - research の一部（PBR・配当利回り）は未実装。
  - news_collector の記事 ID 生成・DB 挿入の完全なワークフローはユーティリティを提供しているが、外部 RSS の取得ループ等の統合処理は今後の実装対象。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions 等）は本リポジトリに含まれていないため、利用前にスキーマ定義の準備が必要。

---

（以降の変更はこのファイルに記載してください）