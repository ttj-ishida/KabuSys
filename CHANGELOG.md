CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトはセマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。

フォーマットは Keep a Changelog に準拠しています（追加: Added、変更: Changed、修正: Fixed、削除: Removed、非推奨: Deprecated、セキュリティ: Security）。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-26

初回公開（ベース実装） — KabuSys 0.1.0

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン情報と主要サブパッケージを公開。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 複雑な .env 行パース実装（export 構文、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパー _require。
    - 設定ラッパー Settings（J-Quants / kabu API / Slack / DBパス / 環境種別・ログレベルの検証、is_live / is_paper / is_dev）。

- ポートフォリオ構築（純粋関数群、DB非依存）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが0の場合は等配分へフォールバックと警告ログ）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing の主要実装（risk_based / equal / score の allocation_method 対応）。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り。
    - スケーリング後の切捨てによる端数を fractional 残差に基づき再配分するロジック（再現性を意識した安定ソート）。
    - 将来的な拡張点として銘柄別 lot_map を想定した TODO コメントあり。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（当日売却予定銘柄を露出計算から除外、"unknown" セクターは上限適用除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバック）。

- 戦略（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - research 側で計算した生ファクターをマージ・ユニバースフィルタ適用・Zスコア正規化・±3クリップして features テーブルへ UPSERT（トランザクションによる日付単位置換、冪等性確保）。
    - ユニバース判定基準（最低株価・20日平均売買代金）を実装。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - ファクター重みの補完・検証・再スケーリング実装（不正なユーザー重みはスキップし、合計が1になるよう調整）。
    - AI ニューススコア補完、Bear レジーム検知時の BUY 抑制、SELL はストップロスとスコア低下を実装。
    - SELL 優先ポリシー（SELL 対象を BUY から除外し、BUY のランクを再付与）。
    - 生成処理はトランザクションで原子性を保証。ROLLBACK の失敗時は警告ログ。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum（1/3/6ヶ月リターン、MA200乖離）、Volatility（20日ATR、相対ATR、20日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB 上の SQL と Python 組合せで実装。
    - データ不足時の None ハンドリングを考慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズン検証）、IC（Spearman ランク相関）calc_ic、ファクター統計 summary を実装。
    - ランク計算時の同順位処理（平均ランク）と丸め（round(v, 12)）による ties 対応。
  - リサーチパッケージ __all__ に主要関数を公開。

- データユーティリティ連携
  - feature_engineering / research から kabusys.data.stats.zscore_normalize を利用。

- バックテスト基盤
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 内部計算は pure 関数で実装、エッジケース（データ不足やゼロ除算）に対する保護ロジックあり。
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator 実装（メモリ内状態管理、日次スナップショット・約定レコード保持）。
    - execute_orders: SELL を先に処理し全量クローズ、BUY は lot_size 単位で約定。スリッページ・手数料モデル対応。
    - TradeRecord に realized_pnl を保持（SELL 時のみ）。

- パッケージのエクスポート調整
  - src/kabusys/portfolio/__init__.py と src/kabusys/strategy/__init__.py にて主要関数を上位エクスポート。

### Fixed
- .env 読み込みでの I/O エラー時に warnings.warn で通知するようにし、読み込み失敗を安全にスキップする実装（config._load_env_file）。
- DB トランザクション内での例外時に ROLLBACK を試み、失敗した場合は警告ログを出すことで不整合時のデバッグ性を向上（feature_engineering / signal_generator）。

### Known issues / Notes（既知の制約・未実装点）
- position_sizing:
  - 銘柄別の単元（lot_size）を受け取る設計は未実装（全銘柄共通 lot_size の想定）。将来的に銘柄別 lot_map を受け取る拡張予定。
  - open_prices に欠損や 0 がある場合、該当銘柄はスキップされるため期待通りの配分にならない可能性あり（ログで通知）。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価され、ブロック対象から外れる恐れがある（将来的に前日終値や取得原価等のフォールバックを検討）。
  - "unknown" セクターはセクター上限の対象外となる設計。
- signal_generator:
  - Bear 相場では generate_signals が BUY シグナルを抑制する仕様（StrategyModel.md に準拠）。Bear 判定に用いる ai_scores のサンプル数が一定数未満なら Bear 判定を行わない（誤判定防止）。
  - トレーリングストップや時間決済（保有期間による自動決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- simulator:
  - SELL は全量クローズのみサポート。部分利確・部分損切りは未対応。
- DB スキーマ依存事項:
  - features / ai_scores / positions / prices_daily / raw_financials / signals 等のテーブルスキーマや存在が前提（duckdb を使用）。実際の運用前にスキーマ準備が必要。
- エラーハンドリング:
  - 一部の内部処理で詳細な例外ラッピングは行っていないため、上位でのハンドリングやユニットテストでの網羅が推奨。

### Breaking Changes
- 初版のため破壊的変更は無し（今後のリリースで API/関数署名の変更があり得ます。）。

---

この CHANGELOG はコードコメント・実装から推測して記載しています。実運用前に各モジュールのユニットテストと実動作確認を強く推奨します。