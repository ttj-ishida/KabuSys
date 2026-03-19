# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

最新リリース: 0.1.0 — 2026-03-19

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システムのコア機能群を含む最初の公開バージョン。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ情報とエクスポートを定義（version=0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - export KEY=val 形式、引用符付き値、インラインコメント処理などに対応する堅牢な .env パーサ実装。
    - OS 環境変数保護機能（override/protected の仕組み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - 必須環境変数取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - 環境（development / paper_trading / live）・ログレベルの検証ロジックを実装。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（株価日足 / 財務データ / マーケットカレンダー）。
    - 固定間隔のレートリミッター（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）および 401 発生時の自動トークンリフレッシュ処理を実装。
    - ページネーション対応（pagination_key の利用）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、ON CONFLICT による冪等保存を実現。
    - 取得時刻を UTC で記録し、look-ahead バイアスをトレース可能にする設計。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース収集パイプライン（デフォルトソースに Yahoo Finance を含む）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリ整列）。
    - defusedxml を用いた XML 攻撃対策、受信サイズ上限（10MB）などセキュリティ考慮。
    - 記事ID を正規化URL の SHA-256 ハッシュ（先頭 32 文字）で生成し、冪等性を確保。
    - DB へのバルク挿入処理やチャンク化（_INSERT_CHUNK_SIZE）によるパフォーマンス対策。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算関数を実装。
    - DuckDB のウィンドウ関数を活用した効率的な集計。
    - データ不足時は None を返すことで堅牢に動作する設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、任意ホライズンに対応、バリデーションあり）。
    - スピアマンランク相関（IC）計算（calc_ic）とランク化ユーティリティ（rank）。
    - ファクタ―の統計サマリー（factor_summary）。
  - src/kabusys/research/__init__.py に主要関数をエクスポート。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research 側で計算された生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用、Z スコア正規化、±3 クリップして features テーブルへ日付単位で置換（UPSERT 相当）する処理を実装。
    - DuckDB トランザクションを用いた原子的な日付置換処理。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換、欠損は中立 0.5 で補完）。
    - weight の入力検証と正規化（合計 1.0 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合を Bear と判定、サンプル数閾値あり）による BUY 抑制。
    - エグジット条件の実装（ストップロス -8% / final_score が閾値未満）、保有ポジションに対する SELL 判定。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。
    - デフォルト重み・閾値は StrategyModel に基づく設定を適用（デフォルト閾値 0.60 等）。

- パッケージ構成（strategy エクスポート）
  - src/kabusys/strategy/__init__.py で build_features と generate_signals を公開。

- データユーティリティ
  - src/kabusys/data/jquants_client.py にて型安全な数値変換ユーティリティ（_to_float, _to_int）を提供し、不正入力に対して None を返す動作。

### 変更 (Changed)
- n/a（初期リリースのため既存からの変更点なし）

### 修正 (Fixed)
- n/a（初期リリース）

### セキュリティ (Security)
- news_collector で defusedxml を採用し XML 攻撃を軽減。
- news_collector にて URL 正規化とスキーム制限、受信サイズ上限を実装し SSRF / メモリ DoS のリスクを低減。
- jquants_client は API レート制限遵守・トークン自動更新・リトライ制御を含め堅牢化。

### パフォーマンス (Performance)
- DuckDB のウィンドウ関数や集計を活用し、ファクター計算・将来リターン計算を単一クエリで実行する設計。
- news_collector のバルク挿入・チャンク処理により DB 書き込みオーバーヘッドを削減。
- jquants_client はページネーションをループで処理し、レート制限に従ってスロットリング。

### 既知の制限 / TODO
- signal_generator のトレーリングストップ・時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- research モジュールは pandas 等を使用せず標準ライブラリのみで実装しているため、特定の分析ワークフローでは機能拡張の余地あり。
- News → 銘柄紐付け（news_symbols）処理は設計書に言及があるが、現状の実装状況は部分的（実データ結びつけの詳細実装が必要）。

### 互換性 (Compat)
- 0.1.0 は最初のリリースのため破壊的変更はなし。将来のリリースで Settings の必須環境変数や DB スキーマに変更が入る可能性あり。環境変数や DB スキーマ変更時はメジャー/マイナー適切にバージョニングする予定。

---

注: 上記はコードベースの内容から推測して作成した CHANGELOG です。リリースノートとして公開する場合は、実際のリリース日・影響範囲・関連ドキュメントへのリンク等を追記してください。