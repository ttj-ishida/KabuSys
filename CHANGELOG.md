# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
各リリースではコードベースから推測される追加機能、改善点、修正点、設計上の注意点等を記載しています。

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更（後方互換性に注意）
- Fixed: バグ修正
- Security: セキュリティ関連の改善
- Performance: パフォーマンス改善

## [Unreleased]
- （現時点のスナップショットは v0.1.0 として最初の公開に相当します。今後の変更はここに記載してください）

## [0.1.0] - 2026-03-20
初期リリース。このバージョンは日本株自動売買システムのコアライブラリ群を提供します。主要なサブパッケージと主な挙動は以下の通りです。

### Added
- パッケージ概要
  - kabusys パッケージ初期版を追加。パッケージバージョンは `0.1.0`。
  - エクスポート対象: data, strategy, execution, monitoring（execution は空の __init__ を持つがレイヤーとして用意）。

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込みする仕組みを追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサーの強化:
    - コメント行・空行の無視、"export KEY=val" 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープ処理含む）
    - インラインコメントの扱いルール（クォートなしは直前にスペース/タブがある '#' をコメントとして扱う）
  - 環境値取得ユーティリティ Settings を追加（J-Quants, kabu station, Slack, DB パス, env/ログレベル検証等）
  - 設定値検証（KABUSYS_ENV・LOG_LEVEL の許容値チェック）と補助プロパティ（is_live 等）を提供。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔レートリミッタ（120 req/min 相当）
    - HTTP リトライ（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）
    - 401 受信時はリフレッシュトークンから ID トークンを再取得して1回リトライ
    - ページネーション対応（pagination_key の共有）
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し Look-ahead バイアスを追跡可能に
  - DuckDB への保存関数を追加（raw_prices / raw_financials / market_calendar）:
    - 冪等性を保つため ON CONFLICT DO UPDATE を利用したアップサート実装
    - PK 欠損レコードはスキップして警告ログを出力
    - 型変換ユーティリティ（_to_float / _to_int）を実装（意図しない丸めを防ぐ挙動を含む）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得して raw_news へ冪等保存する仕組みを追加
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装
  - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保
  - XML パースに defusedxml を利用して XML Bomb 等の攻撃を軽減
  - HTTP レスポンスの最大受信バイト数を設定してメモリ DoS を防止
  - SSRF 回避のためスキームフィルタなどの考慮（コメントベースの設計指針）
  - バルク INSERT のチャンク処理を追加して DB オーバーヘッドを削減

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）
    - Volatility: ATR 20 日、atr_pct、avg_turnover（20 日平均売買代金）、volume_ratio
    - Value: per, roe（raw_financials と prices_daily を組み合わせて計算）
    - SQL ベースの計算により DuckDB のみ参照。外部 API に依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応（デフォルト [1,5,21]）、入力バリデーション
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関（同順位は平均ランク処理）
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median
    - 小さな数理ユーティリティ（rank）実装（丸め対策による ties の扱い）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を追加:
    - research モジュールから得た生ファクターをマージしてユニバースフィルタ（最低株価・最低売買代金）適用
    - 正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT により原子性を保証）
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照するロジック

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を追加:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - スコア正規化に sigmoid を利用、欠損値は中立値 0.5 で補完し過度な降格を防止
    - デフォルト重みを定義し、ユーザ渡し weights のバリデーション＋合計が 1 でない場合の再スケール処理
    - Bear レジーム判定（AI の regime_score 平均が負であれば BUY 抑制）
    - BUY シグナル閾値（デフォルト 0.60）
    - SELL シグナル（エグジット）判定（ストップロス -8% / final_score が閾値未満）
    - positions, prices_daily から現在保有ポジションを取得して SELL 判定を実行
    - signals テーブルへ日付単位で置換（トランザクションで原子性）

### Security
- XML パースで defusedxml を使用して XML ベース攻撃を軽減（news_collector）。
- RSS URL 正規化・スキーム検証等で SSRF リスクを考慮する設計指針を導入。
- HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES）を設定してメモリ消費攻撃を軽減。

### Performance
- J-Quants API クライアントに固定間隔レートリミッタを実装し API レート制限に準拠。
- ページネーション間で ID トークンをキャッシュし再利用。
- DuckDB へのバルク挿入を executemany で実施、raw_news のチャンク化を導入。
- features / signals への日付単位置換で一度に DELETE→INSERT を行い原子性とオーバーヘッド低減を実現。

### Design / Notes
- ルックアヘッドバイアス対策が各所に実装（target_date 時点のデータのみ使用、fetched_at の記録など）。
- 外部発注 API への直接依存を持たない設計（strategy 層は execution 層に依存しない）。
- DuckDB に依存する設計（prices_daily / raw_financials / positions / ai_scores / features / signals 等のテーブル前提）。
- 一部機能は設計書（StrategyModel.md, DataPlatform.md, Research docs 等）に依存する想定（コメント参照）。
- 未実装/将来的実装予定の機能（コード中にコメントあり）:
  - signal_generator: トレーリングストップや時間決済（positions に peak_price/entry_date が必要）
  - news_collector: （実装上の詳細は続くが、ファイルは途中まで提供されている）

### Fixed
- （初期リリースのため既知のバグフィックス履歴はなし。実装上の堅牢性対策（例: PK 欠損でのスキップ・警告、数値変換ユーティリティ）を多数導入。）

---

今後のリリースでは、execution 層（発注ロジック）・monitoring 層（アラート/メトリクス）・テスト/CI の整備、さらなる戦略/リサーチ機能の拡張、ドキュメント（StrategyModel.md 等）の同梱・明文化を予定しています。必要であれば、本 CHANGELOG を英語版やより細かなコミット単位に分割して生成します。