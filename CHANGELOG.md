# Changelog

すべての重要な変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の慣例に従って構成されています。  

なお、以下の変更履歴は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]
### Added
- 実行層（execution）および監視（monitoring）パッケージのプレースホルダを導入（今後の実装を想定）。
- ドキュメント・設計方針の注記を各モジュールに追記（ルックアヘッドバイアス回避、冪等性、トランザクション扱い等の設計原則）。

### Changed
- —（現時点では未リリースのため変更点はなし）

### Known issues / TODO
- ポジション管理（positions）に対するトレーリングストップや時間決済の条件は未実装（feature コメントで言及）。
- positions テーブルに peak_price / entry_date 等が必要な機能が残存（将来実装予定）。

---

## [0.1.0] - 2026-03-20
初回リリース。主要コンポーネントと研究／データ処理・シグナル生成のコア機能を実装。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開 API の __all__ を定義）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の柔軟なパース（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - Settings クラスで必須環境変数をラップ（J-Quants / kabu ステーション / Slack / DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL の検証ロジックと利便性系プロパティ（is_live / is_paper / is_dev）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 を検出した場合は ID トークンを自動リフレッシュして1回だけ再試行。
    - ページネーション対応（pagination_key の連結取得）。
    - fetch_* 系関数: 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - fetched_at を UTC ISO 形式で記録（Look-ahead Bias のトレース目的）。
    - ON CONFLICT DO UPDATE による冪等な保存。
    - PK 欠損行のスキップとログ出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news へ保存するロジック（デフォルトに Yahoo Finance の RSS を定義）。
  - セキュリティ考慮: defusedxml を使用、受信サイズ上限（10 MB）、HTTP スキームチェック、SSRF 緩和のためのホスト処理等の設計方針を反映。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホストの小文字化、フラグメント削除）。
  - 記事 ID の生成方針（正規化後の URL の SHA-256 ハッシュ先頭 32 文字）を確立。
  - DB 挿入は ON CONFLICT DO NOTHING、バルク挿入のチャンク処理による効率化。

- 研究モジュール (kabusys.research)
  - factor_research: Momentum / Value / Volatility / Liquidity ファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率（200 行未満は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - calc_value: raw_financials と prices を組み合わせて PER / ROE を算出。
    - DuckDB を用いた SQL+Python 実装。外部依存を排除。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターン計算。
    - calc_ic: スピアマンのランク相関（IC）計算。3 サンプル未満は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
    - rank: 平均ランク処理（同順位は平均ランク）。

  - 研究用ユーティリティ（zscore_normalize を kabusys.data.stats から再公開）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research の生ファクターを統合して features テーブルへ書き込むワークフローを実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を導入。
    - Z スコア正規化（指定カラム）、±3 でクリップ。
    - 日付単位で既存行を削除してから挿入するトランザクション化による置換（冪等性、ROLLBACK 処理）。
    - DuckDB の prices_daily, raw_financials を参照。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して BUY/SELL シグナルを生成。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算ロジックを実装（シグモイド変換、欠損は中立 0.5）。
    - デフォルト重みを提供し、ユーザ指定重みは検証（未知キー・非数値・負値はスキップ）、合計が 1.0 に正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ必要サンプル数以上の場合は BUY 抑制）。
    - BUY は閾値超過銘柄、SELL はストップロス（-8%）およびスコア低下で判定。SELL は BUY より優先。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。
    - ログ出力（INFO/DEBUG/警告）を適切に実施。

- 共通ユーティリティ
  - 数値パースユーティリティ（_to_float, _to_int）を実装し、変換失敗時は None を返す安全な処理。
  - zscore_normalize 等の統計ユーティリティをデータ層で提供（モジュール参照用に再エクスポート）。

### Security
- XML 処理に defusedxml を利用し、XML ベースの攻撃に対する耐性を確保。
- HTTP リトライ時の Retry-After を尊重、429/5xx に対する指数バックオフを実装。

### Performance / Robustness
- DuckDB に対するバルク挿入＋トランザクション処理で原子性と性能を向上。
- レートリミッタで API 呼び出しをスロットリングし、レート制限違反を防止。
- 各種取得関数でページネーションを安全に処理（pagination_key のループ検出）。

### Documentation / Comments
- 各モジュールに設計方針・処理フロー・注意点を詳細にコメント記載（Look-ahead bias、冪等性、未実装項目の注記など）。

### Removed / Deprecated
- —（初版のため該当なし）

---

注記:
- 一部仕様はモジュール内コメント／TODO により将来の拡張を想定（例: トレーリングストップ、時間決済、positions テーブルの拡張、execution/monitoring 実装）。
- 実際の挙動や DB スキーマ・外部 API の挙動に依存する部分があるため、本 CHANGELOG はコードからの推測に基づきます。実環境での挙動確認・追加調整を推奨します。