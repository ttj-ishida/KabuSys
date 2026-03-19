CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従って記載しています。  
履歴は semver（MAJOR.MINOR.PATCH）に基づき管理します。

[Unreleased]
------------

[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース（0.1.0）。
- パッケージ構成を追加:
  - kabusys パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。
  - strategy モジュール: build_features, generate_signals を公開。
  - research モジュール: ファクター計算・探索ユーティリティを公開。
- 環境変数 / 設定管理:
  - settings（Settings クラス）を導入。J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得用プロパティを提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの堅牢化（export 形式対応、クォート内エスケープ、インラインコメント対応、保護キーによる上書き制御）。
  - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）。

- データ取得・保存（kabusys.data）:
  - J-Quants API クライアント（jquants_client）を実装。
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx の再試行処理。
    - 401 受信時のリフレッシュトークン自動更新（1回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を使用し冪等性を確保）。
    - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）。
    - 取得/保存時に fetched_at を UTC ISO 形式で記録（ルックアヘッドバイアス対策）。
  - ニュース収集モジュール（news_collector）を実装。
    - RSS フィード取得、テキスト前処理、URL 正規化、トラッキングパラメータ除去。
    - defusedxml による XML の安全パース、受信サイズ上限（10MB）などの安全対策。
    - raw_news への冪等保存（ON CONFLICT / DO NOTHING 想定）、記事ID は正規化 URL の SHA-256 による生成方針を採用。
    - 大量挿入に対するチャンク処理を実装（パラメータ数／SQL 長の制御）。
  - DuckDB を想定したテーブル群（利用を前提）: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等。

- リサーチ（kabusys.research）:
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: target_date 以前の最新財務データと株価を組み合わせて PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみを参照し、本番 API への依存は無し。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコードが3未満なら None）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す。
    - rank: 同順位の平均ランクを返す堅牢なランク関数（丸めで ties の検出漏れを防止）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
  - build_features を実装。
    - research モジュールから得た生ファクターをマージ、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
    - 冪等設計（対象日を削除してから挿入）。
    - ユニバース閾値: 最低株価 300 円、最低平均売買代金 5 億円 等。

- シグナル生成（kabusys.strategy.signal_generator）:
  - generate_signals を実装。
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを計算して final_score を算出。
    - コンポーネントの欠損は中立値 0.5 で補完。
    - デフォルト重みとしきい値を定義（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 = 0.60）。
    - weights の入力バリデーション、フォールバック／再スケーリング処理を実装。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、ただしサンプル数閾値あり）により BUY を抑制。
    - 保有ポジション（positions テーブル）に対するエグジット判定（ストップロス -8% / final_score が閾値未満）。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）。

Changed
- 設計方針・実装メモを多くのモジュールに追加し、ルックアヘッドバイアス回避・冪等性・トランザクション方針・ログ出力方針を明文化。

Fixed
- N/A（初回リリースのため該当なし）。

Deprecated
- N/A。

Removed
- N/A。

Security
- news_collector で defusedxml を使用し XML 関連攻撃（XML Bomb 等）を防止する設計を採用。
- ニュース URL 正規化時に HTTP/HTTPS スキーム以外を拒否する方針（SSRF 対策）。
- J-Quants クライアントでタイムアウト / リトライ / レート制限を実装し外部 API 呼び出しの堅牢性を向上。

Notes / Known limitations
- generate_signals の SELL 条件について、コメントでトレーリングストップや時間決済など未実装の条件が明記されています（positions テーブルに peak_price / entry_date が必要）。
- calc_value では PBR・配当利回りは未実装。
- NewsCollector の記事 ID 方針や保存の詳細（例えばニュースと銘柄の紐付け news_symbols の挙動）は実装方針を示しているが、実際の紐付けロジックは今後の実装対象となる可能性があります。
- DuckDB のテーブル名・スキーマはコードから期待される構造があるため、運用前にスキーマ準備（テーブル作成）を行ってください。

互換性 / マイグレーション
- 初回リリースのため破壊的変更はありません。将来のリリースで settings プロパティ名／環境変数名を変更する場合は明確に通知します。

開発上の備考
- ログは各モジュールで logger を利用しており、運用時は LOG_LEVEL を環境変数で調整してください（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 自動 .env ロードはプロジェクトルートの特定に依存するため、配布後の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できるようにしています。
- J-Quants の API レート制限や 429 の Retry-After ヘッダは尊重する実装です。API 呼び出し設計時は rate limit を考慮してください。

開発者 / 貢献
- 初回リリース。今後の issue / PR を歓迎します。