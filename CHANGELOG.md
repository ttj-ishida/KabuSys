# CHANGELOG

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しています。以下の主要機能・設計上の注意点を含みます。

### Added

- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名・バージョンと公開モジュールを定義（version = 0.1.0）。

- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env ファイル自動読み込み機能（OS 環境変数 > .env.local > .env の優先度）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索（CWD 非依存）。
    - .env 行パーサ（export プレフィックス、クォート内エスケープ、インラインコメント処理など）を実装。
    - 環境変数の必須チェック（_require）。
    - Settings クラス：J-Quants / kabu ステーション / Slack / DB パス / システム環境（env, log_level）等の取得ロジック。

- データ取得・保存（J-Quants API）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（ページネーション対応）。
    - レート制限制御（固定間隔スロットリング、120 req/min）。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 発生時のトークン自動リフレッシュ（1 回限り）とモジュールレベルの ID トークンキャッシュ。
    - fetch_* 系関数：fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - save_* 系関数：save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存、ON CONFLICT を用いたアップサート）。
    - 取得時刻 (fetched_at) を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。

- データ前処理・収集（ニュース）
  - src/kabusys/data/news_collector.py:
    - RSS フィードからのニュース収集機能（デフォルトで Yahoo Finance を含む）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）。
    - セキュリティ対策：
      - defusedxml を使った XML パース（XML-Bomb 等の防止）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
      - HTTP/HTTPS 以外のスキーム拒否・SSRF 想定対策。
    - 記事 ID の一意化（正規化後 URL の SHA-256 先頭 32 文字等）で冪等性を確保。
    - バルク INSERT チャンク処理、INSERT RETURNING を想定した実装（パフォーマンス配慮）。

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py:
    - モメンタム (calc_momentum)：1M/3M/6M リターン、200 日移動平均乖離の計算。
    - ボラティリティ (calc_volatility)：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio。
    - バリュー (calc_value)：最新の財務データ（eps, roe）を用いた PER / ROE 計算（EPS=0 や欠損時の取り扱い有り）。
    - DuckDB SQL とウィンドウ関数を主体に実装し、営業日欠損や部分窓に配慮。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)：任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - IC（Information Coefficient）計算 (calc_ic)：スピアマンのランク相関を実装（同順位は平均ランク処理）。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank ユーティリティ：同順位の平均ランク処理、丸めによる ties 対応。

  - src/kabusys/research/__init__.py: 上記関数群の公開。

- 特徴量エンジニアリング（features）
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールから生ファクターを取得して統合 → ユニバースフィルタ（最低株価、20 日平均売買代金）適用 → 指定列を Z スコア正規化 → ±3 でクリップ → features テーブルへ日付単位で置換（トランザクション + バルク挿入）する build_features 実装。
    - ユニバース基準値: 最低株価 300 円、最低平均売買代金 5 億円。
    - 正規化対象列とクリップの扱いを明確化。

- シグナル生成（signals）
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals 実装。
    - コンポーネントスコア：momentum / value / volatility / liquidity / news（AI スコア）。
    - スコア変換ユーティリティ（シグモイド、平均化、欠損時の中立補完 0.5）。
    - デフォルト重みと閾値の実装（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD）。weights の検証・フォールバック・再スケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - エグジット判定（_generate_sell_signals）:
      - ストップロス（終値/avg_price - 1 <= -8%）、
      - final_score の閾値未満。
      - 価格欠損時の SELL 判定スキップや、features に存在しない保有銘柄は score=0 として扱うなど安全策あり。
    - signals テーブルへの日付単位での置換（トランザクション + バルク挿入）で冪等性を確保。

- 汎用ユーティリティ
  - src/kabusys/data/jquants_client.py: _to_float / _to_int（堅牢な型変換ロジック）。
  - config の .env パーサ等、細かな入力正規化と堅牢性向上ロジックを多数実装。

### Security

- news_collector: defusedxml を使用して XML による攻撃を緩和。
- news_collector: 受信最大バイト数の制限を導入（10MB）。
- news_collector: URL 正規化でトラッキングパラメータを除去、SSRF 想定のスキーム制約を明確化。
- jquants_client: API リトライ時に Retry-After を尊重、無限リフレッシュを防ぐため allow_refresh フラグを使用。

### Notes / Known limitations / Todo

- 戦略の未実装/保留点（ソース内コメント参照）:
  - トレーリングストップ（直近最高値からの -10%）や時間決済（保有 60 営業日超過）は positions テーブルに peak_price / entry_date 等が必要であり、現バージョンでは未実装。
  - features, signals, ai_scores, positions 等の DuckDB スキーマは本 changelog に含まれていません。実行前に期待されるスキーマ／インデックス／制約を用意する必要があります。
- research モジュールは外部依存（pandas 等）を排して標準ライブラリと DuckDB の SQL を中心に実装しています。大量データ時のメモリ/性能特性は運用環境で評価してください。
- news_collector の URL 正規化・ID 生成ロジックは既知のトラッキングパラメータに基づくため、追加のケースがある場合は拡張が必要です。
- 環境変数に多数の必須項目（JQUANTS / SLACK 等）があるため、.env.example を参照し設定を整えてください。

### Breaking Changes

- 初回リリースのため特にありません。

### Authors / Contributors

- 本リリースはコード内の実装に基づき生成しています（リポジトリのメタデータは含めていません）。

---

この CHANGELOG はコードから推測して作成しています。実際のリポジトリやドキュメントが存在する場合は、そちらの変更履歴やリリースノートと照合してください。