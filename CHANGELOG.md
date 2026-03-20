# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-20

初回リリース。本リリースでは日本株自動売買システム「KabuSys」の基礎となるモジュール群を実装しています。主な機能、公開 API、設計方針、既知の制限を以下にまとめます。

### Added
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - 公開モジュール一覧として `__all__ = ["data", "strategy", "execution", "monitoring"]` を設定。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート検出は `pyproject.toml` または `.git` を探索する実装で、CWD に依存しない。
  - .env パーサー (`_parse_env_line`) の実装:
    - コメント・空行の無視、`export KEY=val` 形式対応、クォート内のエスケープ処理、行内コメントの扱いなどを考慮。
  - 環境変数取得ユーティリティ `_require` を提供（未設定時は ValueError）。
  - Settings クラスを公開 (`settings`)。取得可能な設定（例）:
    - J-Quants / kabu API / Slack トークン、チャネルID
    - DB パス（duckdb / sqlite の既定値）
    - 実行環境 `KABUSYS_ENV`（development/paper_trading/live の検証）
    - ログレベル `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API ベースURL として `_BASE_URL = "https://api.jquants.com/v1"` を使用。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回）、対象ステータスコードの判定（408/429/5xx）。
    - 401 レスポンス時にリフレッシュトークンで自動的にトークンを更新して再試行する処理（1 回のみ）。
    - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間でトークンを共有。
    - HTTP ユーティリティ `_request`、認証関数 `get_id_token` を提供。
    - データ取得関数:
      - fetch_daily_quotes（株価日足、ページネーション対応）
      - fetch_financial_statements（財務データ、ページネーション対応）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 型安全かつ堅牢なパースユーティリティ `_to_float` / `_to_int` を実装。

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードからニュース取得し raw_news に保存する処理。
    - デフォルト RSS ソースを定義（Yahoo Finance のビジネス RSS）。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート）。
    - 受信サイズ上限（10 MB）や XML パースにおける defusedxml 利用などセキュリティ対策を実装。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）を用いる旨の設計。
    - バルク INSERT のチャンク化、ON CONFLICT DO NOTHING による冪等性確保。

- Research 層（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
      - 200 日移動平均のカウントチェックによりデータ不足を扱う。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
      - true_range の NULL 伝播制御、ATR/取引代金等のウィンドウ集計を実装。
    - Value（per, roe）
      - raw_financials の target_date 以前の最新データを銘柄毎に取得して計算。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) を持つ dict リストを返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算(calc_forward_returns): 複数ホライズン（デフォルト: 1,5,21 営業日）対応、範囲制限チェック。
    - IC（Information Coefficient）計算(calc_ic): スピアマンのランク相関（tie を平均ランクで処理）を実装。サンプル不足時は None を返す。
    - 統計サマリー(factor_summary): count/mean/std/min/max/median を計算。
    - ランク処理ユーティリティ rank を実装（浮動小数点丸めで ties 検出漏れを防止）。
  - research モジュールの公開 API を __all__ で整理。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究環境で計算された raw factors を結合、ユニバースフィルタ（株価>=300円、20日平均売買代金>=5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等・原子性を保証）。
    - 公開関数: build_features(conn, target_date) -> upsert した銘柄数を返す。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して最終スコア（final_score）を算出、BUY/SELL シグナルを生成。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）
      - 各コンポーネントの計算ロジックを実装（例: PER→value の変換、atr_pct を反転して volatility スコア化、シグモイド変換等）。
      - None のコンポーネントは中立値 0.5 で補完。
    - 標準重み（デフォルト）と閾値:
      - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10
      - デフォルト BUY 閾値: 0.60
      - ストップロス閾値: -8%（_STOP_LOSS_RATE）
    - Bear レジーム判定: ai_scores の regime_score の平均が負 -> Bear（十分なサンプル数がある場合のみ）
    - BUY は Bear 時に抑制、SELL は保有ポジションに対してストップロス・スコア低下で生成。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 公開関数: generate_signals(conn, target_date, threshold=..., weights=None) -> 生成したシグナル数。

- パッケージのエクスポート
  - kabusys.strategy に build_features / generate_signals を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known issues / Limitations
- signal_generator 内で言及されているいくつかのエグジット条件は未実装（実装には positions テーブルに peak_price / entry_date 等の追加データが必要）。
  - 未実装例: トレーリングストップ（直近最高値から -10%）、時間決済（保有 60 営業日超過）。
- news_collector の実装は RSS パース・正規化設計を含むが、外部ネットワークの制約やフィードの多様性に対する追加の検証が必要。
- DuckDB のスキーマ（テーブル定義）が本 changelog に含まれていないため、実運用前にスキーマの準備が必要。
- J-Quants API の rate limit / リトライは実装されているが、実運用での負荷試験・監視・メトリクスが推奨される。

### Notes / Implementation details
- ルックアヘッドバイアス対策を各所で考慮（target_date 時点のデータのみを使用、fetched_at を UTC で保存など）。
- 各所で冪等性を重視した実装（ON CONFLICT / DELETE+INSERT の日付単位置換）を採用。
- 外部依存を最小化する方針が一貫（research モジュールは標準ライブラリ + DuckDB のみで実装する意図）。
- 設定周りでは OS 環境変数保護（.env 上書きの protected set）や入力値検証（KABUSYS_ENV, LOG_LEVEL の検証）が行われる。

---

今後のリリースで検討すべき項目:
- positions テーブルの拡張とトレーリングストップ等のエグジットルール実装
- news_collector のフィード追加・NLP 前処理・銘柄アノテーションの自動化
- 単体テスト・統合テスト、CI 環境の整備
- 運用監視（API レート監視、失敗率アラート、処理遅延の計測）
- ドキュメント（API 仕様、DB スキーマ、運用手順）の拡充

（必要であれば、各モジュールの公開関数一覧や例を追記します。）