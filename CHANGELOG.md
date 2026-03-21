# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従ってバージョニングしています。

※この CHANGELOG は提供されたコードベースの内容から推測して作成しています（実装コメント・API 意図に基づく要約）。実際の変更履歴はリポジトリのコミット履歴をご参照ください。

## [Unreleased]

（現時点の作業中・未リリースの変更はここに記載します。現状、特定の未リリースコミット情報はありません。）

---

## [0.1.0] - 2026-03-21

初期リリース。日本株自動売買システムのコアライブラリを提供します。以下の主要機能・設計上の決定が含まれます。

### 追加
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージを __all__ に定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env パーサを実装（export プレフィックス対応、引用符内のエスケープ処理、行内コメント処理など）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）やログレベルの取得とバリデーションを行うプロパティを追加。
  - 必須環境変数未設定時は ValueError を発生させる _require() 実装。

- Data 層（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。主機能：
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - HTTP リクエストの共通処理（JSON デコード、ヘッダ、ページネーション対応）。
    - 冪等性を意識した保存 API（DuckDB へ ON CONFLICT DO UPDATE を用いた保存関数）。
    - リトライ（指数バックオフ、最大 3 回）、429 の場合は Retry-After を優先、408/429/5xx は再試行対象。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - データ取得関数を提供：
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数を提供：
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 型変換ユーティリティを実装（_to_float/_to_int）し、不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（初期 RSS ソースに Yahoo Finance を設定）。
  - セキュリティ上の対策を設計・一部実装：
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - URL 正規化（トラッキングパラメータ削除・スキームとホスト小文字化・フラグメント削除・クエリソート）、記事ID は正規化 URL の SHA-256（先頭 32 文字）を用いる方針（冪等性）。
    - DB へのバルク挿入はチャンク化して実行（_INSERT_CHUNK_SIZE = 1000）。
  - raw_news / news_symbols などの保存設計（ON CONFLICT DO NOTHING 等）を採用。

- 研究用モジュール（kabusys.research）
  - factor_research：prices_daily / raw_financials からファクター算出関数を実装
    - calc_momentum：1M/3M/6M リターン、MA200 乖離（cnt_200 によるデータ不足扱い）
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value：最新財務データから PER / ROE を算出（EPS=0 は None）
  - feature_exploration：研究用解析ユーティリティを実装
    - calc_forward_returns：LEAD を用いた複数ホライズン（デフォルト 1,5,21 日）の将来リターン算出
    - calc_ic：ランク相関（Spearman ρ）を実装（同順位は平均ランク）
    - factor_summary：count/mean/std/min/max/median の統計要約
    - rank：同順位の平均ランク処理（丸め処理で ties 検出の安定化）
  - research パッケージの公開 API を整備（主要関数を __all__ に登録）。

- 戦略層（kabusys.strategy）
  - feature_engineering.build_features
    - research による生ファクターを取得してマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列に対して Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 にクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）。冪等。
  - signal_generator.generate_signals
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）を重み付き合算して final_score を算出（デフォルト重みを提供）。
    - シグナル生成ロジック：
      - Bear レジーム検出（ai_scores の regime_score 平均が負の場合。サンプル数閾値あり）
      - Bear 時は BUY シグナルを抑制
      - BUY: final_score >= threshold（デフォルト 0.60）
      - SELL（エグジット）: ストップロス（終値/avg_price - 1 < -8%）または final_score が閾値未満
    - weights の入力検証・スケーリング（未知キーや NaN/負値を無視、合計を 1.0 に正規化）。
    - signals テーブルへ日付単位で置換（トランザクションで原子性）。SELL 優先で BUY から除外。

### 変更
- （初期リリースのため既存コードからの変更履歴はなし。上記は実装された主要機能の一覧です。）

### 修正
- .env 読み込みの堅牢化：ファイルが開けない場合は warnings.warn で通知して処理継続。
- jquants_client の HTTP リトライ・トークン処理で無限再帰・過剰リトライを回避する制御を実装。

### 既知の未実装 / 注意点（ドキュメントに基づく）
- signal_generator の SELL 条件について、トレーリングストップや保有期間ベースの時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- research.calc_value: PBR・配当利回りは現バージョンで未実装。
- news_collector の一部（IP/SSRF 完全ガードや URL スキーム検証など）は設計通り実装されているが、実運用での細かい検証が必要。
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize 等）は別モジュールで提供される想定（本 changelog 作成時点での呼び出し箇所は存在）。

### 破壊的変更
- なし（初期リリース）。

### セキュリティ
- RSS パースに defusedxml を使用し XML 攻撃対策を実施。
- ニュース収集での受信サイズ制限やトラッキングパラメータ除去など、情報漏洩・DoS 対策を導入。
- J-Quants クライアントでトークンの自動リフレッシュと安全なキャッシュ運用を実装（ただしトークン管理はユーザ環境側の保護が必要）。

---

付記（利用者向け注意）
- 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）は Settings のプロパティで必須扱いとなります。未設定時は起動時に例外が発生します。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  変更する場合は環境変数 DUCKDB_PATH / SQLITE_PATH を設定してください。
- 開発・本番の切り替えは KABUSYS_ENV 環境変数（development / paper_trading / live）で行います。無効値を指定すると例外になります。

もし特定のモジュールや機能ごとにより詳細なリリースノート（例: API 使用例や移行手順、既知のバグ・回避策）を希望される場合は、そのモジュール名を指定して依頼してください。