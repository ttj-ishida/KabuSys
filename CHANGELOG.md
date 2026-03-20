# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
このファイルは、コードベースから実装内容を推測して作成した初回リリースの変更履歴です。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - 公開サブパッケージを __all__ で指定（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に __file__ を起点に探索（配布後の動作を安定化）。
    - 柔軟な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - .env の読み込み優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能）。
    - Settings クラスにて必須環境変数チェックと型変換を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - env / log_level の許容値検証とユーティリティプロパティ（is_live / is_paper / is_dev）。
- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（株価・財務・マーケットカレンダー取得）。
    - レートリミット制御: 固定間隔スロットリングで 120 req/min を順守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回。対象ステータスコード（408, 429, 5xx）に対応。
    - 401 発生時は自動でリフレッシュトークンから id_token を取得して 1 回再試行。
    - ページネーション対応とモジュールレベルのトークンキャッシュ（ページ間で共有）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT による冪等なアップサート処理。
    - CSV/JSON 等の不正値対策ユーティリティ (_to_float / _to_int) を実装。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集して raw_news に保存する機能。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト正規化、フラグメント削除、クエリキーソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - セキュリティ対策: defusedxml を用いた XML パース、HTTP/HTTPS スキームのみ許可、受信サイズ上限（MAX_RESPONSE_BYTES）など。
    - バルク INSERT とチャンク処理で DB への負荷を抑制。挿入件数を正確に返す方針（INSERT RETURNING 想定）。
    - デフォルト RSS ソースを提供（Yahoo Finance のカテゴリ RSS）。
- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - ボラティリティ calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - バリュー calc_value: raw_financials から最新財務を参照して PER / ROE を計算（EPS が 0 の場合は None）。
    - DuckDB を用いた SQL ベースの効率的な実装（スキャン範囲のバッファ等によるパフォーマンス配慮）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来終値リターンを計算（営業日ベース）。
    - IC（Information Coefficient） calc_ic: スピアマンランク相関を計算するユーティリティを提供（ties の平均ランク処理を含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー関数を実装。
    - rank: 同順位は平均ランクを返すランク関数を実装（浮動小数の丸めで ties 検出を安定化）。
  - research パッケージの __init__ で主要関数を再エクスポート。
- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py
    - build_features 実装:
      - research モジュールから生ファクターを取得しマージ。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
      - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性保証）。
      - ルックアヘッドバイアス対策の設計方針を明記。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals 実装:
      - features, ai_scores, positions を参照して銘柄ごとの最終スコア（final_score）を計算。
      - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重みを定義）。
      - 重みの入力検証と合計スケーリング、無効値の警告ログ。
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
      - Bear レジーム検出（ai_scores の regime_score 平均が負でかつサンプル数閾値以上で判定）による BUY 抑制。
      - BUY 閾値はデフォルト 0.60。SELL（エグジット）条件にストップロス（-8%）とスコア低下を実装。
      - signals テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性保証）。
    - SELL が BUY より優先されるポリシーを実装（SELL の銘柄を BUY から除外してランク再付与）。
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集モジュールで defusedxml を利用して XML 関連の脆弱性（XML Bomb など）に対処。
- ニュース URL 正規化でトラッキングパラメータ除去およびスキーム検証により SSRF /トラッキング問題を軽減。
- J-Quants クライアントのリクエストでタイムアウトやリトライ処理を実装し、ネットワーク障害時の安全性と可用性を向上。

---

注意:
- 本 CHANGELOG はリポジトリのソースコードから実装意図・機能を推測して作成しています。実際のリリースノートとして使用する場合は、リポジトリのコミット履歴やリリース時の変更点に合わせて更新してください。