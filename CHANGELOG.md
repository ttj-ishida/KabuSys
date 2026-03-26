# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ (src/kabusys/__init__.py) に合わせています。

## [0.1.0] - 2026-03-26

初回リリース — 日本株自動売買システムのコア機能を実装・公開。

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ公開名: kabusys（__all__ に data, strategy, execution, monitoring を登録）
- 環境設定／自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）
  - .env / .env.local を自動で読み込み（OS 環境変数を保護、.env.local は override）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - 詳細な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートおよびエスケープ対応、コメント処理）
  - Settings クラスを提供し、必須環境変数チェックとデフォルト値、検証（KABUSYS_ENV / LOG_LEVEL の検証）を実装
  - 代表的な必須環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- ポートフォリオ構築（src/kabusys/portfolio）
  - 候補選定: select_candidates（スコア降順、signal_rank でタイブレーク）
  - 重み計算:
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア0時は等配分へフォールバック）
  - ポジションサイズ計算: calc_position_sizes
    - allocation_method="risk_based" / "equal" / "score" に対応
    - リスクベース算出（risk_pct、stop_loss_pct）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）スケールダウン
    - cost_buffer による手数料・スリッページの保守的見積もり
    - スケーリング時のフラクション再配分ロジック（lot_size 単位で残余を配分）

  - リスク調整: apply_sector_cap（セクター集中制限、売却予定銘柄を露出計算から除外）  
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に対する乗数と未知レジームのフォールバック）

- 戦略（src/kabusys/strategy）
  - 特徴量作成: build_features
    - research の生ファクターを取得（momentum / volatility / value）
    - ユニバースフィルタ（最低株価、平均売買代金）適用
    - 指定カラムを Z スコア正規化し ±3 でクリップ
    - DuckDB に対する日付単位の置換（冪等な UPSERT 実装）
  - シグナル生成: generate_signals
    - features と ai_scores を統合して最終スコアを計算（momentum/value/volatility/liquidity/news の重み和）
    - weights の入力検証・フォールバック・正規化処理
    - Bear レジーム判定により BUY を抑制
    - BUY（閾値超え）・SELL（ストップロス・スコア低下）を生成
    - SELL 優先ポリシー（SELL 対象を BUY から除外）、signals テーブルへトランザクション単位で置換書き込み

- 研究ユーティリティ（src/kabusys/research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
    - 各関数は DuckDB の prices_daily / raw_financials を参照してファクターを返す
  - 特徴量解析:
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman rank 相関に基づく IC 計算）
    - factor_summary（基本統計量の算出）
    - rank（同順位を平均ランクで処理）
  - 外部ライブラリに依存しない純粋 Python 実装（pandas 等を使用しない設計）

- バックテスト（src/kabusys/backtest）
  - メトリクス計算: calc_metrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）
  - ポートフォリオシミュレータ: PortfolioSimulator
    - 日次スナップショットとトレードレコードを保持
    - SELL を先に処理・BUY を後で処理（資金確保のため）
    - スリッページ（BUY +、SELL -）と手数料モデルを考慮した約定ロジック（部分的実装、詳細は後述）
    - TradeRecord / DailySnapshot の dataclass 定義

- パッケージ内部エクスポート整理
  - src/kabusys/portfolio/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py で主要 API を整理してエクスポート

### 変更 (Changed)
- （初版リリースのため履歴に記載する破壊的変更は無し）

### 修正 (Fixed)
- ログ/警告の充実
  - .env 読み込み失敗時の警告、DB トランザクションの ROLLBACK に失敗した場合の警告、価格欠損時の SELL 判定スキップ警告、未知レジームでのフォールバック警告などを追加

### 既知の制約・未実装（Notes / Known issues）
- execution モジュールはパッケージに含まれるが、実装は未完成（発注 API との接続など実稼働部分は未実装）
- monitoring モジュールは __all__ に含まれるが、実体はこのリリースに含まれていない
- position_sizing: 銘柄別の lot_size を将来サポートしたい旨の TODO（現状は全銘柄同一 lot_size を想定）
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価のフォールバックが必要
- generate_signals:
  - トレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルの追加情報が必要）
  - features が存在しない保有銘柄は final_score = 0.0 扱いで SELL の対象となる（ログ出力あり）
- PortfolioSimulator の SELL は現状「保有全量クローズ」のみで、部分利確・部分損切りは非対応
- 一部アルゴリズム（例: factor_summary の分散は母分散（N）を使用）や実運用に向けたチューニングは今後の改良対象
- DuckDB に対する SQL は現状のスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提としているため、スキーマ変更時は SQL を更新する必要あり

### セキュリティ (Security)
- なし

### 破壊的変更 (Breaking Changes)
- なし（初回公開）

---

脚注:
- 本リリースはコードから推測した機能仕様をもとに作成しています。実際の運用や API 仕様は README / ドキュメントおよび設計資料（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）を参照してください。