# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

全般:
- 初期バージョン: 0.1.0
- リリース日: 2026-03-19

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基礎構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）

- 環境設定/自動ロード機能（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装（export 形式、クォート処理、インラインコメント処理に対応）。
  - .env と .env.local の読み込み順序を定義（OS 環境変数 > .env.local > .env）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム環境・ログレベル等の取得と検証（必須 env は未設定時に ValueError を送出）。

- データ取得・保存（J-Quants クライアント）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（トークン取得、ページネーション対応）。
  - レートリミッタ（120 req/min 固定スロットリング）を実装。
  - リトライロジック（指数バックオフ、最大試行回数、特定ステータスでの挙動）を実装。
  - 401 応答時の自動トークンリフレッシュを実装（1 回までのリトライ）。
  - API レスポンスの保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。DuckDB への保存は冪等（ON CONFLICT）で実施。
  - データ型変換ユーティリティ（_to_float, _to_int）を追加し、不正値を安全に扱う。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集ロジックを実装（デフォルトに Yahoo Finance のビジネス RSS を設定）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント削除）。
  - セキュリティ対策: defusedxml を用いた XML の安全解析、受信バイト数制限（最大 10MB）、HTTP スキームチェック等。
  - 記事 ID は正規化 URL のハッシュで生成し冪等性を確保。
  - バルク INSERT チャンク化によるパフォーマンス配慮。

- 研究（research）モジュール（src/kabusys/research/*.py）
  - ファクター計算（factor_research）を実装:
    - calc_momentum: 1m/3m/6m リターン、200日移動平均乖離率（MA200）を計算。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER 等を算出。
    - DuckDB の prices_daily / raw_financials を前提にした実装。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21 日）を一括取得。
    - calc_ic: スピアマンランク相関（IC）計算。サンプル数が不足する場合は None を返す。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ。
  - research パッケージの __all__ を整備。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research モジュールの生ファクターを結合・ユニバースフィルタ適用・Zスコア正規化・±3 クリップして features テーブルへ日付単位で置換（トランザクションで原子性を確保）。
  - ユニバース条件: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
  - 欠損値・外れ値対策を実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合し final_score を算出して BUY/SELL シグナルを生成、signals テーブルへ日付単位で置換。
  - スコアのコンポーネント:
    - momentum, value (PER ベースの逆数スコア), volatility (atr_pct の反転), liquidity (volume_ratio), news (AI スコアのシグモイド変換)。
  - 欠損コンポーネントは中立値 0.5 で補完。
  - 重みの検証と合計再スケール処理を実装（不正な値はスキップ）。
  - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
  - エグジット判定（SELL）を実装（ストップロス: -8%／スコア低下）。保有銘柄価格欠損時の判定スキップやログ出力あり。
  - BUY と SELL の優先ポリシー（SELL 優先で BUY から除外、ランキング再付与）。
  - トランザクションによる日付単位置換で原子性を保証。

### 変更 (Changed)
- N/A（初期リリースのため「変更」はなし）

### 修正 (Fixed)
- N/A（初期リリースのため「修正」はなし）

### セキュリティ (Security)
- news_collector で defusedxml を利用し XML 関連の攻撃を防止。
- RSS 取得で受信サイズ制限や URL 正規化、HTTP スキーム検証を導入し SSRF / DoS を軽減。
- J-Quants クライアントでネットワークエラー/HTTP エラーに対する堅牢な再試行とトークンリフレッシュを実装。

### 既知の制限・未実装事項
- signal_generator のエグジット判定でトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- 一部ユーティリティ（zscore_normalize 等）は data.stats に依存（該当実装は別ファイルに存在する想定）。
- feature_engineering / signal_generator は発注 API（execution 層）への直接依存を持たない設計。発注層は別途実装が必要。

---

注: 上記は提供されたコードベースの内容から推測して作成した CHANGELOG です。実際のリリースノート作成時はコミット履歴やプロジェクト管理ツールの情報を合わせて更新してください。