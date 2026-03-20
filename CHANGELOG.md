CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。
リリース日はパッケージ内部のバージョンに基づいています。

Unreleased
----------
- （現時点の作業ブランチ用のプレースホルダ。次のリリースに向けてここに変更を追加してください）

0.1.0 - 2026-03-20
-----------------
Added
- 初回リリース。本リリースで提供する主な機能群とモジュールを追加。
  - パッケージの公開インターフェース
    - kabusys.__init__ により data / strategy / execution / monitoring をエクスポート。
  - 環境設定管理 (kabusys.config)
    - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない設計。
    - 柔軟な .env パーサ実装（export 付き行、クォート、インラインコメント、エスケープ対応）。
    - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須変数取得時の _require() による明示的エラー。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証ロジック。
    - デフォルトのデータベースパス（DuckDB / SQLite）を提供。
  - Data 層 (kabusys.data)
    - J-Quants API クライアント (jquants_client)
      - レート制限（120 req/min）を固定間隔スロットリングで実装。
      - 冪等性を考慮した保存（DuckDB への ON CONFLICT DO UPDATE）を提供：
        - raw_prices（save_daily_quotes）、raw_financials（save_financial_statements）、market_calendar（save_market_calendar）。
      - ページネーション対応のフェッチ関数（fetch_daily_quotes / fetch_financial_statements）。
      - リトライ（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュ処理を実装。
      - id_token のモジュールレベルキャッシュを実装しページネーション間で共有。
      - 数値変換ユーティリティ（_to_float / _to_int）を提供し、データ品質を保つ。
    - ニュース収集モジュール (news_collector)
      - RSS フィードからの収集と raw_news への冪等保存（ON CONFLICT DO NOTHING）をサポート。
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事 ID 生成（SHA-256 ハッシュ）による重複排除。
      - defusedxml による XML パース、最大受信バイト数制限（10 MB）、SSRF/スキームチェック等の安全対策。
      - バルク INSERT のチャンク化により SQL 長・パラメータ上限を回避。
  - Research 層 (kabusys.research)
    - ファクター計算 (factor_research)
      - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER/ROE）を DuckDB を用いて計算。
      - 営業日ベースの窓設計およびデータ不足時の None 応答を考慮。
    - 特徴量探索 (feature_exploration)
      - 将来リターン計算（calc_forward_returns、複数ホライズン対応）。
      - スピアマン IC（calc_ic）、rank、ファクター統計サマリ（factor_summary）を実装。
      - 標準ライブラリだけで動作する設計（pandas 等に依存しない）。
    - 研究向けユーティリティを __all__ で公開（calc_momentum 等）。
  - Strategy 層 (kabusys.strategy)
    - 特徴量エンジニアリング (feature_engineering)
      - research で算出した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）でフィルタし、
        指定列を Z スコア正規化（zscore_normalize を利用）、±3 でクリップして features テーブルへ日付単位で置換（UPSERT 相当）。
      - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
    - シグナル生成 (signal_generator)
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - デフォルトの重み配分・BUY 閾値（0.60）を実装し、最終スコア（final_score）に基づく BUY/SELL シグナルを生成。
      - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル閾値以上）で BUY を抑制。
      - エグジット判定（ストップロス -8%、スコア低下）を実装。signals テーブルへ日付単位で置換。
      - 重みの入力検証・スケーリング、欠損コンポーネントの中立補完（0.5）など堅牢な設計。
  - 汎用ユーティリティ
    - zscore_normalize（kabusys.data.stats）等を研究/戦略層で利用可能に公開。
  - ロギングとエラーハンドリング
    - 各処理で適切な logger 呼び出し（info/warning/debug）を追加し、DB トランザクションの失敗時は ROLLBACK を試行して警告。

Security
- news_collector で defusedxml を使用して XML ベースの攻撃を緩和。
- ニュース収集における受信バイト数制限・URL スキーム検証によりメモリ DoS / SSRF リスクを低減。
- J-Quants クライアントで 401 リフレッシュ挙動やリトライ時の待機制御を実装し、誤ったトークン情報による連続失敗を抑制。

Notes / Implementation details
- DuckDB のテーブル名（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar, raw_news など）を前提とした処理が含まれます。
- 多くの API は target_date を明示的に受け取り、ルックアヘッドバイアスを防ぐため「その日時点で利用可能なデータのみ」を参照する設計です。
- 設定は環境変数主体（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）であり、必須変数は未設定時に明示エラーを返します。

Deprecated
- なし

Fixed
- 初回リリースのため該当なし

Removed
- なし

今後の課題（既知の未実装箇所）
- signal_generator の SELL 条件に記載されている一部（トレーリングストップ、時間決済）は positions テーブルに peak_price や entry_date が必要であり現バージョンでは未実装。
- news_collector の RSS ソースはデフォルトで Yahoo を含むが、ソース管理機能の拡張やより厳密な HTML 正規化は今後の改善候補。
- execution 層はパッケージ構造に存在するが（src/kabusys/execution/__init__.py）実装は含まれていません（発注 API 連携の実装は今後予定）。

--- 
（本 CHANGELOG はコードベースから推測して作成しています。詳細は各モジュールの docstring / ソースを参照してください。）