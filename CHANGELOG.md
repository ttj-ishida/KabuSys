CHANGELOG
=========

すべての重要な変更点を一元的に記録します。
このファイルは Keep a Changelog の形式に準拠します。

v0.1.0 - 2026-03-21
-------------------

Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys.config: 環境変数・設定管理
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）
    - 複雑な .env 行パーサ実装（export 句対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
    - settings オブジェクトで必須キーを取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）
    - KABUSYS_ENV / LOG_LEVEL の入力検証、および is_live / is_paper / is_dev のユーティリティプロパティ
  - kabusys.data.jquants_client: J-Quants API クライアント
    - 固定間隔の RateLimiter (120 req/min) 実装
    - HTTP リトライ（指数バックオフ、最大試行回数 3、408/429/5xx 対象）
    - 401 受信時は自動的にリフレッシュトークンでトークン更新して 1 回再試行
    - ページネーション対応の fetch_* 関数（株価/財務/マーケットカレンダー）
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 値変換ユーティリティ（_to_float / _to_int）
    - fetched_at を UTC ISO8601 で記録し Look-ahead バイアスのトレースを可能にする設計
  - kabusys.data.news_collector: ニュース収集モジュール（RSS）
    - RSS 取得→前処理→raw_news への冪等保存フロー
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）
    - defusedxml を用いた XML パース（XML Bomb 等の攻撃対策）
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）などメモリ DoS 対策
    - バルク挿入のチャンク化による SQL 長・パラメータ数抑制
  - kabusys.research.*: リサーチ用モジュール群
    - factor_research: prices_daily/raw_financials を用いたファクター計算
      - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）
      - ボラティリティ/流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
      - バリュー（per, roe）: raw_financials の最新公開値を利用
      - スキャン範囲やウィンドウ内件数による欠損（None）ハンドリング
    - feature_exploration:
      - 将来リターン計算 calc_forward_returns（horizons 検証、まとめて1クエリ取得）
      - スピアマン IC 計算 calc_ic（ランク変換、同順位は平均ランクで処理、最低サンプル数チェック）
      - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）
      - ランク変換ユーティリティ rank（丸めによる ties 検出改善）
    - research パッケージの公開 API を整理（calc_momentum/calc_volatility/calc_value/zscore_normalize 等）
  - kabusys.strategy.*: 戦略層
    - feature_engineering.build_features
      - research で算出した生ファクターをマージ→ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
      - 数値ファクターを z-score 正規化（外れ値は ±3 でクリップ）
      - DuckDB の features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性確保、冪等）
    - signal_generator.generate_signals
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - コンポーネントごとに補完ロジック（欠損は中立 0.5 で埋める）
      - final_score は重み付け合算（デフォルト重みを持ち、ユーザ指定 weights を検証してスケーリング）
      - Bear レジーム検出（ai_scores の regime_score 平均が負の場合。ただしサンプル数閾値あり）
      - BUY シグナル閾値（デフォルト 0.60）を超える銘柄に BUY を生成（Bear では BUY 抑制）
      - SELL シグナル（エグジット）判定実装:
        - ストップロス: 終値 / avg_price - 1 < -8%
        - スコア低下: final_score < threshold
      - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）
  - kabusys.config の settings を通じた必須環境変数チェックと既定値の導入（DuckDB/SQLite パス等）
  - パッケージ初期 __version__ = "0.1.0"

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を利用して XML 攻撃を緩和
- ニュース収集で受信サイズ上限を設け、メモリ DoS のリスクを低減
- jquants_client でトークンリフレッシュと HTTP リトライ制御を実装し、認証周りとネットワークエラーからの復旧性を向上

Notes / Known limitations
- signal_generator の未実装・将来実装予定のエグジット条件:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加データが必要で現バージョンでは未実装。
- kabusys.__all__ に "monitoring" が含まれるが、モジュール実装は提供されていない（将来追加予定）。
- execution パッケージはプレースホルダとして存在する（実際の発注ロジックは含まれていない）。
- news_collector における追加の SSRF / ホスト検査や IP フィルタリング等の実装はファイル内のユーティリティ準備あり（ipaddress, socket 等のインポート）だが、完全な実装状態は要確認。
- settings の必須環境変数（JQUANTS_REFRESH_TOKEN 等）が未設定の場合、ValueError を送出するためデプロイ前に .env を用意すること。

Upgrade / Migration
- なし（初回リリース）

開発メモ（設計上の注記）
- DuckDB を主体としたデータプラットフォーム設計（prices_daily / raw_financials / features / ai_scores / positions / signals 等を前提）
- データ取得・保存は冪等性を重視（ON CONFLICT / 日付単位の DELETE→INSERT のパターン）
- ルックアヘッドバイアス対策: fetched_at の記録、シグナル/ファクター計算は target_date 時点のデータのみ参照
- ロギングと警告で欠損・異常ケースを明示（例: 価格欠損時に SELL 判定をスキップする等）

--- 

今後の計画（短期）
- execution 層の実装（kabu API 連携と発注ロジック）
- monitoring モジュールの追加（稼働監視、Slack 通知）
- news_collector のホスト/IP レベルの追加検証ロジックの完成
- 戦略アルゴリズムの追加チューニング（トレーリングストップ、時間決済等）

※ この CHANGELOG はソースコードの実装内容から推測して作成しています。実際の公開リリースノートとして使用する際は、実際のコミット履歴やリリースノートに基づいて適宜修正してください。