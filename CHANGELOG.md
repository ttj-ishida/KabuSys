# Changelog

すべての notable な変更はこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。  
https://keepachangelog.com/ja/  
https://semver.org/

現在のバージョン: 0.1.0

## [Unreleased]
（現在未リリースの変更はここに記載）

## [0.1.0] - 2026-03-19
初回リリース。日本株の自動売買プラットフォームの基礎的なモジュール群を実装しました。  
主な機能はデータ取得・保存、研究向けファクター計算、特徴量エンジニアリング、シグナル生成、環境設定管理、ニュース収集などです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys パッケージ（__version__ = 0.1.0、主要サブパッケージを __all__ に公開）。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env と .env.local の読み込み優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化対応。
  - .env パース処理の強化（export プレフィックス、クォート内エスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、アプリ設定（J-Quants トークン、kabu API、Slack、DB パス、実行環境、ログレベル等）をプロパティ経由で取得。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- データ取得 / 保存 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - レート制御（120 req/min を想定する固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx をリトライ対象）。
    - 401 受信時のリフレッシュ処理（トークン自動更新を 1 回まで実施）。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - データ保存ユーティリティ（DuckDB への冪等保存: raw_prices, raw_financials, market_calendar。ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ (_to_float / _to_int) により外部データの堅牢なパースを実装。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスの追跡を可能に。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得と raw_news への冪等保存を実装（デフォルトの RSS ソースに Yahoo Finance を含む）。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）。
    - セキュリティ対策: defusedxml を使った XML パース、受信サイズ上限（10MB）、HTTP/HTTPS スキームチェック、SSRF 対策（注釈あり）。
    - バルク挿入のチャンク化で SQL 長・パラメータ数の上限に配慮。
- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - モメンタム (1M/3M/6M, ma200 乖離) 計算（prices_daily を参照）。
    - ボラティリティ/流動性 (20 日 ATR, ATR/価格, 20 日平均売買代金, 出来高比率) 計算。
    - バリュー (PER, ROE) 計算（raw_financials と prices_daily を組み合わせて最新の財務レコードを参照）。
    - DuckDB SQL を中心に実装し、外部ライブラリに依存しない設計。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン: デフォルト [1,5,21]）。LEAD を用いた一括取得。
    - IC（Spearman）の計算（ランク変換と tie の平均ランク処理を含む）。
    - ファクター統計サマリ（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク）。
- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールが生成した raw factors を結合し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize 使用）、±3 でクリップして outlier の影響を抑制。
  - features テーブルへの日付単位の置換（トランザクション＋バルク挿入で原子性を保証）。
  - build_features(conn, target_date) を公開 API として提供。
- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出（momentum/value/volatility/liquidity/news の重み付け）。
  - デフォルト重みと閾値を実装（デフォルト BUY 閾値 = 0.60 等）。
  - Sigmoid / 平均化ユーティリティ、欠損コンポーネントの中立補完（0.5）対応。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル不足時は Bear とみなさない）。
  - BUY シグナルは Bear 時に抑制、SELL（エグジット）はストップロスとスコア低下を判定。
  - positions / prices_daily / features / ai_scores を参照して signals テーブルへ日付単位で置換保存。
  - generate_signals(conn, target_date, threshold, weights) を公開 API として提供。
- パブリック APIまとめ (src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py)
  - 主要関数をパッケージトップから import できるようエクスポート。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限 / TODO
- シグナル生成のエグジット条件:
  - トレーリングストップ（直近最高値から -10%）および時間決済（60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector の SSRF / IP ブロック等の追加防御は注記のみ。実運用での詳細バリデーションやタイムアウト強化は検討が必要。
- jquants_client の _request は urllib を使った実装のため、より高機能な HTTP クライアント（requests 等）に置き換える余地あり。
- 外部依存を最小化する方針により pandas 等を利用していないため、大規模データ処理や便利関数は今後追加検討。

### マイグレーション / 実行時注意点
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により参照され、未設定の場合は ValueError を送出します。
- 環境のオーバーライド:
  - OS 環境変数は .env による上書きから保護されます（.env.local は上書きだが OS 環境変数が優先）。
  - テスト等で自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト値:
  - KABUSYS_ENV のデフォルトは "development"。
  - KABUSYS が使用するデータベースパスのデフォルトは DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - KABU_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"。
- DuckDB テーブル:
  - 実行には以下のテーブル構成（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）が想定されます。スキーマはコードの SQL 文やコメントから参照してください。

### セキュリティ
- XML パースに defusedxml を使用し、XML ベースの攻撃を軽減。
- news_collector で受信サイズ上限（10 MB）を設定しメモリ DoS を抑止。
- J-Quants クライアントはトークン自動リフレッシュを導入し、機密情報の扱いとレート制御に配慮。

### 貢献者
- 初期実装（作成者情報はソースに明記されていません）

---

今後のリリースでは、トレーリングストップ等の追加エグジットロジック、ニュースとシグナルのより緊密な統合、モジュール間のテストカバレッジ拡充、運用監視（monitoring サブパッケージ拡充）などを予定しています。