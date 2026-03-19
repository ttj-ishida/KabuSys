# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

注意: 以下の変更項目は、提供されたソースコードから推測してまとめたものであり、実際のコミット履歴ではありません。

## [Unreleased]

## [0.1.0] - 2026-03-19

### 追加 (Added)
- プロジェクト初期実装を追加。
  - パッケージメタ情報を定義（kabusys/__init__.py、バージョン: 0.1.0）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - 高機能な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 自動ロードの抑止フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）や既定値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV）を扱う。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値チェック）。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx 等に対応）、429 に対する Retry-After 利用。
  - 401 応答時にリフレッシュトークンでの自動トークン更新を1回だけ行う仕組み（トークンキャッシュをモジュールレベルで保持）。
  - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB へ冪等に保存するための save_* 関数（raw_prices/raw_financials/market_calendar）を実装。ON CONFLICT を利用して更新を行う。
  - データ変換ユーティリティ（_to_float / _to_int）を追加。
  - 取得時に fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス対策を考慮。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード収集と前処理、URL 正規化、トラッキングパラメータ除去、記事ID の SHA-256 ベース生成方針を実装（仕様に基づく）。
  - defusedxml を使った XML パースで安全性を確保し、受信サイズ上限を設ける（MAX_RESPONSE_BYTES）。
  - DB へのバルク INSERT をトランザクションでまとめる方針（チャンクサイズ制御）。
  - デフォルト RSS ソース（Yahoo Finance ビジネス系）を定義。
- リサーチ関連モジュールを追加（src/kabusys/research/）。
  - ファクター計算（factor_research.py）:
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（20日 ATR、相対 ATR、avg turnover、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 営業日ベースの窓長を考慮し、データ不足時は None を返す挙動。
  - 特徴量探索ユーティリティ（feature_exploration.py）:
    - 将来リターン計算（複数ホライズン、1/5/21 日がデフォルト）。
    - IC（Spearman の ρ）計算、ランク関数、統計サマリー（count/mean/std/min/max/median）。
  - re-export（research/__init__.py）で主要関数を公開。
- 戦略層を追加（src/kabusys/strategy/）。
  - 特徴量エンジニアリング（feature_engineering.py）:
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）適用、指定カラムの Z スコア正規化（±3 でクリップ）し features テーブルへ日付単位で置換（トランザクション）。
    - 冪等設計（対象日を削除して挿入）。
  - シグナル生成（signal_generator.py）:
    - features と ai_scores を統合してモメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算し、重み付けで final_score を算出（デフォルト閾値 BUY=0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル閾値を満たす場合）。
    - BUY/SELL ロジック（BUY は閾値超えかつ Bear でない場合、SELL はストップロスとスコア低下）。SELL 判定は BUY より優先し、signals テーブルへ日付単位で置換。
- パッケージ公開 API（strategy/__init__.py、research/__init__.py）を整備。

### 変更 (Changed)
- DuckDB を主要な分析・永続化エンジンとして想定した設計。
  - 各種処理でトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入を用いて原子性とパフォーマンスを確保。
- ロギングを詳細に追加（各処理の成功・警告・デバッグ情報を出力）。

### 修正 (Fixed)
- .env パーサの厳密化により、クォート内のバックスラッシュエスケープやインラインコメント判断、export プレフィックスへの対応を修正想定。
- J-Quants クライアントでの JSON デコードエラー時に詳しいエラーメッセージを出力するよう改善。

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML による攻撃（XML Bomb 等）対策を実施。
- news_collector にて HTTP(S) スキーム以外の URL を扱わない方針（実装コメント）。また、外部 URL 正規化でトラッキングパラメータを削除。
- API クライアントでタイムアウトやネットワークエラー処理、リトライ制御を導入し、外部依存時の堅牢性を向上。

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator のエグジット条件にあるトレーリングストップ（peak_price 必要）や時間決済（保有 60 営業日超過）はコメントで未実装として明示されている。
- news_collector の一部実装（RSS フィード解析の本体や DB 挿入ロジックの続き）は、提供コードスニペットの末尾で切れているため推測に基づく仕様記載が含まれる。
- execution パッケージは空のまま（発注 API との接続ロジックは未実装）。

### マイグレーションノート (Migration notes)
- 環境構築時に以下環境変数の設定が必須:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

（将来のリリースでは、execution 層の発注実装、ニュース記事と銘柄紐付けロジックの完成、追加のテストケース・例外処理強化などを予定）