KEEP A CHANGELOGの形式に従い、コードベースから推測した変更履歴を日本語で作成しました。

CHANGELOG.md
=============
全体ポリシー: このプロジェクトでは Keep a Changelog 規約に沿って変更履歴を管理します。
リリース日付は本ファイル作成日（2026-03-20）としています。

変更履歴
-------

## [0.1.0] - 2026-03-20
最初のリリース。本バージョンで導入された主な機能・実装内容は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。
  - 公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出（.git または pyproject.toml）に基づく自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - コメント行・空行の無視
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートなし/ありの違いを考慮）
  - Settings クラスを実装し、必須値のチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）、デフォルト値、検証（KABUSYS_ENV / LOG_LEVEL の許容値）を提供。
  - パス設定（DUCKDB_PATH / SQLITE_PATH）は Path 型で返却。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（株価日足、財務データ、マーケットカレンダー取得）。
  - レート制限を守る固定間隔スロットリング（120 req/min）を実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ）を実装: ネットワークエラーや 408/429/5xx を対象に最大 3 回までリトライ。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。トークン取得は get_id_token()。
  - ページネーション対応のデータ取得（pagination_key を用いた繰り返し取得）。
  - DuckDB への保存関数を実装（冪等性を確保するため ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes: raw_prices への保存
    - save_financial_statements: raw_financials への保存
    - save_market_calendar: market_calendar への保存
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢性を確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集のための基礎実装を追加（既定の RSS ソースに Yahoo Finance を含む）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）や XML パースに defusedxml を利用して安全性を確保。
  - URL 正規化ユーティリティを実装（トラッキングパラメータ削除、クエリソート、小文字化、フラグメント除去）。
  - 記事表現型（NewsArticle）およびINSERTのチャンク処理（_INSERT_CHUNK_SIZE）など、データベース保存のための基盤を実装。

- 研究用ファクター計算 (src/kabusys/research/factor_research.py)
  - Momentum, Volatility, Value のファクター計算関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR/出来高系）
    - calc_value: per / roe（raw_financials から最新の財務を参照）
  - DuckDB を用いた SQL ベース計算で、営業日不足等の欠損処理を考慮。

- 研究用解析ユーティリティ (src/kabusys/research/feature_exploration.py)
  - calc_forward_returns: 指定日から将来（デフォルト: 1/5/21 営業日）のリターンを計算。
  - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランクで処理）。
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - rank: 同順位を平均ランクで扱うランク関数（丸め処理で ties の漏れを防止）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date): researchモジュールの生ファクターを統合し、ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用して features テーブルへ日付単位の置換（冪等）で保存。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）および ±3 のクリップ処理を実装。
  - 価格取得は target_date 以前の最新価格を参照し、ルックアヘッド防止を考慮。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合し最終スコア final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で書き込み（冪等）。
  - コンポーネントスコア:
    - momentum: momentum_20 / momentum_60 / ma200_dev をシグモイド平均
    - value: PER を 1/(1+per/20) に変換
    - volatility: atr_pct の反転シグモイド
    - liquidity: volume_ratio のシグモイド
    - news: ai_score をシグモイド変換（未登録は中立）
  - 重みのマージ/検証ロジック: デフォルト重みあり、与えられた weights は検証・補完・再スケール（合計が1になるよう）を行う。不正値は無視して警告。
  - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear と判定（サンプル数が閾値未満なら Bear とは判定しない）。
  - BUY シグナルは Bear レジームで抑制。SELL シグナルはストップロス（-8%）およびスコア低下を実装。
  - 保持ポジションの価格欠損時は SELL 判定をスキップする安全措置を実装。
  - signals テーブルへは日付単位で削除→挿入のトランザクション処理を行い原子性を確保。

- パッケージ公開 (src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py)
  - 研究用/戦略用 API を __all__ で再公開して簡単に利用可能に。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 削除 (Removed)
- 初版のため該当なし。

### 非推奨 (Deprecated)
- 初版のため該当なし。

### セキュリティ (Security)
- RSS パースに defusedxml を採用し、XML 脆弱性（XML bomb 等）への対策を実施。
- news_collector において受信サイズ制限を導入し大容量レスポンスによる DoS を軽減。
- J-Quants クライアントはトークン管理時に自動リフレッシュを導入し、401 応答に対して安全に対処。

補足: 既知の制限・未実装機能
- signal_generator のエグジット条件ではトレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装（コメントで TODO 指摘あり）。これらは positions テーブルに peak_price / entry_date 情報が必要。
- calc_value: PBR や配当利回り等は現バージョンでは未実装。
- execution パッケージは存在するが（src/kabusys/execution/__init__.py）、発注 API 連携等の実装はこのリリースには含まれていない（プレースホルダ）。
- news_collector の一部実装（ID生成・DB紐付け・SSRF 防止の各詳細）はコメントで設計が記載されているが、追加実装が必要な箇所がある可能性あり。

開発時注記
- DuckDB を利用した SQL と Python の組み合わせでファクター計算・保存を行う設計のため、DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals 等）の作成が前提となります。
- 環境依存の機密情報（API トークン等）は .env または環境変数で管理し、KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードをテスト時に無効化可能です。

今後の予定（例）
- execution 層の実装（kabu ステーション API 連携と発注ロジック）
- シグナルのバックテスト / ポジション管理機能の強化（トレーリングストップ・時間決済等）
- ニュースと銘柄のマッチングロジック強化（news_symbols の実装、記事→銘柄紐付け）
- ドキュメント・型アノテーションの追加・テストカバレッジ拡充

---
この CHANGELOG はコード内の実装コメント・関数名・ドキュメント文字列から推測して作成しています。追加のリリースや変更を反映したい場合は、変更点の箇所（ファイル名・関数名）と簡単な説明を教えてください。