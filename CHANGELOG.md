# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
この CHANGELOG は「Keep a Changelog」形式に準拠しています。以下の記載は提示されたコードベースの内容から推測して作成しています（実装コメント・関数名・定数等に基づく）。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース — 基本機能の実装とデータ処理／戦略生成パイプラインの整備

### Added
- パッケージ基盤
  - kabusys パッケージを作成、バージョンを "0.1.0" に設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索することでカレントワーキングディレクトリに依存しない読み込みを実現。
  - .env / .env.local の読み込み順序を実装（OS 環境変数を保護、.env.local は override=True）。
  - .env の行パーサを実装（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / ログレベル等の設定プロパティを提供。環境値の検証（KABUSYS_ENV, LOG_LEVEL）を行う。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - ページネーション対応の fetch_* 関数（株価日足、財務データ、マーケットカレンダー）。
    - API レート制御（120 req/min）のための固定間隔レートリミッタを実装。
    - リトライロジック（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 対応。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュを提供。
    - JSON デコードエラーやネットワークエラーのハンドリング。
  - DuckDB へ保存する save_* 関数を実装（raw_prices / raw_financials / market_calendar）。ON CONFLICT DO UPDATE（冪等性）を使用。
  - 取得データの型変換ユーティリティ _to_float / _to_int を提供（安全な変換ロジック）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集器を実装（デフォルトで Yahoo Finance のビジネス RSS を設定）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - defusedxml を利用して XML 攻撃を緩和。
  - 最大受信バイト数の制限（10 MB）や不正スキーム拒否などの安全対策。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し、冪等保存を想定。
  - バルク INSERT のチャンク処理を実装し、DB 書き込み効率を配慮。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - Momentum, Volatility, Value（および一部の流動性指標）を計算する関数を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA による乖離）。
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、volume_ratio。
    - calc_value: PER、ROE（raw_financials の最新レコードと結合）。
  - DuckDB を用いた SQL ベースの実装で、営業日欠損やウィンドウサイズ不足時の安全対策を実装。

- 研究ユーティリティ（src/kabusys/research/feature_exploration.py）
  - 将来リターン計算 calc_forward_returns（任意ホライズンに対応、1/5/21 日をデフォルト）。
  - スピアマンの IC（calc_ic）とランク関数 rank を実装（同順位は平均ランク処理）。
  - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）を算出。
  - すべて外部依存（pandas 等）なしで実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - 研究モジュールの生ファクターを取り込み、正規化・合成して features テーブルに保存する build_features を実装。
  - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリッピングを適用。
  - 日付単位で削除→挿入する方式で冪等性を確保（トランザクション・バルク挿入）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装し、features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存。
  - コンポーネントスコア:
    - momentum（momentum_20, momentum_60, ma200_dev のシグモイド平均）
    - value（PER を 20 を基準にスケール）
    - volatility（atr_pct の Z スコアを反転してシグモイド）
    - liquidity（volume_ratio のシグモイド）
    - news（AI スコアをシグモイドで変換、未登録は中立）
  - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（BUY=0.60）。
  - weights 引数の入力検証（未知キー・非数値・負値などを無視）、合計が 1.0 になるよう再スケール。
  - Bear レジーム検出: ai_scores の regime_score の平均が負であれば BUY を抑制（サンプル数閾値あり）。
  - エグジット（SELL）条件:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満
    - トレーリングストップや時間決済は未実装（positions に peak_price / entry_date が必要）。
  - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。

- パッケージ再エクスポート（src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py）
  - 主要関数群を __all__ で公開（研究・戦略 API の整理）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース XML パースに defusedxml を使用。
- news_collector で受信サイズ上限を設定し DoS を緩和。
- RSS の URL 正規化でトラッキングパラメータ除去、SSRF 対策を意識した実装方針。

### Notes / Limitations（実装から推測される注意点）
- execution パッケージは __init__.py のみで、発注系実装は含まれていない（発注層は別途実装が必要）。
- monitoring モジュールはパッケージに含まれる想定だが実装ファイルは提示コード内に明示されていない。
- news_collector の記事 ID 生成や raw_news への紐付け（news_symbols）等の細部はコメントベースの設計であり、実際の紐付け処理や DB スキーマに依存する。
- 一部の未実装機能（トレーリングストップ、時間決済など）はソース内に明示的に「未実装」として記載されている。

---

この CHANGELOG はコードコメント・関数名・定数・ロギング文等からの推測に基づいています。実際のリリースノートとして公開する場合は、実装差分やコミット履歴に基づく補足・修正を行ってください。