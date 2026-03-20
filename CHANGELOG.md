# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
安定したリリース版はセマンティックバージョニングに従います。

## [Unreleased]

### 追加 (Added)
- 開発用のドキュメント付き実装を多数追加（研究・データ取得・戦略・シグナル生成・設定管理等）。
- DuckDB を用いるデータパイプライン基盤を実装（raw / prices / features / ai_scores / positions 等を前提）。
- 環境変数/設定管理モジュールを実装（kabusys.config）
  - .env/.env.local の自動ロード機能（プロジェクトルート判定は .git / pyproject.toml を使用）。
  - .env パーサは export 形式、クォート、インラインコメントなどに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / Slack 設定 / DB パス / 環境/ログレベル判定など、入力検証付き）。
- J-Quants API クライアントを実装（kabusys.data.jquants_client）
  - 固定間隔のレートリミッタ (_RateLimiter)（120 req/min 想定）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ、429 の Retry-After を尊重）。
  - 401 受信時にリフレッシュトークンから自動的に id_token を再取得して 1 回リトライ。
  - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）。
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT DO UPDATE を利用した save_* 関数）。
  - 入力変換ユーティリティ（_to_float / _to_int）。
  - 取得時刻を UTC で記録し、Look-ahead バイアスのトレーサビリティを確保。
- ニュース収集モジュールを実装（kabusys.data.news_collector）
  - RSS 取得・記事正規化・トラッキングパラメータ除去・URL 正規化（_normalize_url）を実装。
  - defusedxml による XML パース（XML Bomb 等への保護）、受信サイズ上限（MAX_RESPONSE_BYTES）などの安全対策。
  - 記事IDを URL 正規化後の SHA-256 の先頭を使う設計で冪等性を目指す（トラッキングパラメータ排除）。
  - DB へバルク挿入する際のチャンク処理とトランザクションまとめ保存。
- 研究（research）用モジュールを実装（kabusys.research）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）。
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）。
  - 外部ライブラリに依存しない（標準ライブラリ + duckdb）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターをマージ、ユニバースフィルタ適用（最低株価・平均売買代金）、Zスコア正規化（zscore_normalize を利用）と ±3 クリップ、features テーブルへ日付単位の置換（トランザクションで原子性を確保）。
  - ルックアヘッドバイアスの回避方針を明確化（target_date 時点のみ参照）。
- シグナル生成モジュール（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュース（AI）コンポーネントのスコアを計算。
  - コンポーネントを重み付けして final_score を算出、閾値超過で BUY、エグジット条件で SELL を生成。
  - 重みの入力検証とデフォルト値フォールバック・リスケール処理を実装。
  - Bear レジーム検出（ai_scores の regime_score 平均が負）に基づく BUY 抑制。
  - エグジット（SELL）判定ロジックの実装（ストップロス：-8% / スコア降下）、positions テーブル参照、売買シグナルを signals テーブルへ日付単位で置換。
  - トランザクションとロールバックで整合性を担保し、ロールバック失敗時はログ出力。
- パッケージ化
  - kabusys パッケージの __init__ にバージョン情報（0.1.0）とサブパッケージ一覧を追加。

### 変更 (Changed)
- なし（本リリースは初期実装を追加することが主目的のため、既存コードの変更は想定されていません）。

### 修正 (Fixed)
- なし（初期リリースのため特定のバグ修正履歴はありません）。

### セキュリティ (Security)
- defusedxml の採用、RSS/URL 正規化、受信サイズ制限、HTTP スキームチェック等により、外部入力からの攻撃リスクを低減する対策を導入。

---

## [0.1.0] - 2026-03-20

初期公開リリース。上記「Added」に含まれる機能群を初版としてリリース。

主な内容：
- 環境設定ロード・Settings クラス
- J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ・ページネーション）
- DuckDB ベースのデータ永続化ユーティリティ（冪等保存）
- ニュース収集と記事正規化
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー）
- 特徴量生成パイプライン（正規化・フィルタ・features テーブルへの安全な書き込み）
- シグナル生成（final_score 計算、BUY/SELL の生成、signals テーブルへの安全な書き込み）
- Look-ahead バイアス対策の方針と紀録（fetched_at の UTC 記録 等）
- 標準ライブラリと duckdb, defusedxml に依存（外部非必須ライブラリを避ける設計）

注記:
- StrategyModel や DataPlatform の仕様に沿って実装されていますが、ドキュメントの該当セクション（StrategyModel.md / DataPlatform.md 等）を参照してください。
- シグナルの一部条件（トレーリングストップ、時間決済など）はコード内で未実装としてコメントされており、今後の実装予定です。
- 実行（execution）層は本リリースでは未実装（パッケージはプレースホルダあり）。発注 API 連携は将来のリリースで実装予定。

---

今後の予定（例）
- execution 層の実装（kabu API 連携、注文実行・約定管理）
- トレーリングストップ / 時間決済条件の実装
- 単体テスト充実、CI パイプライン整備
- モニタリング・アラート機能（Slack 連携の実装拡張）
- パフォーマンスチューニング（DuckDB クエリ最適化、並列取得等）

---

原文の注意点や設計判断は各モジュールの docstring に記載されています。実装方針・制約（Look-ahead 回避、冪等性、トランザクション原子性、外部依存最小化など）を参照のうえ運用してください。