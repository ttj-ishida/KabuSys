# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
フォーマット: Unreleased / 各バージョン（年月日） → セクション (Added, Changed, Fixed, Security, Breaking Changes など)

## [Unreleased]

- ドキュメント・テスト用に環境変数自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD の挙動をそのまま利用可能（設定変更なし）。
- 将来的な改善案・未実装箇所の注記（トレーリングストップ・時間決済など）を signal_generator / _generate_sell_signals にコメントで明記。

---

## [0.1.0] - 2026-03-20

初回公開リリース（ベース実装）。以下の機能セットを含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン定義を追加（__version__ = "0.1.0"）。
  - 公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env の行パーサを実装（コメント行、export プレフィックス、クォート・エスケープ、インラインコメント処理対応）。
  - .env / .env.local の優先順位で読み込み（OS 環境変数を保護する protected 機能）。
  - 必須環境変数検査ユーティリティ _require と Settings クラスを提供。
  - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。その他 DB パスやログレベル等の設定をサポート。
  - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の検証ロジックを実装（許容値チェック）。

- データ取得 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダー取得）。
  - レート制限を守る固定間隔スロットリング RateLimiter を実装（120 req/min）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大3回、408/429/5xx 対象）。
  - 401 応答時にリフレッシュトークンから id_token を自動更新して 1 回リトライ。
  - ページネーション対応（pagination_key を利用したループ取得）。
  - DuckDB への冪等保存関数を実装（raw_prices, raw_financials, market_calendar への INSERT ... ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ _to_float / _to_int を実装（堅牢な変換・空値処理）。
  - fetched_at を UTC ISO8601 で記録し、データ取得時刻のトレースを可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する仕組みを実装（デフォルトソースに Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - 外部入力に対するセキュリティ対策を実装（defusedxml を使用した XML パース、受信サイズ制限、SSR F 関連チェックの準備）。
  - バルク INSERT チャンク化による DB 書き込みの最適化。

- 研究（Research）機能 (kabusys.research, research.*)
  - ファクター計算モジュール（factor_research）を実装：
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）。
    - バリュー: per, roe（raw_financials と prices_daily を組み合わせて算出）。
    - DuckDB 上で SQL とウィンドウ関数を利用して効率的に算出。
  - 特徴量探索モジュール（feature_exploration）を実装：
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）。
    - IC（Information Coefficient）計算（スピアマンのρ をランク変換で算出）。
    - factor_summary（count/mean/std/min/max/median の統計サマリー）や rank ユーティリティを実装。
  - 研究用 API を __all__ に公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で計算した生ファクターを統合し、features テーブルへ保存する処理 build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指標の Z スコア正規化および ±3 でクリップする処理（外れ値耐性）。
  - 日付単位で features テーブルを置換（DELETE → INSERT のトランザクションで原子性確保）。
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみ参照。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - 各コンポーネントスコア（momentum, value, volatility, liquidity, news）の算出ロジックを実装（シグモイド変換・補完ロジック）。
  - デフォルト重み・閾値を実装し、ユーザー指定 weights のバリデーションとリスケールを実装。
  - Bear レジーム判定（ai_scores の regime_score の平均が負 → BUY 抑制）を実装。
  - エグジット判定（ストップロス -8%、スコア低下）を実装し、SELL シグナルを優先。
  - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
  - 欠損データへの堅牢性（欠損コンポーネントは中立値 0.5、price 欠損時の SELL 判定スキップ）を考慮。

- その他
  - strategy パッケージで build_features / generate_signals をトップレベルに再エクスポート。
  - DuckDB を想定した設計（複数モジュールが DuckDB 接続を引数に取る）。

### Changed
- n/a（初回リリースのため変更履歴はなし）

### Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

### Security
- news_collector で defusedxml を使用して XML パースの安全化を実施。
- ニュース収集時に受信バイト数上限（10 MB）を設定し、メモリ DoS を軽減。
- RSS URL 正規化でトラッキングパラメータを除去。HTTP(S) スキーム以外の URL を拒否する設計方針（実装箇所に注記）。
- J-Quants クライアントで認証トークンの取り扱いに注意（キャッシュ・自動リフレッシュを実装）。

### Breaking Changes
- なし（初回リリース）

---

## マイグレーション / アップグレードノート
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN 等）を .env もしくは OS 環境に設定してください。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）が前提となっています。既存 DB を利用する場合は対応するテーブルを準備してください。
- news_collector の URL 正規化・ID 生成仕様により、既存の raw_news の重複判定が変わる可能性があります。重要記事の扱いに注意してください。

---

## 既知の未実装 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が揃い次第実装予定。
- news_collector の SSRF 対策（IP/ホスト制限など）は設計に言及あり。追加のネットワーク制御は今後の改善要件。
- execution / monitoring パッケージは骨組みのみ（execution/__init__.py が空）。実際の注文実行・監視ロジックは別途実装予定。

---

本 CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要に応じて修正・追記してください。