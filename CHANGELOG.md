CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に準拠して記載しています。
セマンティックバージョニングを使用しています。

[0.1.0] - 2026-03-19
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - ロード順: OS 環境変数 > .env.local (.env を上書き) > .env（既存の OS 環境変数は保護）。
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリから .git または pyproject.toml を探すため、CWD に依存しない動作。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
  - Settings クラスを提供し、必須項目の検査 (_require による ValueError)、既定値、型変換、値検証（KABUSYS_ENV / LOG_LEVEL の許容値）を実装。
  - 代表的プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - env / log_level / is_live / is_paper / is_dev

- データ取得＆保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ。
    - ページネーション対応（pagination_key を利用）。
    - 取得時刻を UTC（fetched_at）で記録してルックアヘッドバイアス対策。
  - fetch_* 系関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等性を保証: ON CONFLICT DO UPDATE / DO NOTHING を利用）
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ変換ユーティリティ: _to_float, _to_int（堅牢な変換処理）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事取得・正規化・raw_news への冪等保存を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - URL 正規化でトラッキングパラメータ除去（utm_* など）。
    - HTTP/HTTPS スキーム以外の URL の禁止（SSRF 対策の下地）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
  - 記事ID は正規化後の URL 等から SHA-256（先頭32文字）で生成して冪等性を担保。
  - バルク挿入はチャンク化してパフォーマンスと SQL 長制限に配慮。

- 研究用ファクター計算 (kabusys.research, factor_research)
  - calc_momentum, calc_volatility, calc_value を実装（DuckDB に対する SQL+Python 実装）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - Volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率
    - Value: PER（EPS 不在/0 の場合は None）、ROE（raw_financials から取得）
  - research パッケージで zscore_normalize（kabusys.data.stats で提供）と合わせて利用可能に。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research で計算した生ファクター（momentum / volatility / value）をマージ。
    - ユニバースフィルタを適用（最低株価 300 円、20日平均売買代金 5 億円）。
    - 数値ファクターを Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）して冪等性と原子性を保証。
    - 依存: prices_daily / raw_financials テーブル、zscore_normalize。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合しコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - シグモイド変換・欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付け合算（デフォルト重みは StrategyModel.md の値）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。サンプル数閾値あり）。
    - BUY シグナルは閾値 (default 0.60) 超えで生成、Bear レジームでは BUY を抑制。
    - SELL シグナル（エグジット判定）を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - SELL は BUY より優先、SELL 対象は BUY から除外してランク再付与。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - 重みの検証・正規化（未知キーや非数値は無視、合計が 1 でなければ再スケール）。

- 研究支援ユーティリティ (kabusys.research.feature_exploration)
  - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
  - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランク）。
  - factor_summary: count/mean/std/min/max/median を計算。
  - rank: 同順位の平均ランク計算、丸めによる ties の検出強化。

- パッケージ公開 API
  - kabusys.strategy.__init__ で build_features / generate_signals を公開。
  - kabusys.research.__init__ で主要ユーティリティを公開。

Security
- defusedxml を利用した XML パース（news_collector）。
- RSS URL 正規化・トラッキングパラメータ除去・受信サイズ制限により SSRF/DoS のリスクを低減。
- J-Quants クライアントは認証再取得・リトライを備え、RateLimiter によるレート制御を実施。

Known issues / Notes
- 未実装のエグジット条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）および時間決済（保有 60 営業日超）についてはコメントとして記載されており未実装。
- calc_* 系関数はデータ不足時に None を返す設計（安全側）。features/signal の計算では欠損値を中立で補完するポリシーを採用。
- news_collector の RSS パーシング本体・HTTP フェッチの細部は実装の前提がある（この差分からは一部ユーティリティの実装が含まれている）。
- 実行層（execution）や外部発注 API との結合は strategy 層で行わず、冪等な signals テーブルを書き出すだけの設計になっている（発注は別層で実装する想定）。
- 外部依存を極力避ける設計（研究モジュールは pandas 等に依存しない）。

その他
- ロギング（logger）と警告出力が広く組み込まれており、運用時の可観測性に配慮。
- DuckDB を中心とした SQL ベースの処理でパフォーマンスと監査性を確保する設計。

--------------------
今後の予定（例）
- トレーリングストップ / 時間決済の実装（positions テーブルの拡張：peak_price, entry_date 等）。
- news_collector のフェッチ周りの堅牢化（接続タイムアウト設定、backoff、ソース管理）。
- テストカバレッジの追加（ユニットテスト・統合テスト）。
- ドキュメント整備（StrategyModel.md / DataPlatform.md 等の参照を README へ統合）。