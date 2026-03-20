CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

[0.1.0] - 2026-03-20
--------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" の基本機能を実装。
- パッケージのバージョンは src/kabusys/__init__.py にて 0.1.0 を設定。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数からの設定読み込みを実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して行い、CWD に依存しない設計。
  - .env の自動ロード順序は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - export KEY=val 形式、クォート付き値（エスケープ対応）、インラインコメント処理など堅牢なパーサを実装。
  - 必須項目取得時に未設定なら ValueError を送出する _require を提供。
  - 設定値（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境・ログレベル判定など）のラッパー（Settings クラス）を提供。環境値の妥当性チェックを実施（KABUSYS_ENV, LOG_LEVEL 等）。
- データ取得・保存（J-Quants クライアント）（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通処理を実装（JSON パース、ページネーション対応）。
  - 固定間隔スロットリングによるレート制御（120 req/min のスロットリング実装）。
  - 再試行ロジック（指数バックオフ、最大3回）を実装（408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
  - id_token のモジュールレベルキャッシュを実装してページネーション間で共有。
  - API 結果を DuckDB に保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を保証。PK 欠損行はスキップして警告ログを出力。
  - 数値パースユーティリティ（_to_float/_to_int）を実装し、型安全な変換を担保。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news 等へ保存する仕組みの基盤を実装（RSS ソース定義、受信制限、正規化ユーティリティ等）。
  - 受信バイト数上限（10 MB）、トラッキングパラメータ除去、空白正規化、URL 正規化などの前処理を実装。
  - defusedxml を利用して XML Bomb 等の攻撃対策を実装。
  - 大量挿入を抑制するためのチャンク処理を用意。
- 研究モジュール（src/kabusys/research/）
  - ファクター計算群（factor_research.py）を実装：モメンタム（1/3/6M、MA200 乖離）、ボラティリティ（20 日 ATR/相対 ATR）、出来高/売買代金関連、バリュー（PER/ROE）を prices_daily / raw_financials を元に計算。
  - 前方リターン計算（calc_forward_returns）を実装：LEAD を用いた将来終値ベースのリターン計算、horizons の妥当性検証（1〜252）、複数ホライズンを一度に取得する最適化クエリ。
  - IC（Information Coefficient）計算（calc_ic）実装：Spearman（ランク相関）方式、サンプル不足時は None を返す。
  - ファクター統計サマリ（factor_summary）・rank（同順位は平均ランク）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの公開 API をまとめてエクスポート。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで計算された生ファクターを取得し、ユニバース（株価・流動性）フィルタ、Z スコア正規化、±3 でのクリッピングを行って features テーブルへ日付単位で UPSERT（削除→挿入）する処理を実装。
  - ユニバースフィルタ閾値: 最低株価 300 円、20 日平均売買代金 5 億円。
  - 正規化対象カラム指定と Z スコア処理を外部ユーティリティ（kabusys.data.stats.zscore_normalize）を通じて利用。
  - トランザクション + バルク挿入で原子性を保証。ロールバック失敗時のロギングを実装。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features テーブルと ai_scores テーブルを統合して各銘柄の final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換（削除→挿入）する処理を実装。
  - コンポーネントスコア：momentum / value / volatility / liquidity / news（AI）を算出。Z スコアはシグモイド変換で [0,1] にマッピング。
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止（BUY 側）。ただし SELL 判定の際は features に存在しない保有銘柄は final_score=0.0 と見なす（閾値未満のため SELL 対象）。
  - デフォルト重みと閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。ユーザ指定の weights は検証・スケーリングされる（未知キー・非数値は無視）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負の場合に BUY を抑制）。サンプル数閾値を設定して誤判定を抑制。
  - エグジット条件の実装（stop loss: -8% など）と、SELL 優先ポリシー（SELL 対象を BUY から除外しランクを再付与）を実装。
  - トランザクション + バルク挿入で原子性を保証。ロールバック失敗時のロギングを実装。
- パッケージのエクスポート（src/kabusys/strategy/__init__.py および research/__init__.py）で主要 API を公開。

Security
- ニュース収集で defusedxml を使用して XML による攻撃を防止。
- news_collector で URL のスキーム検証や受信サイズ上限（メモリ DoS 対策）を採用。
- jquants_client のトークンリフレッシュは allow_refresh フラグで制御し、無限再帰を防止。
- .env 読み込みでは OS の環境変数を protected として上書きを防止する仕組みを導入。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / Implementation details
- DuckDB を主要なオンディスク分析 DB として想定。各 save_* 関数は ON CONFLICT を使って冪等性を確保しているため、定期実行（cron / scheduler）での差分取得に耐える設計。
- ルックアヘッドバイアス防止を設計指針として採用（データの fetched_at 記録、target_date 時点のデータのみを使用する等）。
- 外部依存は最小限とし、研究モジュールでは pandas 等に依存せず標準ライブラリと DuckDB の SQL 機能で実装。

今後の予定（未実装 / TODO）
- strategy の SELL 条件におけるトレーリングストップや時間決済（positions テーブルに peak_price / entry_date を持たせる必要あり）。
- news_collector の記事 ID 生成（URL 正規化後の SHA-256 ハッシュなど）実装の確定と銘柄紐付けロジックの追加。
- 単体テスト・統合テストの整備、CI パイプラインの追加。