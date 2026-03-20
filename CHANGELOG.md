Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

注意: コードベースから推測して記載しています。実装の意図・範囲に基づく要約です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動的にプロジェクトルートを探索して .env を読み込む実装を追加（CWD に依存しない）。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理（クォート内は無視、クォート外は '#' 前の空白でコメント判定）に対応する堅牢な _parse_env_line を実装。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を保護する protected 機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止対応。
  - Settings クラスを追加し、環境依存設定をプロパティとして提供（J-Quants リフレッシュトークン、kabu API パスワード/ベースURL、Slack トークン/チャンネル、データベースパス、環境モード/ログレベル検証など）。必須変数未設定時は ValueError を送出する _require を実装。

- Data / J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装を追加:
    - 固定間隔スロットリングによるレート制限 (120 req/min) をサポートする _RateLimiter を実装。
    - 汎用 HTTP リクエスト関数 _request を実装し、JSON デコード、最大リトライ（指数バックオフ）、408/429/5xx 対象のリトライロジックを備える。
    - 401 受信時はトークンを自動リフレッシュして再試行（リフレッシュは1回のみ）する処理を実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存用ユーティリティ save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等保存を行う。
    - 数値変換ユーティリティ _to_float / _to_int を実装し不正データに対して安全に None を返す。
    - API 呼び出し時の fetched_at を UTC ISO 8601 で記録し、データ取得時点をトレース可能にする設計。

- Data / ニュース収集（src/kabusys/data/news_collector.py）
  - RSS ベースのニュース収集機能を追加:
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
    - URL 正規化機能 _normalize_url を実装（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）。
    - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）、SSRF 防止の設計方針を反映。
    - 記事ID を正規化 URL の SHA-256（先頭32文字など）で生成して冪等性を確保する方針を記載。
    - バルク INSERT のチャンク化や ON CONFLICT DO NOTHING を用いた冪等保存などパフォーマンス／安全性配慮を実装予定箇所を含む（コード内設計記述）。

- Research（src/kabusys/research/*）
  - factor_research モジュールを追加（calc_momentum / calc_volatility / calc_value）:
    - prices_daily / raw_financials のみに依存して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per/roe）を計算。
    - ウィンドウ幅やスキャン範囲をカレンダー日でバッファし、営業日欠損を吸収する設計。
    - データ不足時に None を返す安全設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 複数ホライズン（デフォルト 1/5/21 営業日）で将来リターンを算出。
    - calc_ic: スピアマンのランク相関（IC）算出（ties は平均ランク処理）。有効サンプルが不足する場合は None を返す。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - rank: 同順位は平均ランクとするランク生成ユーティリティ（round(v, 12) による tie 判定の安定化）。

- Strategy（src/kabusys/strategy/*）
  - feature_engineering.build_features を追加:
    - research モジュールの生ファクターを取得しマージ、株価・流動性によるユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ、features テーブルへ日付単位で置換（削除→挿入）することで冪等性・トランザクション性を保つ。
  - signal_generator.generate_signals を追加:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出（デフォルト重みを定義）。
    - weights の入力検証・フォールバック・再スケールを実装（未知キーや NaN/負値は無視）。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）による公正な扱い、Bear レジーム判定（AI の regime_score 平均が負 → BUY 抑制）を実装。
    - BUY は閾値（デフォルト 0.60）以上、SELL はストップロス（-8%）やスコア低下により生成。positions / prices_daily を参照してエグジット判定を行う。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）および signals テーブルへの日付置換保存を実装。ロギング（INFO/DEBUG/警告）を充実。

Changed
- （初回リリースのため過去バージョンからの変更はなし）

Fixed
- （初回リリースのため過去バージョンからの修正はなし）
- 実装上の堅牢化点（.env パーサ、数値変換ユーティリティ、API エラー処理、XML パースの安全化）に留意して実装。

Security
- News collector: defusedxml の使用、受信サイズ制限、URL 正規化・トラッキング除去、HTTP/HTTPS スキーム制限など SSRF / XML Bomb / DoS 対策の設計を反映。
- J-Quants 客先 API クライアント: 401 リフレッシュの制御、リトライに対するバックオフ、タイムアウト設定など通信の堅牢化を実装。

Notes / Implementation details
- DuckDB を主要な分析 DB として想定し、raw_*/prices_daily/features/ai_scores/positions/signals 等のテーブルを利用する設計（テーブル定義は別途管理）。
- ルックアヘッドバイアス回避のため、各処理は target_date 時点までに「システムが観測できる」データのみを参照する方針。
- 発注（execution 層）や本番口座への直接アクセスは strategy / research 層で行わない設計。execution 層は別モジュールで提供予定（src/kabusys/execution は存在）。
- ロギングを多用し、異常系は警告/例外で露出する方針。

Authors
- コードベースの実装に基づき推測して記載。

履歴の追加・修正方法
- 今後の変更は本ファイルの先頭に Unreleased セクションを置き、リリース時に日付付きバージョンブロックへ移動してください（Keep a Changelog の慣習に準拠）。

---