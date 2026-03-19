# Changelog

すべての変更は「Keep a Changelog」の形式に準拠し、セマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ基盤
  - パッケージのバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - 公開 API を __all__ にて定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートを .git または pyproject.toml を起点に探索する _find_project_root。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env をオーバーライド）。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ (_parse_env_line) を実装：
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等を実装。
  - .env のロード処理で OS 環境変数を保護する protected キーセットを採用。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔レートリミッタ(_RateLimiter)。
    - 再試行（指数バックオフ、最大3回）および 408/429/5xx に対する再試行処理。
    - 401 受信時の自動トークンリフレッシュ（1回）とモジュールレベルのIDトークンキャッシュ。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - JSON デコードエラーや HTTP エラー時の詳細ログ/例外処理。
  - DuckDB への冪等保存関数を実装（ON CONFLICT / DO UPDATE 等で重複排除）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - 型変換ユーティリティ (_to_float, _to_int) と PK 欠損行のスキップ/警告ログ。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する実装。
    - デフォルトの RSS ソース定義（例: Yahoo Finance）。
    - defusedxml を使った安全な XML パース（XML Bomb 等の防御）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
    - URL 正規化 (_normalize_url): トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、フラグメント除去、クエリパラメータソート。
    - 記事IDは正規化 URL のハッシュで冪等性を担保。
    - DB バルク挿入のチャンク化とトランザクション集約、INSERT RETURNING による実挿入数の取得を想定した設計。

- リサーチ用ユーティリティ（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）を実装：
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（直近財務レコードの取得ロジック含む）。
    - 各関数は DuckDB 接続と target_date を受け取り、(date, code) をキーとする dict のリストを返す設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を実装：
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: スピアマン順位相関（Information Coefficient）を計算する関数（結合・欠損処理・最小サンプル数チェック含む）。
    - factor_summary, rank: ファクターの統計サマリー、ランク変換ユーティリティ（同順位は平均ランク）。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 関数を実装：
    - research の calc_momentum / calc_volatility / calc_value を組み合わせ、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを zscore 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルに冪等的にアップサート（DELETE + バルクINSERT をトランザクションで保護）。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 関数を実装：
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重みのマージと正規化（デフォルト重みは StrategyModel.md に基づく）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負である場合。ただしサンプル数閾値を設定）により BUY を抑制。
    - BUY閾値（デフォルト 0.60）を超えた銘柄に BUY シグナルを生成。
    - 保有ポジションに対するエグジット判定（ストップロス：-8% など）を実装し SELL シグナルを生成。
    - SELL を優先して BUY から除外し、signals テーブルに日付単位の置換で書き込み（トランザクションで原子性を保証）。
    - 重みの入力検証（未知キーや非数値を無視、合計が 1.0 でなければリスケール）と詳細なログ出力。

- インフラ・運用上の配慮
  - 各種処理でログ出力を充実（info/warning/debug）。
  - DuckDB を使ったバルク挿入やトランザクションを多用し、データの冪等性と原子性を確保。
  - ルックアヘッドバイアス防止に関する設計注記（data の fetched_at, target_date 時点のデータのみ使用等）を各モジュールに明記。

### Changed
- 初版リリースのため該当なし（新規追加のみ）。

### Fixed
- 初版リリースのため該当なし。

### Security
- RSS パースに defusedxml を使用して XML 脅威を軽減。
- ニュース収集で受信サイズ制限・URL のスキーム検証を行う想定設計により SSRF / DoS 対策を考慮。
- J-Quants クライアントでトークンリフレッシュの際に無限再帰を防ぐため allow_refresh フラグを導入。

### Notes / Known limitations
- 一部仕様はドキュメント（StrategyModel.md / DataPlatform.md / Research 配下ドキュメント）に依存し、実装はその節の要約に従っていますが、ドキュメント自体は本リリースに含まれていません。
- signal_generator の一部の退出条件（トレーリングストップ、時間決済など）は positions テーブルへの追加情報（peak_price / entry_date 等）が未整備なため未実装。
- news_collector の RSS フィード取得・パースの具象実装（HTTP ヘッダ制御、タイムアウト細部）は基本設計を満たす形になっていますが、実運用ではさらに堅牢化（並列制御、フェイルオーバー等）が推奨されます。

---

今後のリリースではエグジット条件の追加実装、execution 層（kabu ステーション連携）や Slack 通知等の統合、より詳細なモニタリング機能の追加を予定しています。