# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のリリース
- Unreleased: 今後の変更点（無し）

[0.1.0] - 2026-03-20
Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にパッケージメタ情報を追加。
- 環境設定/ロード機能（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みする機能を実装。
  - export KEY=val 形式やシングル/ダブルクォート付き値、インラインコメント処理に対応した .env パーサを実装。
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）や OS 環境変数保護（.env.local の override 処理時）をサポート。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供し、各種設定プロパティ（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境判定、ログレベル検証など）を公開。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値を限定）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本的な HTTP リクエストラッパーを実装（urllib を使用）。
  - レート制限制御（120 req/min の固定間隔スロットリング）を実装する _RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。
  - 401 レスポンス受信時にリフレッシュトークンでトークンを自動更新して再試行する処理を実装（無限再帰対策あり）。
  - ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存ユーティリティを実装（冪等性確保のため INSERT ... ON CONFLICT DO UPDATE を使用）: save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ _to_float / _to_int を実装し、堅牢な値変換とスキップロジックを提供。
  - id_token のモジュールキャッシュを実装し、ページネーション間でトークンを共有。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news へ保存するための基盤を実装。
  - URL 正規化関数（トラッキングパラメータ除去・スキーム/ホスト小文字化・フラグメント除去・クエリソート）を実装（_normalize_url）。
  - セキュリティ対策を実装: defusedxml による XML の安全なパース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP/HTTPS スキームのみ許可、SSRF/メモリDoS 緩和策、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - RSS ソースのデフォルトに Yahoo Finance のビジネスカテゴリを追加。

- 研究／ファクター計算モジュール（src/kabusys/research/*.py）
  - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離率）。
    - ボラティリティ/流動性: 20日 ATR, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御）。
    - バリュー: per, roe（raw_financials の最新レコードを参照）。
  - 研究支援ツール（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（ペア数が 3 未満なら None）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを与えるランク計算を実装（丸めによる ties 対策あり）。
  - 研究用 API を __all__ に公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research 側で算出した生ファクターをマージ・ユニバースフィルタ（株価 >= 300 円・20日平均売買代金 >= 5 億円）適用、Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして features テーブルへ日付単位で置換（冪等）する build_features を実装。
  - 価格欠損の扱い（target_date 以前の最新価格を参照）やトランザクションでの原子性保証を実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算し BUY / SELL シグナル（signals テーブル）を生成する generate_signals を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算、デフォルト重みと閾値（デフォルト閾値 0.60）を実装。重みのバリデーションと再スケーリング処理を実装。
  - AI レジームスコアの平均に基づく Bear 判定を実装（サンプル数不足時は非 Bear 扱い）。
  - Bear レジームでは BUY シグナルを抑制する処理を実装。
  - SELL 判定ロジック（ストップロス -8%／final_score が閾値未満）を実装し、SELL が優先されるポリシーを適用。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を担保。
  - ログ出力と不正値耐性（None/NaN/Inf の扱い）を実装。

- strategy パッケージの公開（src/kabusys/strategy/__init__.py）
  - build_features, generate_signals をパッケージ外公開。

Security
- ニュースパーサに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS/HTTP の受信サイズ制限・URL 正規化・スキーム検査により SSRF/メモリ DoS のリスク低減。

Known limitations / Notes
- execution パッケージは現時点で未実装（src/kabusys/execution/__init__.py が空）。
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date などの追加情報が必要。
- news_collector の完全実装（パース → DB 挿入／symbols 紐付け等の詳細な保存ロジック）は引き続き拡張の余地あり。
- research モジュールは外部ライブラリに依存せず標準ライブラリ＋DuckDB SQL で実装しているため、大規模データ処理ではパフォーマンスチューニングの余地がある。

その他
- ロギング（logger）を各モジュールで使用し、操作の可観測性を確保。
- DuckDB を中心とした設計（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar 等のテーブル想定）。

今後の予定（例）
- execution 層の実装（kabuステーション API 経由の発注制御、トランザクション管理）。
- news_collector の完全ワークフロー実装（HTTP フェッチ、XML→Article 抽出、news_symbols 紐付け、DB 保存の実装完了）。
- positions テーブルの拡張とトレード管理用の追加メトリクス（peak_price, entry_date 等）の導入。
- 単体テスト・統合テストの整備と CI パイプライン構築。

--- 
この CHANGELOG はコード内容から推測して作成しています。細部の実装やリリースノートの表現は開発方針に合わせて適宜修正してください。