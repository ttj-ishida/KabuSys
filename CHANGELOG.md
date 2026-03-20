# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog に準拠しています。

## [Unreleased]

<!-- 次のリリースに向けた変更をここに記載 -->

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージメタ情報を追加（kabusys.__init__ にて version=0.1.0、公開 API を __all__ で定義）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。これによりカレントワーキングディレクトリに依存せずに .env を自動ロード可能。
  - .env 自動ロード時の優先順位を実装: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 高度な .env パーサを実装:
    - コメント行・空行の扱い、export KEY=val 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを含む。
  - 環境変数の必須チェック（_require）と型/値検証:
    - KABUSYS_ENV の許容値検査（development / paper_trading / live）
    - LOG_LEVEL の許容値検査（DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - デフォルト設定（KABU_API_BASE_URL, データベースパス等）を提供。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足・財務・マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - API 呼び出し共通処理:
    - 固定間隔スロットリングによるレート制御（120 req/min 相当の RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - JSON デコード失敗時の明示的なエラー扱い。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes/save_financial_statements/save_market_calendar: ON CONFLICT を用いた UPSERT による冪等保存。
    - レコード変換ユーティリティ（_to_float / _to_int）で入力の堅牢化。
    - PK 欠損行のスキップとログ警告。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する仕組みを追加。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - URL 正規化機能（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - defusedxml を用いた XML パースで XML-Bomb 等の攻撃を緩和。
  - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）や SSRF 防止を意識した入力検証。
  - バルク INSERT のチャンク処理とトランザクション最適化、INSERT RETURNING で挿入数を正確に返す設計。

- 研究用途モジュール (src/kabusys/research/*.py)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日移動平均乖離率）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリュー: calc_value（最新の raw_financials と prices_daily を組み合わせて PER/ROE を算出）
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、データ不足時は None を適切に返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定日から複数ホライズンに対する将来リターンを一括取得（効率的なウィンドウスキャン）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、ファクターの基本統計量サマリー。
  - research パッケージの公開 API を整理してエクスポート。

- 戦略層 (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features: research モジュールから得た生ファクターをマージ、ユニバースフィルタ適用（最低株価・平均売買代金）、Z スコア正規化（zscore_normalize 利用）、±3 クリップ、DuckDB の features テーブルへ日付単位の置換（トランザクション＋バルク挿入で冪等）。
    - ユニバースフィルタの独立実装（_MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円）。
    - ルックアヘッドバイアス排除のため target_date 時点のデータのみ使用する方針を明示。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals: features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換保存。
    - スコア計算:
      - momentum/value/volatility/liquidity/news の重み付け（デフォルト重みを定義）と user 指定 weights の検証・正規化。
      - z スコアをシグモイド変換し、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム検出（AI の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制。
    - SELL（エグジット）ロジック:
      - ストップロス（-8%）優先判定
      - final_score の閾値割れによるエグジット
      - 価格欠損時は判定をスキップして誤クローズを防止
    - signals テーブルへの原子置換（トランザクション＋バルク挿入）。
    - generate_signals / build_features は発注層や外部 API へ直接依存しない設計。

- データ処理ユーティリティ
  - zscore_normalize を含む統計ユーティリティを data.stats として利用（research/strategy から参照）。

### 改良 (Changed)
- ルックアヘッドバイアスやデータ欠損時の安全性を考慮した設計を多くのモジュールで適用（target_date 時点のみ使用、価格欠損時の警告と処理スキップ、トークン自動更新の再帰防止等）。

### セキュリティ (Security)
- RSS パーシングに defusedxml を採用して XML 攻撃に対する耐性を確保。
- ニュース収集時の受信サイズ上限や URL 正規化 / トラッキングパラメータ除去により外部入力の悪用リスクを低減。
- API クライアントにおけるトークン管理と再試行の設計により不正アクセスリスク・無限再帰を抑止。

### 既知の未実装事項 / 制約
- signal_generator._generate_sell_signals では現在トレーリングストップや時間決済条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- 一部の統計/分析機能は research 環境向けであり、外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装しているため、非常に大規模データの処理性能は用途により調整が必要となる場合がある。

----

開発・運用に関する詳細設計（StrategyModel.md / DataPlatform.md 等）に従って実装されています。今後のリリースではドキュメント化されている未実装条件の追加、テストカバレッジ拡充、性能チューニング等を予定しています。