# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに準拠します。

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能（設定管理、リサーチ／ファクター計算、特徴量生成、シグナル生成、バックテストフレームワーク、シミュレータ、メトリクス）を実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージルート: `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local ファイルまたは OS 環境変数から設定値を読み込む自動ロード機能を実装。
  - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索する実装により、カレントワーキングディレクトリに依存しない読み込みを実現。
  - エクスポート形式（export KEY=val）やシングル/ダブルクォート、エスケープシーケンス、インラインコメント処理などを考慮した .env パーサー実装。
  - OS 側の環境変数を保護する機能（protected set）を導入。`.env.local` は既存OS変数を保護しつつ上書き可能。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - 必須値取得時に未設定であれば ValueError を返す `_require()` と `Settings` クラスを提供。
  - 主要設定プロパティを実装（J-Quants トークン、kabu API パスワード/ベースURL、Slack トークン/チャンネル、DB パス、環境（development/paper_trading/live）判定、ログレベル検証など）。

- リサーチ / ファクター計算（src/kabusys/research/）
  - factor_research.py:
    - モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（20日ATR, 相対ATR）、流動性（20日平均売買代金, 出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily/raw_financials を参照して算出する関数を実装。
    - データ不足時の安全な None 処理、ウィンドウ境界の扱いを考慮した実装。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結する実装。
  - research パッケージから主要関数群を再エクスポート。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを統合して features テーブルへ保存する build_features(conn, target_date) を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を導入。
  - 指定カラムを Z スコアで正規化、±3 でクリップする処理を実装（kabusys.data.stats の zscore_normalize を利用）。
  - 日付単位で冪等な置換（DELETE + bulk INSERT）をトランザクションで行い原子性を担保。例外時の ROLLBACK 対応。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）から final_score を算出する generate_signals(conn, target_date, threshold, weights) を実装。
  - デフォルト重み・閾値を実装し、ユーザー指定 weights を検証して正規化（不正値は無視・警告）。
  - sigmoid、平均化、欠損コンポーネントの中立補完（0.5）などのスコア算出ロジックを実装。
  - AI ニューススコアと市場レジーム（regime_score）を扱い、Bear 判定時は BUY シグナルを抑制。
  - 保有ポジションに対してストップロス（-8%）およびスコア低下に基づく SELL 判定を行うロジックを実装（_generate_sell_signals）。
  - signals テーブルへの日付単位置換（トランザクション）を実装。

- バックテストフレームワーク（src/kabusys/backtest/）
  - simulator.py:
    - PortfolioSimulator を実装。BUY/SELL の擬似約定、スリッページ・手数料モデル、平均取得単価の更新、時価評価（mark_to_market）、トレード記録（TradeRecord）と日次スナップショット（DailySnapshot）を提供。
    - SELL は保有全量クローズの仕様。始値欠損時はスキップし警告ログを出力。
  - metrics.py:
    - バックテスト評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数）を計算するユーティリティを実装（calc_metrics）。
  - engine.py:
    - 本番 DB からインメモリ DuckDB へ必要データをコピーする _build_backtest_conn() を実装（signals / positions 等を汚染しない）。
    - 日次ループでの注文約定・positions 書き戻し・時価評価・シグナル生成・ポジションサイジングを行う run_backtest(conn, start_date, end_date, ...) を実装。
    - DuckDB を用いたデータ取り回し、各ステップでのログ出力と例外保護を実装。

### 変更 (Changed)
- 初回リリースのため履歴なし。

### 修正 (Fixed)
- 初回リリースのため履歴なし。

### 未実装 / 既知の制限 (Known limitations / Not implemented)
- トレーリングストップ（直近最高値ベース）および時間決済（保有 60 営業日超過）は _generate_sell_signals 内で未実装。positions テーブルに peak_price / entry_date 等が必要。
- バリューファクターの PBR・配当利回りは現バージョンで未実装。
- 一部のテーブル操作でスキーマ依存のため（例: raw_financials のカラム依存）事前にスキーマ準備が必要。
- 外部依存: DuckDB が必須（DuckDB 接続を前提に実装）。

### セキュリティ (Security)
- 重要なトークンや認証情報は環境変数から取得する設計（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。.env の取り扱いに注意してください。

### 注意事項 / 運用メモ
- 自動 .env ロードはプロジェクトルートの検出に依存します。パッケージ配布後に想定通り動作させるため、プロジェクトルートに `.git` または `pyproject.toml` が存在することを確認してください。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- Settings クラスの env / log_level は許容値を検証します。誤った値をセットすると ValueError が発生します。
- 各モジュールはデータ欠損や非有限値に対して堅牢な扱い（None/スキップ/警告ログ）を行うよう実装されています。

---

今後の予定（例）
- トレーリングストップや時間決済の実装
- バリューファクターの拡張（PBR、配当利回り）
- 実行層（execution）と Slack/通知の統合強化
- 単体テスト・CI の整備、ドキュメントの充実

Contributors: 初期実装（単一リポジトリより推測）