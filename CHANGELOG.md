# Changelog

すべての変更は「Keep a Changelog」規約に従って記載しています。  
このファイルはコードベースから推測して作成した初期の変更履歴（日本語）です。

フォーマット:
- 変更はカテゴリ別に整理（Added, Changed, Fixed, Security, Known issues / Notes 等）
- 初回リリースとして v0.1.0 を記載

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - サブパッケージのエクスポート: data, strategy, execution, monitoring を公開。

- 設定管理
  - 環境変数・.env 読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）により .env/.env.local を自動読み込み。
    - .env のパースは export 構文・クォート・エスケープ・インラインコメントに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
    - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定を取得。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証処理を実装。
    - パス設定（duckdb/sqlite）を Path 型で提供。

- データ取得・保存 (J-Quants)
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 発生時のトークン自動リフレッシュ（1 回のみ）と、無限再帰を防ぐ設計。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes — 日次株価（OHLCV）
      - fetch_financial_statements — 財務データ（四半期BS/PL）
      - fetch_market_calendar — JPX マーケットカレンダー
    - DuckDB に冪等的に保存する save_* 関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）
    - 日付/取得時刻（fetched_at）を UTC で記録（ルックアヘッドバイアス対策）。
    - 型変換ユーティリティ (_to_float / _to_int)。

- ニュース収集
  - RSS ベースのニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（例: Yahoo Finance）を定義。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホストの小文字化、フラグメント除去、クエリソート）。
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - XML パースに defusedxml を利用して安全に解析。
    - 受信サイズ制限（最大 10 MB）やバルク INSERT のチャンク化等の実装によりメモリ・DB 側の安全性を考慮。
    - raw_news / news_symbols 等への保存を想定した処理フロー。

- リサーチ（研究用）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: target_date 以前の最新財務データと組み合わせて PER, ROE を計算。
    - DuckDB の prices_daily / raw_financials テーブルを参照する設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン先（例: 1,5,21 営業日）の将来リターンを計算（1クエリでまとめて取得）。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数不足時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理（丸めにより tie 判定の安定化）。
  - research パッケージの再エクスポート（calc_momentum 等と zscore_normalize の公開）。

- 特徴量エンジニアリング・シグナル生成（Strategy）
  - build_features（src/kabusys/strategy/feature_engineering.py）:
    - research モジュールから生ファクターを取得して統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化（zscore_normalize を利用）→ ±3 でクリップ。
    - features テーブルへトランザクション + 日付単位で置換（冪等）。
    - 失敗時のロールバック処理とログ出力。
  - generate_signals（src/kabusys/strategy/signal_generator.py）:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みと閾値（デフォルト threshold=0.60）を用いた最終スコア計算。ユーザ指定 weights の検証とリスケーリングを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負で、サンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - 保有ポジションに対するエグジット（SELL）判定を実装（ストップロス -8% とスコア低下）。
    - signals テーブルへトランザクション + 日付単位で置換（BUY / SELL を分けて挿入）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外し、BUY のランクを再付与）。

- 汎用ユーティリティ
  - zscore_normalize は kabusys.data.stats から提供（research/strategy で使用）。
  - DuckDB を用いる設計で大量データ処理に適した SQL ベース実装。

### Changed
- （初回リリースのため過去からの変更はなし。設計方針・実装上の配慮点を明文化）
  - ルックアヘッドバイアス対策として、各種取得タイムスタンプ（fetched_at）と「基準日」ベースの SQL を徹底。
  - 外部発注 API や実口座への操作はこのライブラリの core 計算部では直接行わない設計。

### Fixed
- トークン自動刷新ロジックでの無限再帰を防止するため allow_refresh フラグと _token_refreshed フラグを導入（再試行制御）。
- DuckDB 保存処理で PK 欠損行はスキップし、スキップ数のログ出力を追加（データ不整合検知）。

### Security
- RSS パースに defusedxml を採用し XML 関連の攻撃を軽減。
- news_collector で受信サイズ上限（MAX_RESPONSE_BYTES）を設け、メモリ DoS を防止。
- URL 正規化でトラッキングパラメータを削除し、ID 決定により冪等性を担保。
- .env 自動読み込み時に OS 環境変数を保護するため protected set を採用（.env.local の override でも OS 環境を直接上書きしない）。
- J-Quants クライアントで認証トークン管理をモジュールキャッシュ化し、不要なリフレッシュを抑制。

### Known issues / Notes / TODO
- signal_generator の SELL 条件として設計書にある「トレーリングストップ（peak_price 必要）」および「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector の SSRF 対策は設計に言及あり（HTTP/HTTPS チェックや IP ブロック等）が、実装の詳細についてはさらに検証が必要（HTTP 制限やホワイトリストの強化等）。
- 一部の計算はデータ充足を前提としており、データ不足時は None を返す（上流 ETL によるデータ品質確保が必要）。
- 外部ライブラリへの依存を極力避ける設計（pandas 等未使用）だが、大規模データ解析では最適化や追加依存の検討が必要になる可能性がある。

---

参照:
- 各モジュールの docstring に設計方針・仕様（StrategyModel.md / DataPlatform.md 等）への言及あり。実運用時は該当ドキュメントと合わせて確認してください。