# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0。

- 設定／環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、カレントワーキングディレクトリに依存しない読み込みを実現。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメント扱いの厳密化などをサポート。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）と上書き保護（protected keys）を実装。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu station / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルなどのプロパティを取得・バリデーションするユーティリティを実装。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大試行回数、429 の Retry-After 優先）と 401 発生時の自動トークンリフレッシュを実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等性のため ON CONFLICT を用いた更新を行う。
  - ペイロード変換ユーティリティ（_to_float, _to_int）で入力の堅牢性を向上。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集ロジックを追加。デフォルトソースに Yahoo Finance を設定。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除等）と記事 ID のハッシュ化による冪等化。
  - defusedxml による XML パースで XML Bomb 等の攻撃を緩和。
  - レスポンスサイズ制限（最大 10MB）、HTTP スキームの検証、SSRF 対策、DB バルク挿入のチャンク化など安全性・性能面の配慮。

- 研究（Research）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算。
    - Value（per, roe）計算。raw_financials の target_date 以前の最新データを参照。
    - DuckDB を用いた SQL ベースの高速集計ロジック。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（スピアマン ρ、ランク計算ユーティリティ rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - 研究用ユーティリティを re-export して使用を簡易化。

- 戦略（Strategy）モジュール（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で計算した raw ファクターを読み込み、ユニバースフィルタ（最低株価、平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し、±3 でクリップ。
    - features テーブルへの日付単位の置換（削除→挿入）をトランザクションで実行し原子性を担保。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して最終スコアを生成。
    - 重みのユーザー指定を許容し、フォールバック・正規化・不正値スキップのロジックを実装。
    - Bear レジーム判定（AI の regime_score 平均 < 0 の場合）による BUY シグナル抑制。
    - BUY / SELL ロジックを実装（BUY は閾値超過、SELL はストップロス（-8%）またはスコア低下）。
    - positions / prices_daily / features / ai_scores を参照し、signals テーブルへ日付単位で置換（トランザクション）して書き込む。
    - エグジットの未実装領域（トレイリングストップ、時間決済）をコード中にコメントで明記。

- データ統合ユーティリティ
  - DuckDB を主要なローカル DB として前提にした SQL/Python ハイブリッド実装により、データ取得→保存→特徴量計算→シグナル生成のワークフローを完成。

### Security
- ニュース XML パースに defusedxml を採用して XML 関連の脆弱性を緩和。
- news_collector で受信サイズ上限、スキーム検証、トラッキングパラメータ除去など SSRF/DoS 対策を実施。
- J-Quants クライアントではタイムアウト・リトライ・トークン自動更新・429 の Retry-After 尊重などを実装し、外部 API 呼び出しの堅牢性を向上。

### Known limitations / Notes
- signal_generator の一部エグジット条件（トレーリングストップ、保有期間による決済）は未実装（コード内に明記）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、大規模データでのメモリ/パフォーマンスは実環境で検証が必要。
- 一部の関数は prices_daily / raw_financials / features 等のテーブルスキーマに依存するため、マイグレーション・スキーマ定義は別途必要。

---

（この CHANGELOG はソースコードの内容とドキュメント文字列から推測して作成しています。実際のリリースノートとして使用する際は、変更履歴・日付・責任者等をプロジェクトの実際の運用に合わせて調整してください。）