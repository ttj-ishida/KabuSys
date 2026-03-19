# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。意味のある変更はできるだけ小さく分けています。

# [Unreleased]


# [0.1.0] - 2026-03-19
Initial release

## Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン `0.1.0` を設定。
  - パブリック API: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。  
    - OS 環境変数を保護するための protected キーセットをサポート。
    - `.env.local` は `.env` を上書き（override）する動作。
    - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途等）。
  - `.env` 行パーサーを実装し、以下に対応：
    - コメント行・空行の無視、`export KEY=val` 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（直前にスペースまたはタブがある `#` をコメントとみなす）
  - Settings クラスを追加し、アプリ設定に安全なアクセスを提供：
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティ（必須キーは未設定時に ValueError を送出）
    - 環境（development/paper_trading/live）・ログレベル検証ユーティリティ
    - is_live / is_paper / is_dev のショートカット

- Data レイヤー (kabusys.data)
  - J-Quants API クライアントを実装（jquants_client）:
    - 固定間隔（120 req/min）レート制限（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を考慮）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ、無限再帰防止のため allow_refresh を導入）。
    - ページネーション対応 API 呼び出し（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）、ON CONFLICT 句を用いた更新処理。
    - 型変換ユーティリティ `_to_float` / `_to_int` を追加（厳密な変換ルールで不正値は None に）。
    - fetched_at を UTC ISO8601 で記録して Look-ahead バイアスのトレースをサポート。
  - ニュース収集モジュール（news_collector）:
    - RSS フィードの取得と正規化、raw_news への冪等保存（ON CONFLICT DO NOTHING）をサポート。
    - 記事IDは URL 正規化後の SHA-256 などで一意化する方針（ドキュメント記載）。
    - defusedxml を用いた XML 安全処理、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、トラッキングパラメータ除去、URL 正規化、SSRF 対策等のセキュリティ考慮を実装方針として明示。
    - バルク INSERT のチャンク処理や挿入数の精確なカウント方針。

- Research（研究用）モジュール (kabusys.research)
  - ファクター計算（factor_research.py）:
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - Volatility（20日 ATR、atr_pct、avg_turnover、volume_ratio）
    - Value（per、roe、raw_financials からの最新財務データ取得）
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグや移動平均を計算。
    - データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ（feature_exploration.py）:
    - 将来リターン計算 (calc_forward_returns)：指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman のランク相関を独自に計算（ties は平均ランクで処理）。
    - 統計サマリー (factor_summary) とランク付けユーティリティ (rank) を提供。
  - 研究モジュール全体は外部ライブラリ（pandas 等）に依存しない純粋 Python + DuckDB 実装。

- Strategy（戦略）モジュール (kabusys.strategy)
  - 特徴量生成（feature_engineering.build_features）:
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位で置換（DELETE してから INSERT。トランザクションで原子性確保）。
    - 冪等動作を意識した設計。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - デフォルト重みを用意（momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10）。ユーザ提供の weights は検証・フィルタリングして合計1.0に再スケール。
    - Sigmoid 変換、None は中立 0.5 で補完することで欠損銘柄の不当な降格を防止。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合。ただしサンプル数閾値を設けて誤判定回避）。
    - BUY の閾値（デフォルト 0.60）を超える銘柄に BUY シグナル、保有ポジションに対するエグジット判定で SELL シグナルを生成。
    - SELL 優先ポリシー（SELL 対象を BUY から除外）やランク付けの再計算。
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - stop-loss（-8%）や score 低下によるエグジットを実装。トレーリングストップや時間決済は未実装（コード内に注記）。

## Changed
- N/A（初回リリースのため無し）

## Fixed
- N/A（初回リリースのため無し）

## Security
- news_collector: defusedxml による XML パース、安全な URL 正規化、受信サイズ制限、SSRF/トラッキングパラメータ対策を明示。
- jquants_client: トークン自動リフレッシュの実装で無限再帰を避ける設計（allow_refresh フラグ）。HTTP 429 の Retry-After ヘッダを尊重する実装。

## Notes / Implementation details
- DuckDB を中心に設計しており、多くの処理は SQL（ウィンドウ関数含む）＋最小限の Python ポストプロセスで実装されています。
- 多くの DB 操作はトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入で原子性とパフォーマンスを確保する方針。
- research/strategy 層は発注・execution 層への直接依存を持たない設計（バックテストと本番分離）。
- ロギングおよび警告を多用し、データ欠損や不正入力時に挙動を明示するようにしています。

もし追加でリリース日を変更したい、あるいは未実装機能（トレーリングストップ等）・改善予定の項目を明記してほしい場合は教えてください。