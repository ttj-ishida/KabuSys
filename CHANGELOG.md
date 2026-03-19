# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現在の内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

（現状なし）

## [0.1.0] - 初期リリース
リリース日: 2026-03-19（推定）

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン: 0.1.0）。
  - モジュール公開 API を定義（strategy, execution, data, monitoring 等を __all__ に登録）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - テスト等のために自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - .env のパース機能を強化（export 付形式、クォート内エスケープ、インラインコメントの取り扱いをサポート）。
  - 設定クラス Settings を提供し以下のキーをプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等
  - 環境値のバリデーション（KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準ログレベルのみ）。

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッター（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）と 401 発生時のトークン自動リフレッシュ対応。
    - ページネーション対応のフェッチ関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - データ変換ユーティリティ（_to_float / _to_int）を実装し、不正値を安全に扱う。
  - ID トークンのモジュールレベルキャッシュを導入し、ページネーション間で再利用。

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得 → 前処理 → raw_news への冪等保存までの基盤を実装。
  - 記事IDは URL 正規化後の SHA-256 ハッシュ等で冪等性を確保する方針を記載（実装の前提）。
  - defusedxml を利用した XML パースで XML Bomb 等の攻撃を低減。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）やトラッキングパラメータ除去などの前処理を実装。
  - HTTP/HTTPS スキーム検査など SSRF 対策方針を明記。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）を実装。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、本番 API には依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - 外部依存を持たず標準ライブラリ＋DuckDB で動作する設計。
  - research パッケージのトップレベルエクスポートを整理。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research モジュールから生ファクターを取り込み、ユニバースフィルタを適用、Zスコア正規化、±3 でクリップし features テーブルへ UPSERT（日付単位の置換）する build_features を実装。
    - ユニバースフィルタ条件は最低株価（300 円）と 20 日平均売買代金（5 億円）。
    - DuckDB トランザクションを使用して原子性を保証。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して最終スコア（final_score）を計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - モジュール内でスコア計算（モメンタム/バリュー/ボラティリティ/流動性/ニュース）やシグモイド変換、欠損値の中立補完ロジックを実装。
    - Bear レジーム判定（AI レジームスコアの平均が負の場合）で BUY を抑制する処理を実装。
    - 保有ポジションに対するエグジット判定（ストップロス -8%、スコア低下）を実装（_generate_sell_signals）。トレーリングストップや時間決済は未実装で注記あり。
    - signals テーブルへ日付単位の置換（トランザクション）を実施。

- 汎用ユーティリティ
  - zscore_normalize 等のデータ正規化ユーティリティを data.stats として想定し参照（トップレベルや research からエクスポート）。

- ロギングとエラーハンドリング
  - 各主要処理で詳細ログ（info/debug/warning）を出力するよう実装。
  - DB 操作時の Rollback 失敗に関する警告ログを追加して堅牢性を向上。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS XML を defusedxml で安全にパース。
- ニュース収集での外部 URL 正規化・トラッキングパラメータ削除・スキームチェック等により SSRF や情報漏洩のリスク低減を想定。
- J-Quants クライアントはトークン自動リフレッシュを実装し、認証エラー時の安全な再試行を実現。

### Known Issues / TODO
- signal_generator のエグジット条件におけるトレーリングストップおよび時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の記事→銘柄紐付け（news_symbols）の詳細ロジックは本コードでは未表示／未実装。
- 一部の入力欠損（価格欠損・財務データ欠損等）に対する扱いは保守的（スキップ、None、警告ログ）としているが、運用ポリシーにより調整が必要。
- DuckDB のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news など）を事前に準備する必要あり。スキーマ定義は本コードでは省略。

### Migration notes
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD は必須プロパティとして Settings により取得される。未設定時は起動時に ValueError が発生します。
- 環境の自動読み込みを無効化したいテスト環境等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで指定する必要があります。
- デフォルトデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  必要に応じて環境変数で上書きしてください。
- DuckDB 側のテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar, raw_news 等）が想定するカラムを満たしていることを確認してください（INSERT ... ON CONFLICT 等を利用）。

---

作者（推定）による注釈:
- 本 CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実際のリリースノートはプロジェクトのリリース方針・履歴に基づいて適宜調整してください。必要があれば、各モジュールごとの詳細なスキーマや外部依存（ライブラリバージョン等）情報も追記できます。