# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ初期リリース: kabusys — 日本株自動売買支援ライブラリのコア構成を追加。
  - パッケージメタ情報: src/kabusys/__init__.py（サブモジュール data, strategy, execution, monitoring を公開）。
- 環境設定管理:
  - src/kabusys/config.py に Settings クラスを実装。
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を検出）から自動読み込みする仕組みを追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化: export 構文、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - 必須環境変数取得時のバリデーションとエラーメッセージを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境値の検証: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。dev/paper_trading/live 判定プロパティを追加。

- Data レイヤー:
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - リトライ（指数バックオフ）と 401 発生時の自動トークンリフレッシュ、Retry-After ヘッダ考慮の実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
    - 安全な型変換ユーティリティ (_to_float, _to_int) を追加。
  - RSS/ニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS 取得・パース（defusedxml を使用）、Gzip 対応、最大応答サイズ（10 MB）チェック、Gzip 解凍後のサイズチェックを実装（メモリDoS・Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）および記事ID生成（SHA-256 の先頭32文字）を実装。
    - SSRF 対策: URL スキーム検証、リダイレクト先検査（_SSRFBlockRedirectHandler）、プライベートIP/ループバック/リンクローカル判定を実装。初期ホスト検証も実施。
    - テキスト前処理（URL除去、空白正規化）と、記事内からの銘柄コード抽出（4桁数値、known_codes に基づく）を実装。
    - DuckDB への保存でトランザクション・チャンク挿入・INSERT ... RETURNING を利用する冪等保存ロジック（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。
    - run_news_collection により複数ソースの収集を統合（ソース単位で例外ハンドリング）。

- データスキーマ:
  - src/kabusys/data/schema.py に DuckDB 用スキーマ定義（Raw Layer）を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む）。初期化用の DDL 定義を提供。

- Research / Feature & Factor 計算:
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）を追加。
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1/5/21 営業日）への将来リターンを一括 SQL（LEAD ウィンドウ）で効率的に計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（欠損・非有限値除外、3 銘柄未満は None 返却）。
    - rank: 同順位の平均ランクを返すランク付けユーティリティ（小数丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算。
    - これらは DuckDB の prices_daily テーブルのみ参照し、本番注文APIへアクセスしない設計。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range を適切に扱う）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から最新の財務データを取得して PER（EPS が 0/欠損時は None）、ROE を計算。PBR/配当利回りは未実装として明示。
    - 各計算はウィンドウ関数や LAG/AVG を活用し、スキャン範囲はバッファ付きで限定（パフォーマンス配慮）。

- Research パッケージ初期公開 API を src/kabusys/research/__init__.py でまとめてエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- プロジェクトルート検出ロジックを __file__ 位置から上位ディレクトリに探索する方式にして、カレントワーキングディレクトリに依存しない自動 .env ロードを実現。

### 修正 (Fixed)
- .env 読み込みでファイルオープンに失敗した場合に警告を出して継続するようにし、環境読み込みが致命的にならないように改善。
- RSS パース失敗やネットワーク例外をソース単位でハンドリングして他ソース収集を継続するよう改善。

### 注意点 / 既知の制限 (Known issues / Notes)
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装とし、計算は標準ライブラリ + DuckDB の SQL に依存しています。大規模データでの計算パフォーマンスは運用環境により要検証。
- calc_value では PBR や配当利回りの計算は未実装。
- DuckDB スキーマ定義は Raw Layer の DDL を中心に実装。その他のレイヤー（Processed / Feature / Execution）の完全な DDL は今後の拡張対象。
- news_collector の URL 正規化は既知のトラッキングパラメータプレフィックスを削除しますが、すべてのケースを網羅するものではありません。
- jquants_client のベース URL はコード内定数 _BASE_URL に設定されています。実運用では環境変数 /設定で上書きしたい場合は拡張が必要。

### セキュリティ (Security)
- RSS パースに defusedxml を使用し、XML Bomb 等の攻撃に対する防御を実装。
- RSS 取得で SSRF を防ぐため、スキーム検証、リダイレクト時の検査、プライベートIPフィルタリングを実装。
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュの扱いを厳格に実装し、誤った再帰（無限リトライ）を防ぐ設計を行っています。

---

今後の予定（例）
- Processed / Feature / Execution レイヤーの DDL 完全実装・マイグレーション仕組みの追加
- strategy / execution モジュールの具体的な売買ロジックと発注ラッパーの実装
- 単体テスト・統合テスト（ネットワーク依存部のモック化）と CI の整備

もし CHANGELOG に追記してほしい点（例えば日付の変更、より詳細な実装者情報、未実装項目の優先度など）があれば教えてください。