# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。
このプロジェクトのバージョンはパッケージメタ情報（kabusys.__version__）に合わせて管理しています。

フォーマット: https://keepachangelog.com/ (日本語訳に準拠)

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）: バージョン "0.1.0"、公開モジュール一覧を定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定をロードする Settings クラスを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 環境変数取得ユーティリティ _require と型チェック（環境・ログレベルの検証）を提供。
  - DB パス（duckdb/sqlite）や API トークン等のプロパティを定義。

- Data 層
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API レート制御（120 req/min の固定間隔スロットリング）を実装。
    - 再試行（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ対応。
    - ページネーション対応のデータフェッチ（株価日足 / 財務データ / マーケットカレンダー）。
    - DuckDB への冪等保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT による upsert）と取得時刻（fetched_at）記録。
    - 型変換ユーティリティ _to_float / _to_int。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得・記事パース・前処理・正規化処理。
    - URL 正規化（トラッキングパラメータ削除・クエリソート・スキーム/ホスト小文字化・フラグメント除去）。
    - defusedxml を用いた安全な XML パース、HTTP レスポンスサイズ制限、記事ID（正規化 URL の SHA-256 ハッシュ先頭使用）による冪等保存方針。
    - raw_news / news_symbols 等への一括挿入の方針（チャンク化による安全性と効率性）。

- Research 層
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev を計算する calc_momentum。
    - ボラティリティ・流動性: atr_20 / atr_pct / avg_turnover / volume_ratio を計算する calc_volatility。
    - バリュー: per / roe を計算する calc_value（raw_financials から最新報告を参照）。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日欠損やデータ不足を適切に扱う。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、効率的な SQL 実行）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関実装、サンプル不足時の None ハンドリング）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - ランク計算ユーティリティ rank（同順位は平均順位として処理、丸めによる ties 検出を実装）。

  - research パッケージのエクスポート（src/kabusys/research/__init__.py）: 主要関数を外部公開。

- Strategy 層
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - build_features(conn, target_date): research で計算した生ファクターをマージし、ユニバースフィルタ（最小株価、平均売買代金）を適用、Z スコア正規化（指定列）、±3 でクリップして features テーブルに日単位で置換保存（トランザクションによる原子性）。
    - ルックアヘッドバイアス対策の設計（target_date 時点のデータのみ使用）。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold, weights): features, ai_scores, positions を参照して BUY/SELL シグナルを生成し signals テーブルへ日単位置換保存。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算、シグモイド変換、欠損コンポーネントは中立値で補完。
    - デフォルト重み、閾値、Bear レジーム検知（ai_scores の regime_score 平均が負のとき BUY 抑制）を実装。
    - エグジット判定（ストップロス -8%、スコア低下）を実装。トレーリングストップや時間決済は未実装だが将来の拡張ポイントとして記載。

- 公共インターフェース
  - strategy パッケージのエクスポート（src/kabusys/strategy/__init__.py）：build_features と generate_signals を公開。
  - research パッケージの __all__ 定義で主要ユーティリティを公開。

### Changed
- 該当なし（初回リリースのため変更履歴はありません）。

### Fixed
- 該当なし（初回リリースのためバグ修正履歴はありません）。

### Security
- ニュース収集で defusedxml を利用し XML 攻撃を軽減。
- news_collector で HTTP レスポンスサイズ上限を設けメモリ DoS を緩和。
- jquants_client のトークン取り扱いはキャッシュ化し、401 時にのみトークン更新を試みることで安全に再認証を行う。

### Notes / 設計方針（重要）
- ルックアヘッドバイアス対策: research/strategy 層は target_date 時点のデータのみを使用する設計。
- 冪等性: DB 保存操作は可能な限り upsert（ON CONFLICT）や日付単位の削除→挿入（トランザクション）で原子性・冪等性を担保。
- 本リリースでは発注 API（kabu ステーション等）との接続層は実装対象外（execution パッケージはプレースホルダ）。
- 外部依存は最小化（標準ライブラリ主体）。ただし XML の安全対策に defusedxml を使用。

### Known limitations / 未実装の機能
- strategy のエグジット条件でトレーリングストップや時間決済ロジックは未実装（コメントで将来実装予定を明示）。
- ニュース→銘柄マッチング（news_symbols 作成の詳細ロジック）は仕様に基づく実装が必要。
- execution 層（実際の発注処理）は未実装。

---

変更の追加・修正・バグ報告がある場合はこの CHANGELOG を更新してください。