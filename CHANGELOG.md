CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョンはパッケージの __version__（src/kabusys/__init__.py）を基にしています。

Unreleased
----------
今後の改善点・未実装の仕様（コード内コメント・TODOから推測）:

- トレーリングストップ（直近最高値からの一定割合での退出）の実装予定
- 保有期間に基づく時間決済（例: 60 営業日超で決済）の実装予定
- calc_value における PBR / 配当利回り 等のバリューファクター拡張
- positions テーブルに peak_price / entry_date 等のメタデータを格納し、SELL 判定ロジックを強化
- 部分利確・部分損切りのサポート（現在は保有全量をクローズ）
- CI・単体テストの拡充やエラーハンドリングの強化

[0.1.0] - 2026-03-22
--------------------

Added
- 基本パッケージ初期リリース: kabusys 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開 API の __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env 行パーサの実装（export 付き、クォート内エスケープ、インラインコメント処理等を考慮）。
  - Settings クラスでアプリケーション設定を提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
    - デフォルトパス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research で作成した生ファクターを結合・正規化して features テーブルへ UPSERT（冪等）する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化、±3 でクリップして外れ値影響を抑制。
    - トランザクション＋バルク挿入で日付単位の置換を行い原子性を確保。
  - research モジュールの calc_momentum / calc_volatility / calc_value との連携。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合して BUY / SELL シグナルを生成し signals テーブルへ書き込む（冪等）。
    - ファクター重みのマージと正規化（デフォルト重みは StrategyModel.md の仕様に準拠）。
    - AI ニューススコアの統合（ai_scores が無ければ中立補完）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY 抑制）。
    - SELL（エグジット）判定: ストップロス（-8%）優先、スコア低下による退出。
    - positions テーブルと連携し、SELL 対象は BUY から除外するポリシー実装。
    - DB 書き込みはトランザクションで保護。ROLLBACK 失敗時の警告ログ出力。

- リサーチ関連（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials に依存）。
    - 200 日移動平均乖離、ATR、平均売買代金、volume_ratio、PER/ROE などを算出。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons): 翌日/翌週/翌月等の将来リターンを一括取得するクエリ実装。
    - calc_ic(factor_records, forward_records, ...): スピアマンのランク相関（IC）計算。サンプル不足時には None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで扱うランク関数（丸め処理により ties 検出を安定化）。
  - research/__init__.py で公開 API を整理。

- バックテストフレームワーク（src/kabusys/backtest/）
  - engine.py:
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB に必要データをコピーして日次シミュレーションを実行するエンジン。
    - DB コピーは日付範囲フィルタを用い本番テーブルを汚染しない設計（prices_daily, features, ai_scores, market_regime 等）。
    - signals 読み取り・positions 書き戻しのユーティリティを提供。
  - simulator.py:
    - PortfolioSimulator: 擬似約定・ポートフォリオ管理を提供。
      - execute_orders: SELL を先、BUY を後に約定。SELL は現状「保有全量クローズ」。
      - スリッページ・手数料モデルを適用（BUY は始値*(1+slippage)、SELL は始値*(1-slippage) 等）。
      - mark_to_market による日次評価と DailySnapshot の記録。終値欠損時は 0 として警告出力。
    - TradeRecord / DailySnapshot のデータクラス定義。
    - 約定ロジックは手数料込みで残高不足時の再計算・調整を行う。
  - metrics.py:
    - calc_metrics(history, trades) により BacktestMetrics を計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数）。
    - 各指標の内部計算を分離して実装（年次化や営業日 252 日想定など）。

- データスキーマ/トランザクション、安全性設計
  - features / signals / positions への日付単位の置換はトランザクション＋バルク挿入で実装し原子性を確保。
  - 価格欠損時は判定をスキップしたり警告ログを出して誤クローズ・誤発注を防止する設計。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 環境変数に関する扱い:
  - OS 環境変数は自動ロード時に保護（.env で上書きされない）される旨を実装。
  - 自動ロードを無効化するフラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known limitations
- 一部仕様はコード内コメントで未実装・将来実装予定として記載（トレーリングストップ、時間決済、部分利確等）。
- calc_value は現状 PER/ROE のみを算出し、PBR・配当利回りは未実装。
- SELL ロジックは positions テーブルの一部メタ情報（peak_price / entry_date 等）に依存する機能が未実装のため、将来的な拡張で挙動が変わる可能性あり。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB で実装されることを前提としている。

---
もしリリース日や表記の調整、特定モジュールの記述追加・除外などご希望があれば教えてください。コード上のコメントや関数・定数名に基づいて要点をまとめています。