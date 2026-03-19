CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

注: バージョン番号はパッケージ内の __version__（0.1.0）に基づいています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース（kabusys 0.1.0）。
- パッケージのエントリポイント:
  - src/kabusys/__init__.py にて version と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定・環境変数管理:
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（環境変数優先）。
    - 読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - export KEY=val 形式やクォート・インラインコメント等に対応する堅牢な .env パーサー実装。
    - settings オブジェクトを提供し、J-Quants / kabuステーション / Slack / DB パス 等の必須・デフォルト設定へのアクセスを簡素化。
    - env / log_level の値検証（許容値チェック）を実装。
- Data レイヤー（外部 API クライアント・収集保存処理）:
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライ（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュロジック。429 の Retry-After 処理、ネットワーク例外リトライを考慮。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
    - データ変換ユーティリティ（_to_float, _to_int）を提供し、不正データを安全にスキップ。
  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース収集モジュールを実装（デフォルトに Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）実装。
    - defusedxml を利用した安全な XML パース、受信サイズ上限、SSRF 回避の方針を採用。
    - バルク挿入のチャンク化や INSERT RETURNING を想定した冪等保存戦略。
- Research レイヤー（バックテスト・ファクター計算・解析ユーティリティ）:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対ATR、平均売買代金、出来高比率）、バリュー（PER/ROE）等の計算関数を実装。
    - DuckDB SQL を活用して効率的に計算（ウィンドウ関数・LEAD/LAG/AVG 等）。
    - 欠損やデータ不足時の安全な None ハンドリング。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、ページ幅制御による範囲限定）、IC（Spearman のランク相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク付けユーティリティを実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。
  - research パッケージの __init__ で主要ユーティリティを再公開。
- Strategy レイヤー（特徴量エンジニアリング・シグナル生成）:
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで算出した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）を適用し、Z スコア正規化（zscore_normalize を利用）して features テーブルへ日付単位で置換（トランザクション＋バルク挿入）する build_features を実装。
    - 正規化対象カラムの ±3 クリップ、ユニバース定義（300 円・5 億円）などを明記。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを signals テーブルへ日付単位で置換する generate_signals を実装。
    - momentum/value/volatility/liquidity/news の重み付き統合（デフォルト重みを提供）、しきい値（デフォルト 0.60）、Bear レジーム検出による BUY 抑制、エグジット条件（ストップロス -8% とスコア低下）を実装。
    - weights の検証・合成・正規化ロジックや、欠損コンポーネントの中立補完（0.5）を実装。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランク再付与）。
- Strategy パッケージの __init__ で build_features / generate_signals を公開。
- DuckDB を前提とした SQL 層設計:
  - 多数の処理でトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入を利用して原子性を確保。
  - 多くの関数は prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions / market_calendar 等のテーブルを参照・更新する前提。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- news_collector で defusedxml を利用して XML Bomb 等への耐性を確保。
- RSS の URL 正規化・トラッキングパラメータ除去・受信サイズ上限・HTTP スキーム検証など、外部入力に対する安全対策を導入。
- J-Quants クライアントでトークンの自動リフレッシュとリトライ戦略を実装し、認証エラーやレート制限状況に対処。

Known limitations / Notes
- execution パッケージは空（発注ロジック・kabuステーションとの接続は未実装）。
- signal_generator のエグジット条件のうち以下は未実装（コード中に注記あり）:
  - トレーリングストップ（peak_price を用いる）
  - 時間決済（保有 60 営業日を超える場合の自動クローズ）
  これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の一部挙動（INSERT RETURNING を前提とした挿入数取得など）は DB 実装に依存するため、環境差異に注意。
- zscore_normalize 実装は kabusys.data.stats に委譲している（本リリースでは参照先が別モジュール）。
- 環境変数の必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - （DB パス等はデフォルト値を持つが運用時は設定推奨）
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動ロードすること。

開発者向け補足
- 関数は DuckDB のコネクションオブジェクト（DuckDBPyConnection）を受け取り SQL を直接実行する仕様。テスト時は in-memory DuckDB 等を使うと良い。
- ロガーを広範に使用しており、運用時は LOG_LEVEL 環境変数で出力制御できる。
- API クライアントはページネーション・キャッシュ・レート制限を考慮しており、長時間のデータ収集処理に適している。

--- 

今後の予定（例）
- execution 層の実装（kabuステーション経由の発注・注文監視）。
- ポジション管理の拡充（peak_price / entry_date 管理、トレーリングストップ・時間決済の実装）。
- news_collector の記事 → 銘柄マッチング（news_symbols）ロジック追加。