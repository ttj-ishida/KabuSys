CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

フォーマットの慣例:
- Unreleased — 今後の変更（このリポジトリでは空）
- 各リリースは日付付きで記載
- セクションは Added / Changed / Fixed / Removed / Security など

Unreleased
----------

- なし

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にて __version__ = "0.1.0"
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート (.git または pyproject.toml) を起点に自動的に .env/.env.local を検索して読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォートとバックスラッシュエスケープの取り扱い
    - インラインコメントの扱い（クォートの有無に応じたルール）
  - 必須環境変数取得用の _require() と Settings クラスを提供。必須キー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）に対する未設定時の明示的エラー。
  - KABUSYS_ENV（development/paper_trading/live）のバリデーション、LOG_LEVEL のバリデーションなどのシステム設定検証。

- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールで計算した raw ファクターを統合し、ユニバースフィルタ（株価・流動性基準）を適用。
    - 選定ファクターの Z スコア正規化と ±3 クリップを実行。
    - DuckDB の features テーブルへ日付単位で冪等（DELETE→INSERT トランザクション）で書き込み。ROLLBACK の失敗もログで警告。
    - ユニバース基準（デフォルト）: 最低株価 300 円、20日平均売買代金 5億円。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - シグモイド変換、欠損値は中立 0.5 で補完、ユーザ指定 weights の妥当性チェックとリスケーリングを実装。
    - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数閾値以上で判定）により BUY シグナルを抑制。
    - SELL シグナル（ストップロス、スコア低下）を実装し、SELL 優先ポリシーで BUY から除外。
    - signals テーブルへ日付単位で冪等に書き込み（トランザクション＋バルク挿入）。
    - 実装済みの売り判定条件に関する説明（トレーリングストップ等は未実装）。

- リサーチ / ファクター計算（src/kabusys/research）
  - calc_momentum / calc_volatility / calc_value（src/kabusys/research/factor_research.py）
    - prices_daily / raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を算出。
    - データ不足時に None を返す扱い、ウィンドウサイズ不足の判定を含む。
    - DuckDB のウィンドウ関数を活用した効率的実装（LAG / AVG / COUNT / LEAD 等）。
  - 研究補助ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの fwd_return を一度の SQL で取得。
    - IC（calc_ic）: スピアマンのランク相関を実装。最小有効サンプル数チェック。
    - factor_summary / rank: 基本統計・同順位処理（平均ランク）を提供。
  - research/__init__.py で主要関数を再エクスポート。

- バックテストフレームワーク（src/kabusys/backtest）
  - ポートフォリオシミュレータ (PortfolioSimulator)
    - 約定ロジック（SELL 先行、BUY は資金に応じて株数切り捨て、スリッページと手数料反映）。
    - mark_to_market による日次スナップショット記録 (DailySnapshot)。
    - TradeRecord による約定履歴保持（SELL 時に realized_pnl を計算）。
  - バックテストエンジン (run_backtest)
    - 本番 DB からインメモリ DuckDB へ期間データをコピーして独立してバックテスト実行（signals / positions を汚染しない）。
    - 日次ループ: 前日シグナルの約定→positions 書き戻し→時価評価→当日シグナル生成→ポジションサイジング→翌日の注文作成 の流れを実装。
    - スリッページ・手数料・max_position_pct をパラメータ化。
    - get_trading_days や DB コピー処理のエラーはログで警告しつつフェールセーフに。
  - バックテスト評価指標 (metrics.calc_metrics)
    - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, トレード数等を計算。

Changed
- 設計方針・注意点をコード内ドキュメントに明記
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用する設計を一貫して適用。
  - research モジュールは外部 API や本番発注層に依存しない（DuckDB のみ参照）。
  - 外部重い依存（pandas 等）をあえて使用せず、標準ライブラリ + DuckDB で実装。

Fixed
- 初期リリースのため特定の「修正」は無し。ただし以下のフォールバックや安全策を導入:
  - .env ファイル読み込みでファイルオープン失敗時は warnings.warn で処理を継続。
  - DB トランザクション失敗時の ROLLBACK 失敗をログ出力してエラーのトレースを容易に。

Known limitations / Notes
- 一部のエグジット条件（トレーリングストップ、時間決済）は未実装（コード中に TODO 記載あり）。positions テーブルに peak_price / entry_date が必要。
- AI ニューススコアは ai_scores テーブルから取り込み、未登録時は中立扱い（0.5）で補完される。
- calc_forward_returns はホライズンの上限を 252 営業日に制限。
- バックテストは市場カレンダー等をコピーするが、コピー中の例外は警告してスキップする実装。
- 本パッケージは DuckDB を利用するため、実行環境に DuckDB パッケージが必要。
- 型ヒントに Python 3.10+ の構文（|）を使用しているため、対応する Python バージョンに注意。

Security
- 特になし（初回リリース）。環境変数や .env の取り扱いは OS 環境変数を保護する仕組み（protected set）を用いている。

Authors / Contributors
- リード実装者情報はソース中に記載なし（パッケージ初回リリース）。

補足
- 本 CHANGELOG はコードベースから機能・変更点を推測して記載しています。実際のコミット履歴やリリースノートがある場合は合わせて参照してください。