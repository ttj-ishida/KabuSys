# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の様式に準拠しています。  

## [0.1.0] - 2026-03-22

### Added
- 初期リリース。日本株向け自動売買フレームワークのコア機能を追加しました。
  - パッケージ初期化 (src/kabusys/__init__.py)
    - バージョン番号を 0.1.0 に設定し、主要サブパッケージを公開。
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート検出 (.git または pyproject.toml を基準) による .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export 形式やシングル／ダブルクォート、エスケープ、インラインコメントの扱いを考慮した堅牢な .env パーサを実装。
    - OS 環境変数を保護するための protected キー対応（.env.local を override で取り込みつつ既存 OS 環境を保護）。
    - 必須環境変数取得時に明確なエラーメッセージを返す _require メソッド。
    - 設定値の検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL を検証。
    - 既定の DB パス（DUCKDB_PATH, SQLITE_PATH）や API/Slack 関連設定のプロパティを提供。
  - 戦略関連
    - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
      - research の生ファクターを統合して features テーブルへ書き込む build_features を実装。
      - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
      - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップ、日付単位の冪等な upsert（トランザクション＋バルク挿入）を実装。
      - ルックアヘッドバイアス回避の方針に基づき target_date 時点のデータのみ使用。
    - シグナル生成 (src/kabusys/strategy/signal_generator.py)
      - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals を実装。
      - momentum/value/volatility/liquidity/news コンポーネントの計算ロジック（シグモイド変換、欠損値の中立補完など）を実装。
      - 重み付けの上書き受け入れ（不正値はスキップ）・自動リスケーリング対応。
      - Bear レジーム判定（市場の regime_score 平均が負の場合 BUY を抑制）を実装。
      - エグジット判定（ストップロス、スコア低下）を実装し SELL を生成。positions テーブル参照による売却判定を実装。
      - 日付単位の冪等書き込み（signals テーブルの置換）を実装。
  - 研究（Research）機能 (src/kabusys/research/)
    - ファクター計算 (src/kabusys/research/factor_research.py)
      - momentum（1/3/6ヶ月・MA200乖離）、volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、value（PER/ROE）を prices_daily / raw_financials から算出する関数群を実装。
      - 窓不足時に None を返す慎重な設計。
    - 特徴量解析ユーティリティ (src/kabusys/research/feature_exploration.py)
      - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL で一括取得）。
      - スピアマンランク相関（IC）計算 calc_ic（結合・欠損除外・最小サンプルチェック付き）。
      - ファクター統計サマリー factor_summary と rank ユーティリティを実装。
    - research パッケージのエクスポートを整理（__all__）。
  - バックテスト (src/kabusys/backtest/)
    - シミュレータ (src/kabusys/backtest/simulator.py)
      - PortfolioSimulator を実装。メモリ内保持、BUY/SELL 約定モデル、スリッページ・手数料モデル、SELL では保有全量クローズのポリシー。
      - BUY の資金不足時の株数再計算、平均取得単価の更新、約定履歴（TradeRecord）記録。
      - mark_to_market による日次スナップショット（DailySnapshot）記録と終値欠損時の警告ログ。
    - メトリクス (src/kabusys/backtest/metrics.py)
      - CAGR, Sharpe Ratio（無リスク=0に仮置き）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する calc_metrics を実装。
      - 各指標の個別計算ロジックを実装（エッジケースへの保護：サンプル不足、ゼロ除算回避等）。
    - バックテストエンジン (src/kabusys/backtest/engine.py)
      - 本番 DB からインメモリ DuckDB へデータをコピーする _build_backtest_conn（signals/positions を汚さないため）。
      - 日次ループ: 約定（前日シグナル→当日始値）、positions 書き戻し、時価評価、generate_signals による翌日シグナル生成、ポジションサイジングのフローを実装。
      - 日付範囲でのテーブルコピー、安全なコピー失敗時の警告ログ、market_calendar 全件コピー。
      - ヘルパー: 始値/終値取得、positions 書き戻し（冪等）、signals 読取。
    - バックテスト公開 API と型エクスポートを整理（__all__）。
  - パッケージのエクスポート整理（strategy / backtest / research の __all__ を通じた主要関数公開）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- 環境読み込み時のファイル読み込み失敗で警告を出して処理を継続する耐障害処理を追加（.env 読込で OSError をハンドル）。
- トランザクション処理時の例外発生時に ROLLBACK を試み、失敗時にログ出力する安全策を導入（features/signals 挿入時）。

### Security
- （初期リリースのため該当なし）

### Known limitations / Notes
- 一部仕様は意図的に未実装／簡易実装:
  - signal_generator のエグジット条件でトレーリングストップ・時間決済（保有 60 営業日超）は未実装（コメント記載）。
  - calc_value は PBR・配当利回りなどは未実装。
  - generate_signals は AI スコアが未登録の場合に中立値で補完する設計だが、実運用では ai_scores の整備が推奨。
- 外部依存:
  - DuckDB を前提としている（prices_daily / raw_financials / features 等のテーブルが必要）。
  - 研究用コードは pandas 等に依存せず標準ライブラリ＋DuckDBで実装しているため、データ整形は DuckDB 側で行う前提。
- 正確な本番接続・発注は execution 層に依存しており、本リリースでは発注 API への直接呼び出しは含まれない（戦略層は発注層と分離）。

---

今後の予定（例）
- trailing stop / 時間決済の実装
- execution 層（kabuステーションとの連携）の提供
- AI スコア生成パイプラインとの統合
- 単体テスト・型チェック・CI の整備

---- 
(この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・マージ情報に基づいて調整してください。)