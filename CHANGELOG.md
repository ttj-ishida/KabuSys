# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、コードベースから推測できる機能追加・設計上の決定・既知の制約等をまとめた初版リリースノートです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装。

### Added
- パッケージ基本設定
  - パッケージ初期化（src/kabusys/__init__.py）とバージョン定義 (__version__ = "0.1.0") を追加。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env の行パースロジック（コメント・export プレフィックス・クォート・エスケープ対応）。
  - 環境変数読み込みの保護機構（OS 環境変数は protected として上書き防止）。
  - 自動読み込み無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスを導入し、J-Quants / kabuAPI / Slack / DB パス / システム環境（env, log_level）等のプロパティ化と入力検証を実装。

- データ収集クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レートリミット制御（120 req/min 固定間隔スロットリング）。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx などをリトライ対象）。
  - 401 受信時の ID トークン自動リフレッシュ（1 回のみリトライ）。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等的に保存する関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による更新）
  - データ変換ユーティリティ (_to_float, _to_int) を実装。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集処理骨格を実装（デフォルトソースに Yahoo Finance を指定）。
  - 安全性対策: defusedxml を用いた XML パース、受信サイズ上限（10MB）、URL のホワイトリスト的検査を想定。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を維持。
  - バルク INSERT のためのチャンク処理、ON CONFLICT DO NOTHING による冪等保存想定。
  - news と銘柄の紐付け（news_symbols）を想定した設計。

- リサーチ（研究）モジュール（src/kabusys/research/ 以下）
  - factor_research:
    - calc_momentum（1m,3m,6m リターン、200 日 MA 乖離）
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - calc_value（PER, ROE：raw_financials と prices_daily を組み合わせ）
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、結果を (date, code) キーの dict リストで返す。
  - feature_exploration:
    - calc_forward_returns（指定ホライズンの将来リターン集計、複数ホライズン対応）
    - calc_ic（Spearman のランク相関 / IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理）
  - 研究モジュールは pandas 等の外部依存を使わず Python 標準 + DuckDB で実装。

- 戦略（strategy）モジュール（src/kabusys/strategy/ 以下）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で算出した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターの Z スコア正規化（_NORM_COLS）と ±3 クリップ。
    - features テーブルへ日付単位での置換（DELETE → INSERT）の冪等処理を実装。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み・閾値（default weights、BUY threshold=0.60）を実装。ユーザ指定の weights を検証・正規化して合計 1.0 にスケール。
    - AI スコアはシグモイドで 0-1 に変換、未登録は中立 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY シグナル生成、SELL（エグジット）判定（ストップロス -8% / final_score が閾値未満）。
    - 保有ポジションに対する SELL 判定は優先し、signals テーブルへ日付単位の置換で保存（冪等）。
    - 生成されるシグナル数を返す API（generate_signals）。

- モジュール間の公開 API を __all__ 等で整理（research/__init__.py, strategy/__init__.py）。

### Changed
- （初回公開のため「変更」履歴はなし）

### Fixed
- （初回公開のため「修正」履歴はなし）

### Removed
- （初回公開のため「削除」履歴はなし）

### Security
- ニュースパーシング部分で defusedxml を採用（XML 攻撃対策の設計）。
- ニュース収集で SSRF を抑止するために HTTP/HTTPS スキームの想定と URL 正規化を実施。

### Notes / Known limitations / TODO
- signal_generator のエグジット条件では、トレーリングストップや時間決済（保有 60 営業日超）などの一部仕様はまだ未実装。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- value ファクターについて PBR・配当利回りは現バージョンで未実装。
- news_collector の RSS フィード取得本体（HTTP 取得・XML パース→DB 保存の完全な実装）は骨格があるが、外部環境依存（ネットワーク・RSS ソース管理）のため追加の統合テストが必要。
- DB スキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news, news_symbols 等）は実行前に適切に作成しておく必要がある（スキーマ定義はこのリリースに含まれていない想定）。
- .env パーサは多くのケースに対応しているが、極端なパースケースや非 UTF-8 ファイルに対する挙動は限定的（読み込み失敗時に警告を出す設計）。
- J-Quants クライアントはネットワーク例外・HTTP エラーに対するリトライを行うが、実運用では API レートやトークン管理の追加監視が推奨される。

---

この CHANGELOG はコード内の docstring・実装・定数・設計コメントから推測して作成しています。実際のリリースノートとして公開する際は、テスト結果・マイグレーション手順・DB スキーマ定義・API 使用法（環境変数の設定例）を補完してください。