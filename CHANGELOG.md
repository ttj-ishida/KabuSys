CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョン番号はパッケージ定義（kabusys.__version__）に基づいています。

[Unreleased]
-------------

（現在なし）

[0.1.0] - 2026-03-22
-------------------

Added
- 基本パッケージ構成を追加
  - src/kabusys/__init__.py にパッケージ名とバージョン、公開モジュール一覧を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可（テスト用）。
  - .env パーサを実装し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - OS 環境変数を保護する "protected" ロジック（.env.local の上書き時に既存 OS 環境を保持）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定などのプロパティを取得。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M モメンタム、200 日移動平均乖離率の計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率の算出。
    - calc_value: latest raw_financials と結合して PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）の一括取得（1 クエリで複数ホライズン対応）。
    - calc_ic: スピアマン順位相関（IC）計算機能。
    - factor_summary / rank: 基本統計量計算とランク付けユーティリティ。
  - research パッケージは外部ライブラリに依存せず DuckDB を利用。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールから取得した raw factor を統合し、ユニバースフィルタ（最低株価 / 20 日平均売買代金）を適用。
  - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへの日付単位の置換（DELETE 後 INSERT）をトランザクションで行い冪等性を保証。
  - 欠損や異常値処理、最新価格の取得は target_date 以前の最新値を参照して休場日対応。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
  - コンポーネントはシグモイド変換・平均化して final_score を算出。欠損は中立値 0.5 で補完。
  - AI の regime_score を集計して Bear レジーム判定を行い、Bear 時は BUY シグナルを抑制。
  - デフォルト重みと閾値を実装（重みはユーザー入力で補完・検証し合計が 1.0 にリスケール）。
  - 保有ポジションに対するエグジット判定（ストップロス、スコア低下）を実装し SELL シグナルを生成。
  - signals テーブルへの日付単位の置換をトランザクションで実施し冪等性を担保。
  - 不正な weight 値や NaN/Inf をスキップして警告出力。

- バックテストフレームワーク (kabusys.backtest)
  - simulator:
    - PortfolioSimulator による擬似約定、ポジション管理、コスト基準（平均取得単価）管理を実装。
    - SELL を先に処理し保有全量をクローズ（部分利確は非対応）。BUY は割り当て額に基づき端数切り捨て。
    - スリッページ率・手数料率の適用ロジックとトレード記録（TradeRecord）を実装。
    - mark_to_market により終値で時価評価を行い日次スナップショット（DailySnapshot）を記録。欠損終値は 0 として警告。
  - metrics:
    - バックテスト指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, 総トレード数）。
  - engine:
    - run_backtest 実装。実運用 DB からインメモリ DuckDB へ期間限定データをコピーしてバックテストを実行。
    - コピー対象テーブルは prices_daily, features, ai_scores, market_regime, market_calendar（market_calendar は全件）。
    - コピー範囲は start_date - 300 日〜end_date（features 等の生成に必要な過去データを確保）。
    - 日次ループ: 前日シグナルを始値で約定 → positions テーブル書き戻し → 終値評価 → generate_signals 呼び出し → ポジションサイジング/発注。
    - signals 読み出しユーティリティと positions 書き戻しユーティリティを提供。

- モジュール公開・インポート利便性
  - strategy, research, backtest の主要 API を __init__ で公開（例: build_features, generate_signals, run_backtest 等）。

Changed
- なし（初版リリース）

Fixed
- なし（初版リリース）

Security / Robustness
- .env 読み込み時にファイル IO エラーで警告を出して処理を続行。
- DB 操作時にトランザクション (BEGIN/COMMIT/ROLLBACK) を用いて原子性を確保。ROLLBACK に失敗した場合は警告ログを出力。
- 欠損データ（価格欠損等）に対しては処理をスキップまたは中立値で補完し、誤操作を防ぐ設計。

Notes
- research パッケージは本番環境の発注 API に一切依存しない設計。DuckDB のテーブル（prices_daily, raw_financials）だけを参照する。
- 一部アルゴリズムや指標（例: トレーリングストップ、時間決済、PBR/配当利回り）は未実装で TODO の旨コメントあり。
- デフォルト定数（閾値、重み、スキャン日数など）はコード内に定義されており、必要に応じて呼び出し側で上書き可能。

Development
- 詳細な設計仕様はコード内の docstring（StrategyModel.md, BacktestFramework.md 等参照の記載）に従うこと。

今後の予定（例）
- 部分利確 / トレーリングストップ等のエグジット戦術の追加
- PBR・配当利回り等バリューファクターの実装
- AI スコア連携インターフェースの拡張と監視用ダッシュボード

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートはプロジェクト方針に合わせて調整してください。）