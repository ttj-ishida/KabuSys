# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

### Added
- ドキュメント化された設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local の自動ロード機能（プロジェクトルート探索：.git または pyproject.toml を基準）。
  - export 形式やクォート・エスケープ、行内コメント処理に対応した .env パーサ実装。
  - 環境変数の保護（既存 OS 環境変数はデフォルトで上書きされない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラス経由で各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）およびパス設定（DUCKDB_PATH/SQLITE_PATH）を提供。環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL）を実装。

- データ取得・保存モジュール（kabusys.data.jquants_client）を追加。
  - J-Quants API から日足・財務・マーケットカレンダーを取得するクライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min）実装。
  - 指数バックオフを用いたリトライ（最大3回）、408/429/5xx の再試行、429 の Retry-After 対応。
  - 401 時の自動トークンリフレッシュ（1回）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応 fetch_* 関数と、DuckDB への冪等保存（ON CONFLICT DO UPDATE）を提供。
  - データ型変換ユーティリティ（_to_float / _to_int）を追加し、意図しない丸めを回避。

- ニュース収集モジュール（kabusys.data.news_collector）を追加。
  - RSS フィードから記事を収集し raw_news に保存する処理を実装。
  - URL の正規化（トラッキングパラメータ除去・ソート・フラグメント削除）や記事 ID のハッシュ化による冪等化。
  - defusedxml を利用した XML パースで XML Bomb 等の攻撃耐性を確保。
  - レスポンスサイズ制限や安全な URL スキーマ検証、バルク挿入チャンク化による DoS や SSRF 対策を考慮。

- リサーチ用ファクター計算モジュール群（kabusys.research）を追加。
  - calc_momentum / calc_volatility / calc_value により prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
  - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得。
  - calc_ic: スピアマンランク相関（IC）計算を実装（ties の平均ランク処理を含む）。
  - factor_summary / rank: ファクターの統計サマリーとランク付けユーティリティを提供。
  - 外部ライブラリに依存せず、DuckDB + 標準ライブラリのみで実装。

- 戦略関連モジュール（kabusys.strategy）を追加。
  - feature_engineering.build_features:
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）適用、Zスコア正規化（クリップ ±3）、features テーブルへの日付単位での置換（トランザクション）を実装。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ利用。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）のスコアを計算し、重み付き合算で final_score を生成。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）による BUY 抑制。
    - BUY 閾値、エグジット条件（ストップロス、スコア低下）に基づく BUY/SELL シグナル生成と signals テーブルへの日付単位置換（トランザクション）。
    - weights 入力の検証・補完・再スケーリング、欠損コンポーネントは中立値 0.5 で補完するポリシーを実装。

- 共通ユーティリティ・安全対策
  - DuckDB トランザクションを用いた原子性確保（features/signals の日付単位置換）。
  - ロギング（情報/警告/デバッグ）の導入と、例外発生時のロールバック・警告。
  - ルックアヘッドバイアス回避や冪等性を意識した設計が随所に反映。

### Changed
- （開発初期なので今回リリースでの差分はなし）

### Fixed
- （Unreleased: まだ報告されたバグはなし）

### Security
- XML パースに defusedxml を使用して安全性を向上（news_collector）。
- 外部 URL の取り扱いでスキーム検証・受信サイズ制限などを追加。

---

## [0.1.0] - 2026-03-21

最初の公開リリース。本パッケージのコア機能を実装。

### Added
- パッケージ初期化とバージョン定義（kabusys.__version__ = "0.1.0"）。
- 環境設定管理（kabusys.config） — .env 自動読み込み、Settings API、バリデーション。
- J-Quants API クライアント（kabusys.data.jquants_client） — 取得、ページネーション、保存（DuckDB）をサポート。レート制限・リトライ・自動トークンリフレッシュを実装。
- ニュース収集（kabusys.data.news_collector） — RSS 収集、正規化、冪等保存、セキュリティ対策。
- リサーチ（kabusys.research） — モメンタム/ボラティリティ/バリュー計算、将来リターン、IC、統計サマリ。
- 戦略（kabusys.strategy） — 特徴量構築（build_features）、シグナル生成（generate_signals）。ユニバースフィルタ、Zスコア正規化、Bear レジーム対応、エグジット判定を実装。
- DuckDB 向けの冪等保存ユーティリティ（raw_prices/raw_financials/market_calendar への upsert）。
- 小さなユーティリティ（_to_float/_to_int、rank、zscore_normalize の導入は data.stats で提供される想定）。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Security
- RSS XML の安全なパース（defusedxml）。
- API 呼び出しのエラーハンドリング強化（リトライ・バックオフ・429 Retry-After の考慮）。

---

その他、設計メモ:
- ほとんどのデータ保存処理は「日付単位の置換（DELETE then bulk INSERT をトランザクションで実行）」で冪等性と原子性を確保しています。
- ルックアヘッドバイアス防止のため、各処理は target_date 当時に利用可能なデータのみを参照するよう設計されています。
- 今後の予定: ポジション管理でのトレーリングストップ実装、追加ファクター（PBR/配当利回りなど）、および execution 層（kabuステーション連携）の実装・統合。

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴やリリース日付はリポジトリの履歴に基づいて調整してください。