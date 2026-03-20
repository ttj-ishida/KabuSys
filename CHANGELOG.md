CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従っています。  
このリポジトリはセマンティックバージョニングを採用しています。

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py にてバージョンを設定。
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / システム設定（環境・ログレベル）を環境変数から取得。
  - 環境変数の必須チェック（未設定時は ValueError）および env/log_level の値検証を追加。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min）を実装し API リクエスト間隔を強制。
  - 再試行（指数バックオフ、最大3回）と特定ステータス（408, 429, 5xx）に対するリトライ処理を実装。
  - 401 受信時の自動トークンリフレッシュ（1回）を追加。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB への永続化ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT による冪等保存をサポート。
  - 型変換ユーティリティ (_to_float / _to_int) を追加して入力データの堅牢性を向上。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）を実装。
  - defusedxml を用いた安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）などのセキュリティ対策を導入。
  - レコードの冪等保存方針（エントリID: 正規化URLのSHA-256ハッシュ利用を想定）などをドキュメント化。
- 研究用ファクター計算 (kabusys.research)
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: PER/ROE を prices_daily と raw_financials から計算。
  - 解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算。
    - calc_ic: Spearman（ランク相関）による IC 計算を実装（少数サンプル時は None を返す）。
    - factor_summary / rank: ファクターの統計サマリー、ランク付けユーティリティを実装。
  - research パッケージ __all__ に主要関数を公開。
  - DuckDB のみ参照し、本番APIや発注系には依存しない設計。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research 側で算出した生ファクターをマージし、ユニバースフィルタ（最低株価: 300 円、20日平均売買代金: 5 億円）を適用。
    - 指定カラムを zscore 正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ。
    - 日付単位の置換（DELETE してから BULK INSERT）によって冪等性と原子性を確保（トランザクションを使用）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features / ai_scores / positions を参照して最終スコア（final_score）を算出。
    - momentum / value / volatility / liquidity / news の重み付け集計（デフォルト重みを定義）と閾値（デフォルト 0.60）による BUY 判定。
    - AI レジームスコアを用いた Bear 判定（サンプル数閾値を導入し過少サンプルでの誤判定を回避）。
    - エグジット判定（ストップロス -8% を優先、スコア低下による売却）を実装。ポジション価格欠損時の判定スキップや features 欠損銘柄の扱い（final_score = 0.0 として SELL 判定）を明示。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と日付単位置換による冪等保存（トランザクション使用）。
- パッケージ公開 API (kabusys.strategy, kabusys.research)
  - strategy/__init__.py と research/__init__.py にて主要関数をエクスポート。
- ロギング/監視
  - 重要な処理（build_features, generate_signals, fetch/save 系）に logger を追加し操作ログを出力。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- news_collector で defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）への対策を実施。
- ニュース収集時の受信サイズ上限、URL スキーム検証、トラッキングパラメータ除去など SSRF/DoS の緩和策を設計に組み込み。

Notes / Implementation details
- DuckDB への書き込みは ON CONFLICT/DELETE+INSERT とトランザクションで原子性・冪等性を担保する設計です。
- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュし、ページネーション間で共有する実装です（_ID_TOKEN_CACHE）。
- .env のパースは export 形式やクォート内のエスケープ、インラインコメントの扱いなど実運用を考慮した実装になっています。
- 一部設計（例: トレーリングストップ、時間決済）はコメントで未実装として記載されており、将来の拡張を想定しています。

今後の予定（例）
- トレーリングストップや時間決済等、追加のエグジット条件の実装。
- news_collector の記事→銘柄紐付けロジック（news_symbols）や記事ID生成処理の実装・テスト。
- テストカバレッジの追加（CI での自動テスト）。
- execution / monitoring サブパッケージの実装（現状はプレースホルダ）。

-----