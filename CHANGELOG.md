# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、リポジトリ内のソースコードから推測できる実装内容・設計意図に基づき作成しています。

全般:
- セマンティックバージョニングに従います。現在のパッケージバージョンは 0.1.0（src/kabusys/__init__.py）。
- 初期リリース相当の機能群（データ収集/保存、ファクター計算、特徴量生成、シグナル生成、設定管理、ニュース収集）を実装しています。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース:
  - 基本パッケージ構成を追加（kabusys モジュール、サブパッケージ: data, strategy, execution, monitoring を __all__ に公開）。
  - バージョン情報: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサを独自実装（コメント・export プレフィックス・クォートやエスケープ処理を考慮）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）などのプロパティを取得可能に。
  - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を実装。

- データ収集・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（認証、ページネーション、データ取得）。
  - レート制限（120 req/min）の固定間隔スロットリングを実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を再取得して 1 回のみリトライする仕組みを実装。
  - id_token のモジュールレベル・キャッシュを導入しページネーション中のトークン共有を可能に。
  - DuckDB への冪等保存ユーティリティを提供:
    - save_daily_quotes: raw_prices テーブルへの保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへの保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar テーブルへの保存（ON CONFLICT DO UPDATE）。
  - 入力値変換ヘルパー (_to_float / _to_int) を実装し、型安全に値を整形。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news に保存するための基盤を実装。
  - URL 正規化ロジック（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - セキュリティ設計: defusedxml を用いて XML 爆弾等を防御、受信サイズ上限を設定、SSRF 対策（HTTP/HTTPS 検証想定）やトラッキングパラメータ除去などが設計に明記。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を設定（DEFAULT_RSS_SOURCES）。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）などを計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高変化率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。
    - DuckDB を用いた SQL ベースの実装で、営業日（連続レコード）ベースのウィンドウ処理を考慮。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを計算。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク相関）による IC 計算を実装（有効レコード < 3 の場合は None を返す）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクを割り当てるランク関数を実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research のファクターを集約し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize に依存）を実行し ±3 でクリップして外れ値影響を抑制。
  - features テーブルへの日付単位での置換（DELETE + INSERT をトランザクションで実行）により冪等性を確保。
  - ユニバース条件: 最低株価 300 円、20日平均売買代金 5 億円。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
  - コンポーネントはシグモイド変換・平均化等で正規化し、重み付き合算で final_score を算出（デフォルト閾値 BUY=0.60）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負で、サンプル数閾値を満たす場合）により BUY シグナルを抑制。
  - SELL（エグジット）判定を実装（ストップロス: -8% / final_score が閾値未満）。ポジションの価格欠損時は判定スキップ。
  - signals テーブルへの日付単位置換をトランザクションで実行し冪等性を確保。
  - 重み（weights）引数の妥当性検査と合成（デフォルト値にフォールバック、再スケール）を実装。

- パッケージ public API（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - 主要関数を __all__ によりエクスポートし外部から利用可能に。

### Security
- news_collector で defusedxml を採用して XML に関する脆弱性（XML bomb など）を軽減。
- news_collector はトラッキングパラメータ除去や受信サイズ制限を設計に明記。
- jquants_client は認証エラーに対して自動トークンリフレッシュを行い、不正アクセス時の挙動を明示。
- ネットワークエラーや HTTP エラーに対する適切なリトライ/バックオフを実装し、DoS・レート超過の影響を緩和。

### Known issues / TODO (コード中に明記されている未実装項目や改善点)
- シグナル生成のエグジット条件で、トレーリングストップ（peak_price ベース）や時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の実装はいくつかの処理について（記事ID生成や DB 挿入の詳細など）設計書に沿っているが、RSS パース周りの完全な処理や外部依存（例: defusedxml の利用方法）は追加テスト/レビューを推奨。
- 一部モジュールは外部モジュール（kabusys.data.stats など）へ依存。テスト用のモックやインタフェースの安定化が望まれる。
- 実運用向けの例外ハンドリング・監視（モニタリング）および execution（発注）層はパッケージ内にプレースホルダがあり、発注 API 連携・トランザクション管理の実装は別途必要。

### Notes / Implementation highlights
- DuckDB を用いた分析パイプライン（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions 等）を前提とした設計。
- ルックアヘッドバイアス回避の設計方針が各所に反映（target_date 時点のデータのみ参照、fetched_at に UTC タイムスタンプを保持など）。
- 冪等性を重視した DB 操作（ON CONFLICT / トランザクション + DELETE→INSERT）を採用。

---

今後のリリースでは以下を予定しています（コード内コメント・設計ノートに基づく推測）:
- execution 層（kabu ステーション等）との安全な連携・発注ロジックの実装。
- モニタリング（Slack 通知など）と運用監視の強化。
- 単体テスト・統合テストの追加と CI パイプライン整備。
- ニュースの銘柄紐付け（news_symbols）や NLP による ai_scores 生成パイプラインの追加。

（注）本 CHANGELOG はソースの実装内容から推測して作成しています。実際の変更履歴・コミット履歴が存在する場合はそちらに基づく正式な履歴（CHANGELOG）を別途作成することを推奨します。