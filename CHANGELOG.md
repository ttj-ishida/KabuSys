# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。主要な追加点は以下の通りです。

### Added
- パッケージ初期化・バージョン情報
  - `kabusys.__version__ = "0.1.0"` を追加し、主要サブパッケージをエクスポート (`data`, `strategy`, `execution`, `monitoring`)。

- 環境変数 / 設定管理
  - `kabusys.config.Settings` クラスを実装。環境変数から各種設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベルなど）を取得。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
  - `.env` / `.env.local` の読み込みロジック、優先順位（OS 環境 > .env.local > .env）と保護（既存 OS 環境変数を上書きしない）を実装。
  - `.env` パースは `export KEY=...`、引用符（シングル/ダブル）内のエスケープ、インラインコメントの扱い等に対応。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。

- 戦略: 特徴量エンジニアリング
  - `kabusys.strategy.feature_engineering.build_features` を実装。
    - 研究モジュール（`kabusys.research.factor_research`）から生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）し ±3 でクリップ。
    - `features` テーブルへ日付単位で置換（冪等、トランザクション + バルク挿入）。
    - 欠損や休日を考慮して target_date 以前の最新価格を参照する実装。

- 戦略: シグナル生成
  - `kabusys.strategy.signal_generator.generate_signals` を実装。
    - `features` と `ai_scores` を統合し、モメンタム / バリュー / ボラティリティ / 流動性 / ニュースのコンポーネントスコアを算出して重み付き合算（デフォルト重みを定義）。
    - シグモイド変換・欠損時の中立補完（0.5）・重みの検証とリスケーリングを実装。
    - Bear レジーム検出（AI の `regime_score` 平均が負、かつサンプル数 >= 3 のとき）による BUY 抑制。
    - BUY 閾値デフォルト 0.60、SELL 判定としてストップロス（-8%）およびスコア低下を実装。
    - `signals` テーブルへ日付単位で置換（トランザクション + バルク挿入）。SELL を優先して BUY から除外する方針を採用。

- Research（研究用ユーティリティ）
  - `kabusys.research.factor_research` にてファクター計算を実装:
    - `calc_momentum`: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - `calc_volatility`: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - `calc_value`: raw_financials から最新財務データを取り出し PER / ROE を計算（EPS が 0 または欠損のときは PER を None にする）。
  - `kabusys.research.feature_exploration` にて解析ユーティリティを実装:
    - `calc_forward_returns`: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - `calc_ic`: スピアマンランク相関（IC）を計算。
    - `factor_summary`: 各ファクターの count/mean/std/min/max/median を算出。
    - `rank`: 同順位を平均ランクにするランク変換（丸めを用いて ties の取り扱いを安定化）。

- バックテストフレームワーク
  - `kabusys.backtest.simulator.PortfolioSimulator` を実装:
    - BUY/SELL の疑似約定ロジック（始値 + スリッページ、手数料、BUY 時の株数再計算、SELL は全量クローズ）とトレード記録（TradeRecord）を管理。
    - `mark_to_market` による日次スナップショット記録（終値欠損時は 0 として警告ログ）。
  - `kabusys.backtest.metrics` にてバックテスト評価指標を実装:
    - CAGR, Sharpe Ratio（無リスク金利 0）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算。
  - `kabusys.backtest.engine.run_backtest` を実装:
    - 本番 DB から必要データをインメモリ DuckDB（`init_schema(":memory:")`）へコピーしてバックテストを実行（signals/positions を汚さない）。
    - 日次ループ: 前日シグナル約定 → positions に書き戻し → 終値評価（スナップショット）→ `generate_signals` 実行 → BUY/SELL の発注リスト作成（ポジションサイジングに max_position_pct を考慮）。
    - データコピー範囲・例外処理により実運用 DB に対する安全性を確保。

- モジュール再エクスポート
  - `kabusys.backtest.__init__`, `kabusys.research.__init__`, `kabusys.strategy.__init__` に主要 API をエクスポート。

### Changed
- なし（初回リリースのため変更履歴なし）。

### Fixed
- なし（初回リリースのため修正履歴なし）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

Notes / 備考
- 多くの処理は DuckDB の SQL ウィンドウ関数を多用しており、prices_daily / raw_financials / features / ai_scores 等のスキーマ準拠が前提です。
- `kabusys.data.stats.zscore_normalize` 等、データユーティリティは別モジュール（data パッケージ）に依存します。実行前にスキーマと必要テーブルの準備を行ってください。
- `feature_engineering` / `signal_generator` は発注層（execution）や外部 API に直接依存しない設計です。これによりテストとバックテストが容易になっています。

貢献者
- 初期実装: コードベース（関数・クラスの docstring を含む）に基づいて CHANGELOG を作成しました。

---- 

（このファイルはプロジェクトの最初のリリースノートです。今後の変更はこのファイルに追記してください。）