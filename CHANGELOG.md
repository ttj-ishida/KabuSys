# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは主にコードベースの初期リリース（v0.1.0）に含まれる機能・設計意図・既知の制約をコードから推測してまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を導入。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys/__init__.py）とバージョン定義 `__version__ = "0.1.0"`。

- 設定・環境変数（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - ルート検出: __file__ を起点に親ディレクトリから `.git` または `pyproject.toml` を探してプロジェクトルートを特定。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - .env パーサーの強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートの有無で挙動を分離）。
    - ファイル読み込み時に OS 環境変数を保護する `protected` 処理（既存 OS 環境変数の上書きを防止）。
  - 必須設定取得メソッド `_require` による明示的エラー（未設定時 ValueError）。
  - 設定クラス `Settings` を提供:
    - J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティ（デフォルト値や Path 変換を含む）。
    - `KABUSYS_ENV`（development/paper_trading/live）や `LOG_LEVEL` の値検証。
    - 辞書的プロパティ: `is_live`, `is_paper`, `is_dev`。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定（portfolio_builder.select_candidates）
    - スコア降順ソート、同点時は `signal_rank` 昇順でタイブレーク。
  - 重み計算
    - 等金額配分（calc_equal_weights）
    - スコア加重配分（calc_score_weights）
      - 全スコアが 0 の場合は等分配へフォールバックし WARNING を出力。
  - リスク調整（risk_adjustment）
    - セクター集中制限（apply_sector_cap）
      - 既存保有のセクター別時価算出（当日売却予定銘柄を除外するオプションあり）。
      - "unknown" セクターは上限適用対象外。
      - セクター超過時に新規候補から除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）
      - マッピング: "bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 にフォールバック（警告ログ）。
  - 株数決定（position_sizing.calc_position_sizes）
    - 複数の配分方式をサポート: "risk_based", "equal", "score"。
    - risk_based: 許容リスク率（risk_pct）とストップロス率（stop_loss_pct）を用いた株数算出。
    - equal/score: 重み（weights）に基づく割当、`max_position_pct` による per-position 上限、`max_utilization` による総投下上限考慮。
    - 単元（lot_size）丸め、`cost_buffer` による手数料・スリッページ考慮。
    - aggregate cap 超過時のスケーリング処理:
      - 各銘柄のスケーリング、lot 単位での丸め、残差（fractional_remainder）に基づく追加配分アルゴリズムを実装（残余キャッシュで端数補充）。
    - 価格欠損時のスキップや詳細なデバッグログ。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 = 300 円、20日平均売買代金 >= 5億円）適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - DuckDB のトランザクションで date 単位の置換（DELETE→INSERT）により冪等性を確保。エラー時にロールバック。

  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントごとに欠損は中立値 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、ユーザ重みをマージして合計が 1.0 でない場合は再スケール。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合）により BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60。
    - SELL（エグジット）判定:
      - ストップロス（終値未満が -8% 以下）を最優先。
      - final_score が閾値未満の場合は score_drop として SELL。
      - features に存在しない保有銘柄は final_score=0 と見なして SELL 判定（警告ログ）。
    - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。ロールバック時は警告ログ。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ウィンドウ未満は None）。
    - Volatility: 20日 ATR（真の範囲=tr／prev_close 管理）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 の場合は PER=None）。
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials のみ参照。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）対応。ホライズン検証と範囲制約（<=252 日）。
    - IC（Information Coefficient）計算（calc_ic）: Spearman の ρ をランク（平均ランク処理）で計算。サンプル 3 未満は None。
    - ランク処理（rank）: 同順位は平均ランク、浮動小数丸めで ties の検出の安定化。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。

- バックテスト（kabusys.backtest）
  - メトリクス（metrics.calc_metrics）
    - CAGR, Sharpe Ratio（無リスク=0）、最大ドローダウン、勝率、ペイオフ比、総取引数を計算する API を実装。
    - 内部関数で年次化や分散計算の実装を含む。
  - シミュレータ（simulator.PortfolioSimulator）
    - メモリ内でのポートフォリオ管理、擬似約定を実装。
    - TradeRecord / DailySnapshot データクラス。
    - 約定処理:
      - SELL を先に全量クローズ、その後 BUY（部分約定は非対応だが lot_size による丸めはサポート）。
      - スリッページ（BUY +、SELL -）・手数料率に基づく約定価格と commission の計算を想定。
    - エンジン層からの呼び出し用途に設計。DB 参照は持たない純粋な状態管理。

- モジュールのエクスポート整理
  - strategy、portfolio、research モジュールで主要関数を __all__ にエクスポートして簡易インポートを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
  - ただし多くの関数で「価格欠損時には処理をスキップ」「データ不足時は None を返す」「エラー時にトランザクションをロールバックして警告」を明示的に扱う実装がされている。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境を保護する仕組み（protected set）を導入して、意図しない上書きを防止。

---

## 既知の制約・今後の改善予定（コードコメントより）
- position_sizing.calc_position_sizes:
  - 将来的には銘柄別の lot_size をサポートする設計への拡張が予定（現在は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題がある旨の TODO（前日終値や取得原価でのフォールバック検討）。
- signal_generator:
  - トレーリングストップや時間決済のためには positions に peak_price / entry_date 等の追加情報が必要（未実装）。
- feature_engineering / signal_generator:
  - DuckDB を用いたトランザクションで冪等性を担保しているが、本番環境でのパフォーマンス・同時実行性の検証が必要。
- simulator:
  - BUY の部分約定／複雑な注文タイプは未対応（SELL は全量クローズのみ）。
- research.calc_forward_returns:
  - horizons の上限は 252（1 年営業日想定）に制限。
- .env パーサー:
  - 複雑なシェル展開や複数行クォートなどの完全なシェル互換は対象外（最低限の .env 形式を想定）。

---

下記モジュールは雛形／空ファイルが含まれており、今後実装が想定されます:
- src/kabusys/execution/__init__.py
- 監視（monitoring）関連のエントリ（__all__ に記載されているがコードは別途）

以上。README やドキュメント（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md, UniverseDefinition.md 等）に基づく設計思想をコード内ドキュメントとして反映しています。リリース後はユニットテスト、性能検証、エッジケースの追加テストを推奨します。