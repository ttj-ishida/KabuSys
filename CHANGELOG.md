# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

## [0.1.0] - 2026-03-21

初回リリース — KabuSys 日本株自動売買システムの基盤実装を追加しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期公開。バージョンは 0.1.0。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルと OS 環境変数から設定を自動ロードする機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定するため、CWD に依存しない動作を意図。
  - .env パーサを実装（コメント、export 形式、クォート内のエスケープ、インラインコメントの扱い、トラッキングなどに対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト時などで自動ロードを無効化可能）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル等の設定プロパティを公開。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装（許容値は定義済み）。

- データ取得・保存 (src/kabusys/data)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出し用 HTTP ユーティリティを実装。ページネーション対応。
    - 固定間隔スロットリングによるレート制限 (_RateLimiter、120 req/min)。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。429 の場合は Retry-After を優先。
    - 401 受信時の自動トークンリフレッシュ（リフレッシュは最大 1 回）とトークンキャッシュ共有。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT / DO UPDATE による冪等保存を行う。
    - データ変換ユーティリティ（_to_float, _to_int）で不正データに寛容に扱う実装。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィードから記事収集し raw_news へ冪等保存する基盤実装。
    - URL 正規化（トラッキングパラメータ除去・キーソート・フラグメント除去など）と記事 ID の生成方針（URL 正規化後のハッシュ）を実装。
    - defusedxml を用いた XML パースで XML 攻撃に対する堅牢化。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）やバルク INSERT チャンクなどによる DoS 対策、SQL パフォーマンス対策を実装。
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定。

- 研究（Research）モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1/3/6 月リターン、200日移動平均乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などのファクター計算を DuckDB(SQL) ベースで実装。
    - 営業日ベースのウィンドウ設計、欠損時の None 扱い、スキャン範囲に安全マージンを持たせる設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 複数ホライズンに対応、1/5/21 日をデフォルト）、IC（Spearman の ρ）計算（calc_ic）、ファクター統計サマリー (factor_summary)、ランク付け util (rank) を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。

- 戦略（Strategy）モジュール (src/kabusys/strategy)
  - feature_engineering.py
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）を適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）する build_features を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用する方針。
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
    - モメンタム/バリュー/ボラティリティ/流動性/ニュース（AI）を重み付きで合算（デフォルト重みを定義）。ユーザー重みは検証・正規化して適用。
    - Bear レジーム検知（ai_scores の regime_score 平均が負なら Bear、ただしサンプル閾値あり）による BUY 抑制。
    - エグジット条件（ストップロス: -8%、スコア低下）による SELL 判定を実装（positions テーブルを参照）。BUY と SELL の競合は SELL を優先して排除。
    - signals テーブルへの日付単位置換をトランザクションで実装（冪等）。
    - ロギング・不正データ耐性を考慮。

### 変更 (Changed)
- （初回リリースのためなし）設計・実装は上記新規追加に相当。

### 修正 (Fixed)
- データ保存・処理の堅牢化を図る実装を多数追加：
  - raw データの PK 欠損行をスキップしてログを出力する動作を追加（save_* 関数）。
  - JSON デコード失敗時に詳細を含んだ例外を投げる処理を追加（J-Quants のレスポンス検証）。
  - HTTP リトライ時のログ・待機戦略を明確化。

### セキュリティ (Security)
- news_collector で defusedxml を採用し XML 攻撃を防止。
- ニュース URL の正規化でトラッキングパラメータを除去し、ID 決定の冪等性を確保。
- RSS フィード取得において受信バイト数上限を設定しメモリ DoS を緩和。
- J-Quants クライアントでタイムアウトやエラーハンドリングを強化（過度な再試行を避ける設計）。

### 注意事項 / 未実装の機能 (Notes)
- signal_generator 内の一部エグジット条件（トレーリングストップや時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加データが必要（コード内にコメントあり）。
- news_collector の SSRF 関連なより厳密な外部接続制御は実装方針にあるが、実装済のチェック（ipaddress / socket ベースの制限など）は将来的に拡張の余地あり。
- Research モジュールはあくまで prices_daily / raw_financials のみ参照。実運用ではデータ整備（欠損補完、日付整合性）に注意が必要。
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）未設定時は ValueError が発生します。リリース前に .env を準備してください。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  必要に応じて環境変数で上書きしてください。

### 互換性 (Compatibility)
- 初期リリース。後続バージョンで設定キー名や DB スキーマを変更する可能性があります。マイグレーションに関する注意は次回以降に記載します。

---

今後の予定（短期的ロードマップの例）
- execution 層の実装（kabu ステーション API 連携、注文ロジック、rate limiting）
- monitoring 層（ポジション・注文状態の監視、Slack 通知の統合）
- テストカバレッジの整備（ユニット・統合テスト）
- パフォーマンス改善（大量銘柄処理時のバルク処理最適化）

（この CHANGELOG はソース中の docstring と設計コメントに基づき作成しています。実際の変更履歴はコミットログと合わせてご確認ください。）