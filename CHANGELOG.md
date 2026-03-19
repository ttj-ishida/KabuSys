# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買システム基盤として以下の主要機能・モジュールを含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブモジュールのエクスポート設定（data, strategy, execution, monitoring）。

- 設定・環境管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml ベース）により、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順序をサポート（OS 環境変数を保護する protected 機構）。
  - 行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等を適切に処理。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須検証、データベースパスの既定値 (DuckDB, SQLite)、環境（development/paper_trading/live）とログレベルの検証ユーティリティ（is_live 等）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントの実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx 対応）。
  - 401 受信時にはトークンを自動リフレッシュして1回リトライする仕組み。
  - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）で冪等性を担保（ON CONFLICT DO UPDATE）。
  - データ整形ユーティリティ（_to_float, _to_int）を実装。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアスのトレーサビリティを確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事取得および raw_news への冪等保存処理の骨組みを実装。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
  - defusedxml を用いた XML パース（XML Bomb 等への防御）。
  - HTTP/HTTPS スキームのみ受け入れる安全対策、MAX_RESPONSE_BYTES による受信サイズ制限（メモリ DoS 対策）。
  - 挿入時のチャンク処理（_INSERT_CHUNK_SIZE）や INSERT RETURNING を想定した設計。

- リサーチ（kabusys.research）
  - ファクター計算と解析のためのモジュール群を提供。
  - ファクター生成（kabusys.research.factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組合せて計算
    - 各計算は DuckDB のウィンドウ関数を活用し、営業日欠損に配慮してスキャン範囲を制限
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns） — 複数ホライズン対応、ホライズン検証（1〜252 日）
    - IC（calc_ic）: スピアマンランク相関を実装（ties の平均ランク処理、3 サンプル未満は None）
    - ファクター要約統計（factor_summary）と rank ユーティリティ
  - re-export により主要 API を上位名前空間で利用可能に。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールが計算した raw factor を取り込み、ユニバースフィルタ（最低株価・流動性）を適用。
  - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへ日付単位で冪等 UPSERT（トランザクションで原子性を確保）。
  - ユニバース基準: 最低株価 300 円、20 日平均売買代金 5 億円。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成・保存。
  - コンポーネントスコア:
    - Momentum（momentum_20/momentum_60/ma200_dev をシグモイド平均）
    - Value（PER を 1/(1+per/20) でスコア化）
    - Volatility（atr_pct の Z スコアを反転してシグモイド）
    - Liquidity（volume_ratio をシグモイド）
    - News（AI スコアをシグモイドで取り込み。未登録は中立）
  - 重み（DEFAULT_WEIGHTS）合成ロジックと入力検証（不正値は無視、合計を 1.0 に正規化）。
  - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値）により BUY を抑制。
  - エグジット判定（ストップロス -8% およびスコア低下）。SELL 優先ポリシー（SELL 対象は BUY から除外）。
  - signals テーブルへ日付単位で置換（トランザクションで原子性を確保）。
  - ログ出力と警告により欠損データ時の安全動作を確保（価格欠損時は SELL 判定スキップなど）。

### Changed
- 設計ドキュメントに基づく実装方針をコード内ドキュメンテーションとして反映。
  - ルックアヘッドバイアス回避、発注層への直接依存回避、DuckDB を中心とした設計等を明文化。

### Fixed
- （初版のため、主に設計上の注意点や未実装箇所を注記）
  - データ欠損や不正値に対する堅牢性を向上（NaN/Inf チェック、None 補完、ログ警告）。

### Known limitations / Not implemented
- 戦略仕様上の一部条件は未実装:
  - トレーリングストップ（peak_price 追跡）
  - 時間決済（保有 60 営業日超）
  - signals/positions テーブルの拡張（peak_price / entry_date 等）は将来の実装を想定
- news_collector の RSS 取得ループ以降の具体的な DB 挿入・銘柄紐付けロジックは骨組みを実装済みだが、完全な運用フローは今後拡張予定。
- 外部依存（kabusys.data.stats の zscore_normalize など）は既存実装を利用することを前提。

### Security
- news_collector: defusedxml を利用した XML パース、HTTP スキーム制限、受信サイズ制限、ホスト/IP 検証を想定した設計（SSRF/XML Bomb 対策）。
- jquants_client: トークン自動リフレッシュ時の無限再帰回避（allow_refresh フラグ）を実装。

---

今後の予定（例）
- execution 層（kabuステーション API 連携）と monitoring（Slack 通知等）の実装・統合。
- テストカバレッジ拡充（特にレート制御・リトライ・DB 集約処理）。
- パフォーマンス最適化（DuckDB のバルク処理・インデックス最適化など）。
- news_collector の記事→銘柄マッピング、自然言語処理パイプラインの導入。

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴・PR 控えに基づく追記・修正を推奨します。）