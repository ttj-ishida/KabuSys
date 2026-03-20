# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-20

初回リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` と公開モジュール一覧を追加（data / strategy / execution / monitoring を公開）。
- 設定管理
  - `src/kabusys/config.py`
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索、パッケージ配布後も動作）。
    - .env パースの堅牢化: コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントへ対応。
    - 環境変数上書き制御（override）と保護キー（protected）をサポート。自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - `Settings` クラスを提供し、J-Quants トークン・kabu API パスワード・Slack トークン・DB パスなどを型安全に取得。`KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（許容値チェック）。利便性プロパティ: `is_live` / `is_paper` / `is_dev`。
- データ取得・保存（J-Quants）
  - `src/kabusys/data/jquants_client.py`
    - J-Quants API クライアントを実装。ページネーション対応の取得関数（株価/財務/カレンダー）を提供。
    - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する `_RateLimiter` を導入。
    - リトライロジック（指数バックオフ、最大3回）および 408/429/5xx のリトライ対象化。429 の場合は Retry-After を尊重。
    - 401 (Unauthorized) 受信時の ID トークン自動リフレッシュ（1 回だけ）を実装。
    - DuckDB へ保存する関数（`save_daily_quotes` / `save_financial_statements` / `save_market_calendar`）を実装。挿入は冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - 取得データの変換ユーティリティ `_to_float` / `_to_int` を提供し、型変換の堅牢化を図る。
- ニュース収集
  - `src/kabusys/data/news_collector.py`
    - RSS フィードから記事を取得して `raw_news` へ冪等保存するための基礎実装。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）を実装し、記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成する設計。
    - defusedxml を用いた XML パース（XML Bomb 対策）、応答サイズ上限（10MB）設定、挿入のチャンク化とトランザクションによる原子保存など、安全性・性能に配慮した設計。
- 研究（research）モジュール
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value のファクター計算を実装（DuckDB SQL ウィンドウ関数を活用）。
    - 各関数は `prices_daily` / `raw_financials` テーブルのみを参照し、(date, code) 単位の dict リストを返す設計。
    - 計算範囲のバッファ設定（営業日換算）や欠損・データ不足時の None 処理を明示。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（LEAD を用いた複数ホライズン一括取得）を実装。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（同順位は平均ランク、丸めで ties を扱う）、およびファクター統計サマリーを提供。
  - `src/kabusys/research/__init__.py` で主要関数群をエクスポート。
- 戦略（strategy）モジュール
  - `src/kabusys/strategy/feature_engineering.py`
    - 研究側で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化（外部ユーティリティ zscore_normalize を使用）、±3 でクリップして外れ値影響を抑制。
    - `features` テーブルへ日付単位での置換（DELETE + bulk INSERT）を行い、処理はトランザクションで原子性を保証。
  - `src/kabusys/strategy/signal_generator.py`
    - 正規化済みの features と `ai_scores` を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みを定義し、ユーザー指定の weights は検証・正規化して合計が 1 になるようスケーリング。
    - AI の regime_score を集計して Bear レジーム判定（サンプル数閾値あり）。Bear の場合は BUY シグナルを抑制。
    - BUY シグナルは閾値（デフォルト 0.60）を超える銘柄を選出。SELL シグナルはストップロス（-8%）およびスコア低下に基づき判定。価格欠損時の判定スキップや features に存在しない保有銘柄の扱い（score=0 として SELL）など現実運用を意識した挙動。
    - 最終的に `signals` テーブルへ日付単位の置換で保存（トランザクション + bulk insert）。
  - `src/kabusys/strategy/__init__.py` で主要 API（build_features, generate_signals）を公開。
- その他
  - `src/kabusys/execution/__init__.py` はプレースホルダとして追加（将来の実行層統合のためのパッケージ準備）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Security
- ニュース収集で defusedxml を使用し、XML パーサ攻撃対策を行う設計。
- J-Quants クライアントでタイムアウト・リトライ制御・トークン自動更新を実装し、API エラーや認証切れに対する堅牢性を確保。
- .env パースでエスケープやクォートを適切に扱い、予期しない環境変数解釈ミスを防止。

### Notes / Design decisions
- DuckDB を中心とした設計で、research / data / strategy 間のデータ受け渡しはすべてテーブル（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions 等）経由で行うことでルックアヘッドバイアスを防止。
- 各種保存処理は冪等性（ON CONFLICT）およびトランザクション（DELETE + bulk INSERT）による「日付単位の置換」を採用し、再実行・再計算に対して安全に動作するように配慮。
- strategy 層は発注 API への直接依存を持たない（signals テーブルを通じて execution 層へ橋渡しする想定）。

---

今後の予定（例）
- execution 層の実装（kabu ステーション経由の実注文ロジック、補正・再試行の詳細実装）
- モニタリング・アラート機能の追加（Slack 通知等）
- ニュースと銘柄の紐付けロジック（news_symbols）の完成および全文検索 / NLP 前処理の高度化

もしCHANGELOGに追加して欲しい点（より詳細な項目分解や日付/コミットハッシュの付記など）があれば教えてください。