# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  
安定版のみでなく、設計上の要約や注意点も併せて記載しています。

※ リリース日はコードベースから推測して設定しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回公開リリース。以下の機能群とモジュールを追加しました。

### Added
- パッケージ初期化
  - パッケージのバージョンを定義（kabusys v0.1.0）。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの堅牢化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理
    - クォートなしの行でインラインコメント（#）の扱いを適切に判定
    - 無効行や PK 欠損行のスキップ
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - J-Quants / kabu ステーション / Slack / DB（duckdb/sqlite）パス等
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許可）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須設定が欠如している場合に ValueError を発生させる _require を実装。

- Data モジュール（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - HTTP レスポンスに対するリトライ（指数バックオフ, 最大 3 回）。408/429/5xx を再試行対象に含む。
    - 401 時の自動トークンリフレッシュ（1 回のみ）および module-level の ID トークンキャッシュ実装。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等性を保つ ON CONFLICT 更新）:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 数値変換ユーティリティ _to_float / _to_int（不正値を None にする安全実装）
    - Look-ahead Bias 対策のため fetched_at を UTC タイムスタンプで記録

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード取得と記事パース機能（defusedxml を利用して XML 攻撃を軽減）
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字を使用して冪等性を確保
    - SSRF 対策:
      - リダイレクト時にスキーム検査・ホストのプライベートアドレス判定を行うカスタム RedirectHandler を導入
      - 事前に URL ホストのプライベート判定を行い内部ネットワークへのアクセスを拒否
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - テキスト前処理（URL 除去、空白正規化）
    - 銘柄コード抽出（4桁数字パターン）と既知コードフィルタリング
    - DB 保存（DuckDB）:
      - save_raw_news: INSERT ... RETURNING を使い実際に挿入された記事 ID を返却。チャンク分割とトランザクションを実装。
      - save_news_symbols / _save_news_symbols_bulk: 記事⇔銘柄紐付けの一括挿入（ON CONFLICT DO NOTHING）とトランザクション管理
    - run_news_collection: 複数ソースを順次処理し、ソース単位でエラー隔離を行う統合ジョブ

- Research モジュール（kabusys.research）
  - feature_exploration（特徴量探索）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1/5/21 営業日）の将来リターンを DuckDB の prices_daily から一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（欠損/非有限値を除外、十分なサンプルがない場合 None を返す）
    - rank: 同順位は平均ランクを採るランク変換（丸め誤差対策に round(v, 12) を使用）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す
    - 設計としては pandas 等外部依存を避け、標準ライブラリのみで実装
  - factor_research（ファクター計算）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）の計算
      - スキャンレンジやウィンドウサイズは定数化（例: MA200, momentum windows）
      - データ不足の銘柄には None を返す
    - calc_volatility: atr_20（20日 ATR）・atr_pct・avg_turnover・volume_ratio の計算
      - true_range の NULL 伝播を正確に扱い、部分窓に対するカウントも管理
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0 または欠損なら PER は None）
    - すべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部 API にはアクセスしない設計

- DB スキーマ初期化ユーティリティ（kabusys.data.schema）
  - DuckDB 用の DDL を定義（Raw Layer を中心に定義）
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（NOT NULL / CHECK / PRIMARY KEY 等の制約を含む）
  - スキーマ設計は Raw / Processed / Feature / Execution の 3 層構造を想定

- パッケージエクスポート（kabusys.research.__init__）
  - 研究用ユーティリティとファクター計算関数を __all__ にて公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

### Security
- ニュース収集モジュールで以下の安全対策を実装:
  - defusedxml を使った XML パース（XML Bomb 等の軽減）
  - SSRF 対策（スキーム検査、プライベート IP/ホスト検出、リダイレクト検査）
  - レスポンスサイズ制限と gzip 解凍後チェック（メモリ DoS / Gzip bomb 対策）
- J-Quants クライアントでトークン管理とリトライ制御を実装し、認証周りの堅牢性を向上

### Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings で必須とされている。未設定時は ValueError が発生します。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を protected として上書きしません）
- DuckDB スキーマは初期化ロジックを通じて適用してください（このリリースでは DDL 定義を提供）。
- Research モジュールは外部ライブラリに依存しない実装を目指しており、パフォーマンス上の配慮から DuckDB 側での集約を多用しています。
- news_collector は外部 RSS フィードの構造差異に対しフォールバックを用意していますが、極端に非標準なフィードは正しく解析できない場合があります。

### Known limitations / TODO
- Strategy / Execution / Monitoring パッケージの実装はこのリリースでは未掲載（パッケージ構成は存在）。
- 一部 DDL（raw_executions など）はファイル切り出しの都合で抜粋されています。完全なスキーマ整備を今後進める予定。
- 単体テストや統合テストのスイートはこのスナップショットには含まれていないため、運用前に実データでの検証を推奨します。

---

保持方針:
- 重要な API 互換性の破壊的変更はメジャーバージョンを上げて通知します。
- バグ修正や小改善はマイナーバージョンでリリースします。

(End of CHANGELOG)