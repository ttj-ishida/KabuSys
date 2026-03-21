# CHANGELOG

すべての変更は Keep a Changelog の形式に従い記載しています。  
重要: このログはリポジトリ内のソースコードを解析して推測した内容に基づくものであり、実際のコミット履歴ではありません。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買フレームワークのコア機能を提供します。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージのエントリポイント
  - kabusys パッケージを追加。バージョンは 0.1.0。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml）から読み込む機能を実装。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env 行パーサを実装（コメント行・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理に対応）。
  - _load_env_file にて既存 OS 環境変数を保護する protected セットを導入。
  - Settings クラスを提供し、環境変数をプロパティ形式で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須としてチェック。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を定義。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証。
    - is_live / is_paper / is_dev の便宜プロパティを追加。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔の RateLimiter（120 req/min を想定）を導入。
    - 冪等なページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - リトライ戦略（最大 3 回、指数バックオフ、408/429/5xx を対象）、429 の場合は Retry-After を尊重。
    - 401 応答時にリフレッシュトークンから id_token を再取得して 1 回だけリトライする自動リフレッシュ機能を実装。モジュールレベルで id_token をキャッシュ。
    - HTTP レスポンスの JSON デコードチェックと明確な例外発生。
  - DuckDB への保存用関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - INSERT ... ON CONFLICT DO UPDATE により冪等保存を実現。
    - fetched_at を UTC ISO8601 形式で記録。
    - PK 欠損レコードはスキップし、スキップ件数をログ警告。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し安全にパース。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の基礎機能を実装。
  - URL 正規化機能を実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート）。
  - defusedxml を利用して XML 攻撃を防止。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）や SSRF 対策（HTTP/HTTPS スキームの想定）等、堅牢性を考慮した設計。
  - バルク INSERT チャンク（_INSERT_CHUNK_SIZE）により DB 書き込み負荷を制御。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム / ボラティリティ / バリュー計算関数を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA のカウントチェック）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播を考慮）
    - calc_value: per（EPS が 0/NULL の場合は None）, roe（最新財務データを target_date 以前から取得）
  - DuckDB を活用した SQL ベースの実装で、必要データ範囲を限定してパフォーマンス配慮。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で算出した生ファクターを統合・正規化して features テーブルへ保存する build_features を実装:
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - zscore_normalize を利用した Z スコア正規化（対象カラムを限定）。
    - Z スコアを ±3 でクリップして外れ値影響を抑制。
    - 日付単位で DELETE → INSERT をトランザクションで行い原子性を担保（冪等）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコアを計算し signals テーブルへ保存する generate_signals を実装:
    - momentum / value / volatility / liquidity / news の重み付けを実装（デフォルト重みを定義）。
    - 重みの入力検証（未知キー・非数値・負値は無視）と合計が 1.0 でなければ再スケール。
    - Z スコアを sigmoid で [0,1] に変換するユーティリティ、欠損値は中立 0.5 で補完して不当な降格を防止。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）時は BUY シグナルを抑制。
    - BUY 生成閾値（デフォルト 0.60）を超える銘柄を BUY とする一方、エグジット判定（STOP LOSS -8% または スコア低下）で SELL を生成。
    - SELL は BUY より優先し、signals テーブルへトランザクション + バルクで日付単位置換。

- 研究用ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算 calc_forward_returns（複数ホライズン対応、取得範囲を buffer で限定）。
  - スピアマンランク相関（IC）計算 calc_ic（欠損・サンプル数チェック、同順位の平均ランク処理を含む）。
  - factor_summary による基本統計量（count/mean/std/min/max/median）を計算する関数を提供。
  - rank 関数は ties を平均ランクで扱い、丸めて ties 検出の安定化を図る。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- news_collector で defusedxml を使用し XML パーシングの脆弱性（XML Bomb 等）に配慮。
- ネットワーク I/O ではタイムアウトや受信サイズ上限を想定した防御策を盛り込み、外部データを扱う際の安全性を向上。

### 既知の制約 / 注意点 (Known issues / Notes)

- calc_forward_returns やファクター計算は「営業日ベース（連続レコード数）」を前提としており、カレンダー日ではないことに注意。
- 一部機能（例: トレーリングストップ、時間決済）は comments に記載のとおり未実装であり、positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の記事 ID 生成、抽出の詳細ロジック（ハッシュ生成・銘柄紐付け等）は設計コメントにあるが、実装の残り部分は今後の開発対象。
- J-Quants クライアントは rate limiting / retry / token refresh を実装しているが、実運用でのエッジケース検証（頻発する 429、ネットワーク断など）は要確認。

---

注: 実装の意図や仕様はソース内の docstring・コメントから推定しました。実際の変更履歴やコミットメッセージを元にした正確な CHANGLEOG を作成する場合は、Git の履歴を参照してください。