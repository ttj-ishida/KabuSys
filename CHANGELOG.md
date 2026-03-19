# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠しています。  
すべての重要な変更点をバージョンごとに記録します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として初期化。
  - 公開モジュール群（data, strategy, execution, monitoring）をパッケージの __all__ に定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD に依存しない挙動）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env パーサを実装（`_parse_env_line`）。
    - コメント/空行処理、`export KEY=VAL` 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの取り扱いを考慮。
  - .env 読み込みの上書き制御（`override`）および OS 環境変数保護（`protected`）を実装。
  - Settings クラスを提供し、環境変数からアプリ設定を取得するプロパティを実装：
    - J-Quants / kabuステーション / Slack / DB パスなどに対応（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - env（KABUSYS_ENV）と log_level（LOG_LEVEL）の検証（許容値の制約）。
    - Path 型での `duckdb_path` / `sqlite_path` を返すユーティリティ。

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（認証・ページネーション・保存まで）。
    - 固定間隔のレートリミッタ（120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、対象ステータス: 408/429/5xx）。
    - 401 受信時はトークン自動リフレッシュ（1 回）して再試行。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
    - データ型変換ユーティリティ `_to_float` / `_to_int`（安全な変換と空値処理）。
    - fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアスのトレースを容易に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース収集し raw_news に保存する基盤を実装。
    - デフォルト RSS ソース（Yahoo Finance）を定義。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）で記事 ID を生成（後で SHA-256 による冪等 ID 化を想定）。
    - セキュリティ対策を組み込み:
      - defusedxml による XML パーシング（XML Bomb 対策）
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
      - トラッキングパラメータ除去
      - SSRF を念頭に置いたスキーム検証等（コメントに明記）
    - バルク INSERT のチャンク処理で SQL 長やパラメータ上限を回避。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
    - ボラティリティ: 20日 ATR / atr_pct / avg_turnover / volume_ratio
    - バリュー: per / roe（raw_financials の最新財務データを参照）
    - DuckDB SQL を活用した効率的なウィンドウ集計、データ不足時の None 処理。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足（<3件）や ties に対処。
    - rank: 同順位を平均ランクにするランク付けユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した raw factor を読み込み、ユニバースフィルタ・正規化・クリップを行い features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ:
      - 株価 >= 300 円
      - 20日平均売買代金 >= 5 億円
    - 正規化: zscore_normalize を利用し、指定列を Z スコア正規化して ±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成する処理を実装（generate_signals）。
    - コンポーネント:
      - momentum / value / volatility / liquidity / news（AIスコア）
    - デフォルト重みを定義（合計が 1.0 になるようスケール）。ユーザ指定 weights の検証と補完を実装（不正値は無視）。
    - Z スコア → Sigmoid 変換、欠損値は中立 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数が十分（>=3）の場合に BUY を抑制。
    - エグジット判定（_generate_sell_signals）:
      - ストップロス（終値 / avg_price - 1 <= -8%）
      - スコア低下（final_score < threshold）
      - 価格データ欠損時は SELL 判定をスキップ（誤クローズ防止）
      - 未実装の注記: トレーリングストップ / 時間決済（comments に明記）
    - signals テーブルへの日付単位の置換（トランザクションで原子性保証）。
    - ロギングで各ステップの状況を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- ニュースパーサで defusedxml を利用、RSS の受信サイズ制限・URL 正規化・トラッキングパラメータ削除などを実装し、安全性を考慮。
- J-Quants クライアントで HTTP エラー処理とトークンリフレッシュを厳密に扱い、誤った再帰や無限リトライを防止。

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装であり、positions テーブルに peak_price / entry_date 等の拡張が必要。
- news_collector の記事 ID 生成・DB 保存の詳細（SHA-256 切り出し長など）は実装コメントに記載されており、後続実装で DB スキーマとの連携が必要。
- 多くの機能が DuckDB の既定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, raw_news 等）を前提としているため、初期スキーマ作成スクリプトが必要。
- .env のパースは多くのケースに対応しているが、極端に複雑なシェル式の評価は行わない（意図的）。

---

今後の予定:
- execution 層（kabu ステーション連携）および monitoring（Slack 通知等）の実装拡充。
- news_collector の記事→銘柄マッピング（news_symbols）と raw_news の永続化実装。
- CI/テストの追加、ドキュメント（StrategyModel.md / DataPlatform.md）との照合による仕様テスト。

---