# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-19
初回リリース。モジュール化された日本株自動売買システムのコア機能を実装しました。主な追加点と設計上の要点は以下のとおりです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開サブモジュールの定義。

- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数保護（.env の上書きを制御）機構を実装。
    - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等を取得・検証するプロパティを提供。
    - デフォルト: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値を定義。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
    - レート制限制御（固定間隔スロットリングで 120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから id_token を再取得して 1 回リトライする仕組みを実装。
    - ページネーション対応（pagination_key を使ったループ取得）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。ON CONFLICT DO UPDATE による更新を行う。
    - 型変換ユーティリティ：_to_float / _to_int を提供（安全な変換と不正値スキップのポリシー）。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を取得して raw_news に保存する機能（デフォルトに Yahoo Finance の RSS を含む）。
    - 記事 ID は URL 正規化後の SHA-256 の一部を使用して冪等性を確保。
    - URL 正規化機能（トラッキングパラメータ除去、フラグメント除去、キーソートなど）。
    - XML パースに defusedxml を利用して XML-Bomb 等の攻撃を軽減。
    - SSRF 対策指針（HTTP/HTTPS のみ許可等）、最大受信バイト数制限（10MB）、バルク INSERT チャンク化などを実装。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー系ファクターを計算する関数を追加:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）等。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio 等（真のレンジ処理に注意）。
      - calc_value: per, roe を raw_financials と prices_daily を組み合わせて計算。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部 API に依存しない設計。

  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（デフォルト 1/5/21 営業日）を計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクにするランク付けユーティリティ。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

  - src/kabusys/research/__init__.py: 主要関数を再エクスポート。

- 戦略（特徴量生成・シグナル）
  - src/kabusys/strategy/feature_engineering.py:
    - research で計算した生ファクターをマージしてユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化には zscore_normalize を利用し、対象カラムを Z スコア化して ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（削除→一括挿入）することで冪等性と原子性を確保。

  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みは StrategyModel.md に基づく（momentum:0.4, value:0.2, volatility:0.15, liquidity:0.15, news:0.1）。与えられた weights は検証・補完・再スケールされる。
    - final_score の閾値デフォルトは 0.60。Bear レジーム（AI の regime_score が負の場合の市場平均判定）では BUY シグナルを抑制。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
      - （将来的にトレーリングストップや時間決済を追加予定）
    - signals テーブルへ日付単位で置換（冪等）。

- API エクスポート
  - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。

### Security
- news_collector: defusedxml による XML パース、防御的 URL 正規化、受信サイズ上限等を導入して外部入力に対する耐性を強化。
- jquants_client: API 認証トークン管理を導入し、401 時のトークンリフレッシュや再試行で認証失敗による情報漏洩リスクを低減。

### Internal / Design notes
- DuckDB を中心に設計し、analysis / research / strategy 層は原則として DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）のみを参照することでルックアヘッドバイアスを防止。
- 冪等性を重視: データ保存は ON CONFLICT / DELETE→INSERT の日付単位置換等で再実行可能な設計。
- 外部依存は最小限に抑え、研究環境と本番実行の分離を意識したモジュール分割。

### Fixed
- 初版リリースのため該当なし。

### Changed / Deprecated / Removed
- 初版リリースのため該当なし。

---

注:
- 各モジュールの詳細実装やアルゴリズム仕様（例: StrategyModel.md, DataPlatform.md 等）はソース内の docstring に記載された設計指針に従って実装されています。
- 今後のリリースではトレーリングストップ、時間決済、追加のリスク管理ルール、より高度なニュース紐付けロジックなどを追加予定です。