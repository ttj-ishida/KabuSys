# Changelog

すべての重要な変更履歴をこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従っています。
継続的に更新してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。パッケージバージョンを `0.1.0` として公開。
  - パッケージの公開 API を定義（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を想定）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準として行う（__file__ を起点に探索）。
  - .env パーサーの実装（コメント行・export プレフィックス・クォート処理・インラインコメント処理に対応）。
  - .env.local を .env の上から上書きする挙動（既存 OS 環境変数は保護）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用途）。
  - Settings クラスを実装（プロパティ経由で必須トークンやパス等を取得）。
  - 設定値の検証を実施（KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準のログレベルのみ許可）。

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大試行回数、特定ステータスでのリトライ）を実装。
    - 401 受信時はリフレッシュトークンを使ってトークン自動更新を行い 1 回再試行。
    - ページネーション対応の fetch 関数（daily_quotes / financial_statements / market_calendar）。
  - DuckDB への保存ユーティリティを実装（raw_prices / raw_financials / market_calendar）。
    - 冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC で記録し、いつデータを取得したかを追跡可能に。
    - 入力値の型変換ユーティリティ（_to_float / _to_int）を提供。
    - PK 欠損行はスキップし、スキップ件数をログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得する収集モジュールを追加（デフォルトで Yahoo Finance の Business フィードを用意）。
  - セキュリティを考慮した実装:
    - defusedxml を用いて XML 攻撃（XML Bomb 等）に対応。
    - 受信バイト数上限（MAX_RESPONSE_BYTES）を設定してメモリ DoS を軽減。
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）等で冪等性を担保する設計（ドキュメント化）。
  - DB 保存はバルク挿入とトランザクションで実施、INSERT RETURNING を想定した運用設計（実装設計を明記）。

- 研究（research）モジュール
  - factor_research: prices_daily / raw_financials を使ったファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算。
    - calc_value: 最新の財務データ（eps/roe）と株価から PER / ROE を計算。
    - 各関数はデータ不足時に None を適切に返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算を実装。サンプル不足時に None。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク付け実装（丸めを入れて ties の検出を安定化）。

- 戦略（strategy）モジュール
  - feature_engineering.build_features:
    - research で計算した生ファクターを統合・正規化し、features テーブルへ日付単位で置換（冪等）する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - 正規化は z-score 正規化を利用し ±3 でクリップ（外れ値抑制）。
    - トランザクション + バルク挿入で原子性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - momentum/value/volatility/liquidity/news のコンポーネントスコア算出ロジックを実装（デフォルト重みも定義）。
    - 不足コンポーネント値は中立値（0.5）で補完して不当な降格を回避。
    - AI レジームスコアの平均で Bear を判定し、Bear 時は BUY シグナルを抑制する処理を実装。
    - SELL（エグジット）判定を実装（ストップロス -8% または final_score が閾値未満）。
    - weights の検証・補完・再スケーリングロジックを実装（不正なキーや NaN/負値を無視）。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。

- DB 操作と堅牢性
  - 重要な書き込み処理は明示的に BEGIN/COMMIT/ROLLBACK を用いてトランザクション管理。
  - 例外時の ROLLBACK 失敗はログ警告で記録し、例外は上位へ伝播。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- defusedxml を用いた RSS パースや受信サイズ制限、URL 正規化により外部データ取り込み時の安全性を考慮。
- API クライアント側でトークン自動リフレッシュとリトライ制御（過負荷時の待機・Retry-After 尊重）を実装し、堅牢な HTTP エラー処理を提供。

---

注:
- 本 CHANGELOG はコード内のドキュメント（docstring）や実装から推測して作成しています。実際のユーザー向けリリースノートでは、変更点の粒度や影響範囲に応じて調整してください。