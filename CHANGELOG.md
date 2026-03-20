# CHANGELOG

すべての注記は Keep a Changelog のガイドラインに従っており、重大度・目的別に分類しています。日付はこのリリースを推測した作成日です。

全般方針:
- セキュリティ・冪等性・ルックアヘッドバイアス回避に配慮して設計されています。
- DuckDB を中心としたローカルデータプラットフォーム上でのデータ取得・保存・解析・シグナル生成のワークフローを提供します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ定義（src/kabusys/__init__.py）: version 0.1.0、公開サブパッケージを宣言。
- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 一行パーサを備えた堅牢な .env パーシング（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理、無効行スキップ）。
  - OS 環境変数保護（protected set）を考慮した上書きロジック。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パスなど主要な環境変数をプロパティ経由で取得。値検証（KABUSYS_ENV / LOG_LEVEL 等の許容値チェック）を実装。
- Data レイヤー: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API レート制限（120 req/min）を守る固定間隔レートリミッタ実装。
  - 再試行（指数バックオフ、最大3回）と 401 時のトークン自動リフレッシュ（1 回のみ）を実装。
  - ページネーション対応のデータ取得: 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT による冪等保存を行い、保存前の PK 欠損行スキップとログ出力を行う。
  - 型安全なパースユーティリティ (_to_float / _to_int) を追加。
  - 取得時に fetched_at を UTC ISO8601 で付与し、データがいつ得られたかトレース可能に（ルックアヘッド回避の設計）。
- Data レイヤー: ニュース収集（src/kabusys/data/news_collector.py）
  - デフォルト RSS ソース、RSS 取得・XML パース（defusedxml を使用して XML 攻撃対策）、記事ID を正規化 URL の SHA-256 ハッシュで生成し冪等性を確保。
  - URL 正規化処理（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、HTTP スキーム検証、バルク INSERT のチャンク化、DB トランザクション内での保存ロジック。
- Research レイヤー（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - momentum (1M/3M/6M)、ma200 乖離、ATR（20日）、20日平均売買代金、出来高比率、PER/ROE 取得を DuckDB SQL によって実装。
    - スキャン範囲にカレンダーバッファを採用し、休場日や欠損に堅牢。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンのリターンを効率的な単一クエリで取得。
    - IC（Spearman の ρ）計算（calc_ic）: ランク化・同順位平均の実装、最小サンプルチェック。
    - ファクター統計サマリー（factor_summary）と rank 関数を実装。外れ値・None を除外して安全に集計。
  - 研究向けの z-score 正規化機能をエクスポート（kabusys.research 経由）。
- Strategy レイヤー（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research で計算された生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - 休場日や当日の欠損に対応するため target_date 以前の最新価格を参照。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を計算（デフォルト重みを定義）。
    - Sigmoid と平均化ロジックを用いたコンポーネント正規化、None の補完（中立値 0.5）で欠損の不当な降格を回避。
    - Bear レジーム判定（AI の regime_score の平均が負、十分なサンプルがある場合にのみ Bear と判定）で BUY を抑制。
    - BUY/SELL の判定と signals テーブルへの日付単位置換を実装。SELL 判定にはストップロス（-8%）とスコア低下を含む。SELL 優先ポリシー（SELL の銘柄は BUY から除外）。
    - 重みのバリデーションと再スケーリング、ユーザ指定 weights の部分的上書きサポート。
- Execution / Monitoring
  - パッケージに名前空間を用意（execution, monitoring）が公開され、将来の実装拡張に備えています。

Changed
- N/A（初期リリース）

Fixed
- N/A（初期リリース）

Security
- defusedxml を使った RSS パース、受信サイズ制限、URL スキーム検証、トラッキングパラメータ削除による ID 正規化など、外部入力に対する複数の防御策を導入。
- J-Quants クライアントでのトークン自動リフレッシュ制御により無限再帰を防止（allow_refresh フラグ）。

Notes / Known limitations
- signal_generator のエグジット条件のうちトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）。
- news_collector の記事IDは正規化した URL のハッシュに依存するため、URL ベースで関連付けされないニュースは別エントリとなる可能性あり。
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます（配布後の挙動を保護）。
- 一部のファクターは十分な過去データがないと None を返す設計（ファクター不足時は中立値で扱うなどの安全策を適用）。

参考
- 実装には DuckDB を用いた SQL ウェイト（ウィンドウ関数）やトランザクション制御、ログ出力、例外ハンドリングが中心に置かれています。
- 設計文書（StrategyModel.md / DataPlatform.md 等）に準拠した実装方針がコードコメントに記載されています。

[0.1.0]: 0.1.0