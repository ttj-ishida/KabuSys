# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このリポジトリの初期リリースに相当する変更履歴をコードベースから推測して作成しています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加 (`src/kabusys/__init__.py`)。バージョンを "0.1.0" に設定し、公開サブパッケージを __all__ に宣言（data, strategy, execution, monitoring）。
- 設定・環境変数管理
  - 環境変数/設定管理モジュールを追加 (`src/kabusys/config.py`)。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - 読み込み時の override/protected 制御を実装（OS 環境変数を保護）。
    - 必須環境変数取得メソッド _require と Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル判定など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許可値の検査）。
- Data 層（DuckDB）
  - DuckDB スキーマ定義モジュールを追加 (`src/kabusys/data/schema.py`)。
    - raw_prices / raw_financials / raw_news / raw_executions 等のテーブル DDL 定義を提供し、3 層アーキテクチャ（Raw / Processed / Feature / Execution）に沿った初期化が可能。
- J-Quants API クライアント
  - `src/kabusys/data/jquants_client.py` を追加。
    - API 呼び出し共通処理（_request）を実装。JSON デコード、最大リトライ回数、指数バックオフ、429 の Retry-After 対応、401 発生時の自動トークンリフレッシュ（1 回のみ）を実装。
    - 固定間隔レートリミッタを実装（120 req/min をデフォルト）。モジュールレベルの ID トークンキャッシュを実装し、ページネーション間で共有。
    - ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 型安全な変換ユーティリティ _to_float, _to_int を実装（不正値や小数誤変換を防止）。
- ニュース収集モジュール
  - `src/kabusys/data/news_collector.py` を追加。
    - RSS フィードからの記事収集（fetch_rss）、テキスト前処理（URL 除去・空白正規化）、記事ID生成（正規化 URL の SHA-256 先頭 32 文字）を実装。
    - XML パースに defusedxml を利用して XML 攻撃（XML Bomb 等）を防止。
    - SSRF 対策を多数実装:
      - URL スキーム検証（http/https のみ）
      - フェッチ前にホストがプライベートアドレスか検査
      - リダイレクト時にもスキームとプライベートアドレス確認するカスタムハンドラを導入
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック
    - DB 保存はチャンク化とトランザクションで処理、INSERT ... RETURNING を活用して実際に挿入された ID / 件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes）と統合収集ジョブ run_news_collection を実装。既知銘柄セットに基づく紐付け処理をサポート。
- 研究（Research）モジュール
  - `src/kabusys/research/feature_exploration.py` を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1 クエリでまとめ取得）。
    - ファクター有効性評価 calc_ic（Spearman の ρ、ランク関数 rank を内部提供）。
    - ファクター統計要約 factor_summary（count/mean/std/min/max/median）。
    - 実装は標準ライブラリのみで依存を最小化、prices_daily テーブルのみ参照する設計。
  - `src/kabusys/research/factor_research.py` を追加。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility/流動性（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を計算する関数 calc_momentum, calc_volatility, calc_value を実装。
    - DuckDB のウィンドウ関数・OVER を活用し、データ不足時の None 扱いなどを厳密に扱う。
  - `src/kabusys/research/__init__.py` で主要ユーティリティを再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- その他モジュールのひな型
  - strategy/execution パッケージの __init__ ファイルを追加（今後の拡張余地）。

### 変更 (Changed)
- （この初期リリースにおける設計上の決定）
  - DuckDB を組み込みデータストアとして採用し、取得データの冪等保存（ON CONFLICT）や INSERT RETURNING を前提とした API を整備。
  - 研究モジュールは外部ライブラリ（pandas 等）に依存しない実装を優先し、軽量に保つ設計にした。

### 修正 (Fixed)
- （初期実装で想定される問題点を考慮した堅牢性改善）
  - .env パースでのクォート内エスケープ対応やインラインコメントの扱いを実装し、一般的な .env フォーマットへの互換性を向上。
  - fetch_rss の XML パース失敗や大きすぎるレスポンスに対して明示的にログを出し空結果で安全に戻すようにした。

### セキュリティ (Security)
- NewsCollector における SSRF 対策および XML パースの安全化（defusedxml）を導入。
- J-Quants クライアントでの認証トークン自動リフレッシュ時の無限再帰回避（allow_refresh フラグ）や、レート制御・リトライの方針を実装。429 の Retry-After を尊重。
- ニュース収集時の外部 URL の正規化とトラッキングパラメータ除去により、ID 決定を安定化（冪等性強化）。

### 既知の制限 (Known limitations)
- research モジュールは標準ライブラリのみを使う設計のため、大規模データ分析や高速な DataFrame 操作は外部ライブラリ（pandas 等）使用時より柔軟性が劣る可能性がある。
- DuckDB 側で INSERT ... RETURNING を使用しているため、組み込みの DuckDB バージョンや実行環境によっては互換性に注意が必要（想定は最新互換）。
- raw_executions テーブル定義はファイルの途中で切れている（現状は未完成の可能性あり）。初期スキーマ実装は継続的に拡張予定。

### 依存関係
- defusedxml をニュース XML の安全パースに使用（明示的な依存）。

---

注: 上記は提供されたソースコードから推測した初期リリース向けの CHANGELOG です。実際のコミット履歴や追加の変更点があれば、該当箇所を反映して更新してください。